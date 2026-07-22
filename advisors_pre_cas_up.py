import random
import time
import json
import re
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st
from openai import OpenAI

from advisors_theme import apply_advisors_theme

# ------------ Question bank & settings ------------

QUESTION_BANK = {
    "Background": [
        "Where have you studied previously and what qualifications did you obtain?",
        "Can you explain any gaps in your study or employment history?",
    ],
    "Study destination": [
        "Why have you chosen to study in the UK rather than your home country or another destination like the US or Canada?",
        "The costs of studying in the UK are higher than in your home country. Why incur these extra costs?",
    ],
    "Institution choice": [
        "Why did you choose this university over others in the UK?",
        "What do you know about the city or area where your university is located?",
    ],
    "Course choice": [
        "Why did you choose this specific course?",
        "How does this course relate to your previous education or work experience?",
    ],
    "Course knowledge": [
        "What are the names or topics of some modules you will study?",
        "How long does your course last and how is it structured?",
    ],
    "Finances": [
        "How do you plan to pay for your tuition fees and living expenses in the UK?",
        "Who is financing your studies and what is the source of those funds?",
    ],
    "Accommodation": [
        "Where will you be living while studying in the UK?",
        "How will you travel from your accommodation to campus?",
    ],
    "Future plans": [
        "What do you plan to do after completing your course?",
        "Do you intend to return to your home country after your studies?",
    ],
}

QUESTION_ORDER = [
    "Background",
    "Study destination",
    "Institution choice",
    "Course choice",
    "Course knowledge",
    "Finances",
    "Accommodation",
    "Future plans",
]

QUESTION_HINTS = {
    "Study destination": "Mention 1–2 concrete reasons: course quality, recognition, Graduate Route, or proximity, based on your own research.",
    "Institution choice": "Mention a specific feature: ranking, facilities, department strength, or placement links, and how you found this out.",
    "Course choice": "Link the course to your previous study, work experience, and career goal, in your own words.",
    "Course knowledge": "Name at least one real module, assessment method, and practical outcome.",
    "Finances": "Explain the funding source, total amount, how long funds have been held, and what evidence you have (bank statements, sponsor letter).",
    "Accommodation": "Say where you will live, approximate cost, and how you will commute.",
    "Background": "Give a short timeline (years and institutions) and explain any gaps honestly.",
    "Future plans": "State your post-study plan in your home country and how the course helps you return and progress there.",
}

ANSWER_TIPS = {
    "default": "Use: direct answer → one specific detail → one short link to your goal.",
    "Study destination": "Mention one UK-specific academic advantage and one career reason, based on your own research.",
    "Institution choice": "Mention one university strength, one department feature, or one location reason backed by facts.",
    "Course choice": "Connect previous study or work directly to this exact course and career path.",
    "Course knowledge": "Mention a real module, assessment style, and practical outcome or accreditation.",
    "Finances": "State source of funds, total amount, how long they have been held, and what documents you will show.",
    "Accommodation": "Name where you will stay, estimated cost, and how you will commute to campus.",
    "Background": "Give a clear timeline and explain gaps honestly, with what you were doing.",
    "Future plans": "Describe a specific job or role in your home country and how the course prepares you to return and succeed there.",
}

RED_FLAGS = [
    "i don't know",
    "not sure",
    "my agent",
    "i haven't researched",
    "i plan to stay",
    "might not return",
    "i just want",
]

POSITIVE = [
    "because",
    "specifically",
    "module",
    "dissertation",
    "placement",
    "nhs",
    "career",
    "return",
    "back home",
    "sponsor",
    "tuition",
]

DEFAULT_THINK_TIME = 2
DEFAULT_MIN_WORDS = 20
QUESTION_TIME_SECONDS = 3 * 60

COURSE_PROFILES = {
    "UG – Business & Management": {
        "examples": "Business Management; International Business; Business Administration; Entrepreneurship",
        "extra_tip": "Mention business modules like strategy, operations, leadership, entrepreneurship, or international business, and explain how they fit your career plan.",
        "keywords": [
            "business",
            "management",
            "strategy",
            "leadership",
            "operations",
            "entrepreneurship",
            "international business",
            "organisation",
            "business environment",
        ],
    },
    # ... (keep all your other UG/PG course profiles exactly as in file:480)
}

# ------------ Streamlit & OpenAI setup ------------

st.set_page_config(
    page_title="Pre UKVI Compliance Interview",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_advisors_theme()

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2.4rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }
    .timer-card {
        border-radius: 22px;
        padding: 1.4rem 1rem;
        background: rgba(15, 23, 42, 0.06);
        text-align: center;
        margin-bottom: 1rem;
    }
    .timer-value {
        font-size: 4.25rem;
        font-weight: 900;
        line-height: 1;
        margin: 0;
    }
    .timer-label { font-size: 1.05rem; margin-top: 0.6rem; opacity: 0.8; }
    .timer-green { color: #15803d; }
    .timer-amber { color: #d97706; }
    .timer-red { color: #dc2626; }

    header [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ------------ Helpers ------------

def init_session_state():
    defaults = {
        "started": False,
        "completed": False,
        "idx": 0,
        "scores": [],
        "log": [],
        "profile": {},
        "current_category": "",
        "current_question": "",
        "question_start": None,
        "question_expired": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_interview_state():
    keys_to_clear = [
        "started",
        "completed",
        "idx",
        "scores",
        "log",
        "profile",
        "current_category",
        "current_question",
        "question_start",
        "question_expired",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    for key in [k for k in st.session_state.keys() if k.startswith("answer_")]:
        del st.session_state[key]
    init_session_state()

def pick_question():
    idx = st.session_state.idx
    if idx >= len(QUESTION_ORDER):
        st.session_state.completed = True
        return
    category = QUESTION_ORDER[idx]
    st.session_state.current_category = category
    st.session_state.current_question = random.choice(QUESTION_BANK[category])
    st.session_state.question_start = time.time()
    st.session_state.question_expired = False

def time_left():
    start = st.session_state.get("question_start")
    if not start:
        return QUESTION_TIME_SECONDS, f"{QUESTION_TIME_SECONDS // 60:02d}:00"
    elapsed = time.time() - start
    remaining = max(0, int(QUESTION_TIME_SECONDS - elapsed))
    return remaining, f"{remaining // 60:02d}:{remaining % 60:02d}"

def verdict(avg: float) -> str:
    if avg >= 4.5:
        return "✅ Strong Pre UKVI performance"
    if avg >= 3.5:
        return "🟡 Borderline — strengthen weak areas"
    if avg >= 2.5:
        return "🟠 At risk — more practice needed"
    return "🔴 High risk — urgent coaching required"

# --- Gibberish detector ---

def is_basic_gibberish(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 10:
        return True  # extremely short, likely not a real answer

    non_alpha = sum(1 for c in cleaned if not c.isalpha() and not c.isspace())
    if non_alpha > len(cleaned) * 0.3:
        return True

    words = cleaned.split()
    long_no_vowel = [
        w for w in words
        if len(w) >= 4 and not re.search(r"[aeiouAEIOU]", w)
    ]
    if len(long_no_vowel) >= 2:
        return True

    return False

def bespoke_score(answer: str, category: str, profile: dict) -> dict:
    lower = answer.lower()

    if is_basic_gibberish(answer):
        return {
            "score": 1,
            "feedback": "Answer appears to be random or not meaningful.",
            "student_tip": "Type a clear sentence in your own words that directly answers the question.",
            "risk_flags": ["gibberish"],
            "missing_points": ["Coherent explanation", "Real reasons and examples"],
            "counsellor_note": "Student provided gibberish; needs guidance on answering in full sentences.",
            "red_flag": True,
            "generic_pos": 0,
            "cluster_hits": 0,
            "readiness": "High risk",
        }

    for flag in RED_FLAGS:
        if flag in lower:
            return {
                "score": 1,
                "feedback": f"High-risk phrase detected: '{flag}'.",
                "student_tip": "Avoid agent-led or immigration-focused language. Explain your own genuine reasons.",
                "risk_flags": [flag],
                "missing_points": ["Clear personal rationale", "Evidence that supports your story"],
                "counsellor_note": "Student used a high-risk phrase; requires reframing and clear evidence.",
                "red_flag": True,
                "generic_pos": 0,
                "cluster_hits": 0,
                "readiness": "High risk",
            }

    generic_pos = sum(1 for signal in POSITIVE if signal in lower)

    course_track = profile.get("course_track")
    cluster_hits = 0
    if course_track and course_track in COURSE_PROFILES:
        keywords = COURSE_PROFILES[course_track].get("keywords", [])
        cluster_hits = sum(1 for keyword in keywords if keyword.lower() in lower)

    wc = len(answer.split())
    if wc < 15:
        score = 2
    elif wc >= 40 and generic_pos >= 2:
        score = 4
    elif wc >= 30 and generic_pos >= 1:
        score = 3
    else:
        score = 3

    if cluster_hits >= 2 and score <= 4:
        score += 1
    elif cluster_hits == 1 and score <= 3:
        score += 1

    score = max(1, min(score, 5))

    feedback_map = {
        5: "Excellent — specific and aligned with the chosen course and goals.",
        4: "Good — add one more concrete detail to strengthen credibility.",
        3: "Average — answer is acceptable but still generic.",
        2: "Weak — too vague or incomplete.",
        1: "High risk — major credibility concerns detected.",
    }

    if course_track and course_track in COURSE_PROFILES:
        student_tip = COURSE_PROFILES[course_track]["extra_tip"]
    else:
        student_tip = ANSWER_TIPS.get(category, ANSWER_TIPS["default"])

    readiness = {5: "Low risk", 4: "Moderate risk", 3: "Moderate risk", 2: "Elevated risk", 1: "High risk"}[score]

    return {
        "score": score,
        "feedback": feedback_map[score],
        "student_tip": student_tip,
        "risk_flags": [],
        "missing_points": ["More specific evidence"],
        "counsellor_note": "Bespoke scoring used (course-track aware).",
        "red_flag": False,
        "generic_pos": generic_pos,
        "cluster_hits": cluster_hits,
        "readiness": readiness,
    }

def openai_evaluate_answer(answer: str, category: str, question: str, profile: dict) -> dict:
    prompt = f"""
You are an expert UK university compliance officer conducting a Pre UKVI credibility interview.

Applicant profile:
- Name: {profile.get('name', 'Applicant')}
- Course: {profile.get('course', 'N/A')}
- University: {profile.get('university', 'N/A')}
- Home country: {profile.get('country', 'N/A')}
- Course track: {profile.get('course_track', 'N/A')}

Question category: {category}
Question: {question}

Applicant answer:
\"\"\"{answer.strip()}\"\"\"

Return compact JSON with keys:
score, feedback, student_tip, risk_flags, missing_points, readiness
"""
    response = client.responses.create(
        model="gpt-5.1-mini",
        input=prompt,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.output[0].content[0].text)
    return {
        "score": int(data.get("score", 3)),
        "feedback": data.get("feedback", "Answer evaluated."),
        "student_tip": data.get("student_tip", ANSWER_TIPS.get(category, ANSWER_TIPS["default"])),
        "risk_flags": data.get("risk_flags", []) or [],
        "missing_points": data.get("missing_points", []) or [],
        "readiness": data.get("readiness", "Moderate risk"),
    }

# Stub transcription for Student speaking mode

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    Temporary stub for audio transcription.

    Replace this with a real speech-to-text call (e.g. OpenAI Whisper)
    when you are ready. For now, it returns a placeholder transcript.
    """
    return "This is a placeholder transcript. Replace this function with real transcription."

def auto_expire_question(idx: int, category: str, question: str):
    answer_key = f"answer_{idx}"
    latest_text = st.session_state.get(answer_key, "").strip()
    st.session_state.log.append(
        {
            "Question #": idx + 1,
            "Category": category,
            "Question": question,
            "Answer": latest_text,
            "Score": 1,
            "Feedback": "Time expired before submission.",
            "Student Tip": "Give a complete answer before the timer ends.",
            "Risk Flags": "Time expired",
            "Missing Points": "Answer not submitted in time",
            "Counsellor Note": "Question auto-advanced after the timer expired.",
            "Readiness": "Elevated risk",
            "Red Flag": False,
            "Generic Positives": 0,
            "Cluster Hits": 0,
        }
    )
    st.session_state.scores.append(1)
    st.session_state.idx += 1
    pick_question()
    st.rerun()

def submit_answer(answer_text: str, idx: int, category: str, question: str):
    cleaned = answer_text.strip()
    wc = len(cleaned.split())
    if wc < DEFAULT_MIN_WORDS:
        st.warning(f"Your answer is quite short ({wc} words). Aim for at least {DEFAULT_MIN_WORDS} words.")

    start_time = st.session_state.get("question_start")
    elapsed = time.time() - start_time if start_time else None
    # relaxed paste-like detection: long answer submitted very quickly
    is_paste_like = elapsed is not None and elapsed < 15 and wc > 60

    if is_paste_like:
        st.error(
            "This answer looks pasted rather than typed. "
            "For CAS practice, please type or dictate the answer in your own words."
        )
        st.info(
            "Rephrase the response in natural sentences, as you would say it in a real interview, "
            "then submit again."
        )
        st.session_state.log.append(
            {
                "Question #": idx + 1,
                "Category": category,
                "Question": question,
                "Answer": cleaned,
                "Score": 0,
                "Feedback": "Answer flagged as pasted; scoring skipped.",
                "Student Tip": "Type your own spoken answer rather than pasting prepared text.",
                "Risk Flags": "paste_like",
                "Missing Points": "Authentic, spoken-style explanation",
                "Counsellor Note": "Answer appears pasted; student should practise answering in their own words.",
                "Readiness": "Elevated risk",
                "Red Flag": False,
                "Generic Positives": 0,
                "Cluster Hits": 0,
            }
        )

        return

    local = bespoke_score(cleaned, category, st.session_state.profile)

    if local.get("red_flag"):
        final_score = local["score"]
        st.error("This answer contains UKVI high-risk language and must be reframed.")
        st.success(f"Score: {final_score}/5 — {local['feedback']}")
        st.info(f"Student tip: {local['student_tip']}")
        if local.get("risk_flags"):
            st.warning(f"Risk flags: {', '.join(local['risk_flags'])}")

        st.session_state.scores.append(final_score)
        st.session_state.log.append(
            {
                "Question #": idx + 1,
                "Category": category,
                "Question": question,
                "Answer": cleaned,
                "Score": final_score,
                "Feedback": local["feedback"],
                "Student Tip": local["student_tip"],
                "Risk Flags": ", ".join(local.get("risk_flags", [])),
                "Missing Points": ", ".join(local.get("missing_points", [])),
                "Counsellor Note": local.get("counsellor_note", ""),
                "Readiness": local.get("readiness", "High risk"),
                "Red Flag": True,
                "Generic Positives": local.get("generic_pos", 0),
                "Cluster Hits": local.get("cluster_hits", 0),
            }
        )
        time.sleep(DEFAULT_THINK_TIME)
        st.session_state.idx += 1
        pick_question()
        st.rerun()
        return

    final_score = local["score"]
    feedback = local["feedback"]
    student_tip = local["student_tip"]
    risk_flags = local.get("risk_flags", [])
    missing_points = local.get("missing_points", [])
    readiness = local.get("readiness", "Moderate risk")

    if final_score <= 2:
        try:
            oa = openai_evaluate_answer(cleaned, category, question, st.session_state.profile)
            final_score = int(oa.get("score", final_score))
            feedback = oa.get("feedback", feedback)
            student_tip = oa.get("student_tip", student_tip)
            risk_flags = oa.get("risk_flags", risk_flags) or risk_flags
            missing_points = oa.get("missing_points", missing_points) or missing_points
            readiness = oa.get("readiness", readiness)
        except Exception as e:
            st.caption(f"OpenAI evaluation unavailable, using local scoring only. ({e})")

    st.success(f"Score: {final_score}/5 — {feedback}")
    st.info(f"Student tip: {student_tip}")
    st.caption(
        f"Signals detected: {local.get('generic_pos', 0)} generic positives, "
        f"{local.get('cluster_hits', 0)} course-track keywords."
    )
    if risk_flags:
        st.warning("Risk flags: " + ", ".join(risk_flags))
    if missing_points:
        st.caption("Missing points: " + ", ".join(missing_points))

    st.session_state.scores.append(final_score)
    st.session_state.log.append(
        {
            "Question #": idx + 1,
            "Category": category,
            "Question": question,
            "Answer": cleaned,
            "Score": final_score,
            "Feedback": feedback,
            "Student Tip": student_tip,
            "Risk Flags": ", ".join(risk_flags),
            "Missing Points": ", ".join(missing_points),
            "Counsellor Note": local.get("counsellor_note", ""),
            "Readiness": readiness,
            "Red Flag": False,
            "Generic Positives": local.get("generic_pos", 0),
            "Cluster Hits": local.get("cluster_hits", 0),
        }
    )

    time.sleep(DEFAULT_THINK_TIME)
    st.session_state.idx += 1
    pick_question()
    st.rerun()

# ------------ Sidebar ------------

init_session_state()

with st.sidebar:
    st.header("👤 Applicant Profile")

    # Mode toggle
    mode = st.radio(
        "Usage mode",
        ["Advisor (typed)", "Student (speaking)"],
        horizontal=True,
    )

    study_level = st.radio("Study level", ["UG", "PG"], horizontal=True)
    filtered_tracks = [track for track in COURSE_PROFILES.keys() if track.startswith(f"{study_level} –")]
    course_track = st.selectbox(
        "Course track",
        filtered_tracks,
        index=0 if filtered_tracks else None,
        help="Choose the closest cluster for the applicant's course.",
    )

    s_name = st.text_input("Full Name")
    s_university = st.text_input("University")
    s_course = st.text_input("Course")
    s_country = st.text_input("Home Country", value="Nigeria")
    s_experience = st.text_input("Experience", placeholder="e.g. 2 years work or study")

    c1, c2 = st.columns(2)
    with c1:
        start = st.button("Start Pre UKVI Interview", use_container_width=True, type="primary")
    with c2:
        reset = st.button("Reset Session", use_container_width=True)

    if reset:
        reset_interview_state()
        st.rerun()

    total_sections = len(QUESTION_ORDER)
    approx_minutes = total_sections * 3
    st.caption(
        f"Estimated interview duration: about {approx_minutes} minutes "
        f"({total_sections} categories, 1 question per category)."
    )

    if start:
        reset_interview_state()
        st.session_state.started = True
        st.session_state.completed = False
        st.session_state.idx = 0
        st.session_state.scores = []
        st.session_state.log = []
        st.session_state.profile = {
            "name": s_name or "Applicant",
            "university": s_university or "your university",
            "course": s_course or "your course",
            "country": s_country or "Nigeria",
            "experience": s_experience or "",
            "course_track": course_track,
        }
        pick_question()
        st.rerun()

    if st.session_state.started and not st.session_state.completed:
        remaining, t_str = time_left()
        st.caption(f"Time left this question: {t_str}")
        if remaining == 0:
            st.warning("Time is up for this question.")

# ------------ Main UI ------------

if mode == "Advisor (typed)":
    st.title("Pre UKVI Compliance Interview – Advisor Mode")
    st.caption("UKVI-aligned typed simulator with enriched feedback and compliance report for counsellors.")
else:
    st.title("Pre UKVI Compliance Interview – Student Speaking Mode")
    st.caption("UKVI-style speaking practice with live transcription and feedback on your answers.")

with st.expander("How your answers are scored"):
    st.markdown(
        """
- 5/5 – Excellent: clear, specific, and aligned with your UK course and career plan.
- 4/5 – Good: strong answer; add one more concrete detail.
- 3/5 – Average: basically correct but still generic.
- 2/5 – Weak: vague or incomplete.
- 1/5 – High risk: unclear or risky language, or UKVI red-flag phrases.

Local bespoke scoring runs first. OpenAI evaluation is used only for weak answers (score ≤ 2) without red-flag language, to enrich feedback.
        """
    )

if not st.session_state.started:
    st.info(
        f"Fill in the applicant profile on the left, choose a mode, "
        f"then click 'Start Pre UKVI Interview'. Estimated duration: about {approx_minutes} minutes."
    )
else:
    if st.session_state.completed:
        scores = st.session_state.scores
        avg = sum(scores) / len(scores) if scores else 0
        overall_verdict = verdict(avg)

        st.subheader("📊 Pre UKVI Compliance Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Applicant", st.session_state.profile.get("name", "Applicant"))
        m2.metric("Questions", len(scores))
        m3.metric("Average Score", f"{avg:.1f} / 5")
        m4.metric("Verdict", overall_verdict)

        df = pd.DataFrame(st.session_state.log)
        st.divider()
        st.dataframe(
            df[
                [
                    "Question #",
                    "Category",
                    "Score",
                    "Feedback",
                    "Student Tip",
                    "Generic Positives",
                    "Cluster Hits",
                    "Readiness",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        weak = df[df["Score"] <= 2]
        if not weak.empty:
            st.divider()
            st.subheader("⚠️ Recommended actions before CAS")

            weak_categories = sorted(set(weak["Category"]))
            st.markdown(
                "- Strengthen answers for: " + ", ".join(f"`{cat}`" for cat in weak_categories)
            )

            missing_all, risk_all = [], []
            for _, row in weak.iterrows():
                if isinstance(row.get("Missing Points"), str) and row["Missing Points"]:
                    missing_all.extend([p.strip() for p in row["Missing Points"].split(",") if p.strip()])
                if isinstance(row.get("Risk Flags"), str) and row["Risk Flags"]:
                    risk_all.extend([p.strip() for p in row["Risk Flags"].split(",") if p.strip()])

            missing_all = sorted(set(missing_all))
            risk_all = sorted(set(risk_all))

            if missing_all:
                st.markdown("**Key gaps to address:** " + ", ".join(missing_all))
            if risk_all:
                st.markdown("**Risk phrases to avoid:** " + ", ".join(risk_all))

            st.markdown(
                """
- Prepare a clear finance story with amounts, sources, how long funds are held, and evidence.
- Memorise 3–4 real modules, assessments and outcomes for your UK course.
- Practise a return-home plan: role, sector, and how this course supports it.
                """
            )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download Interview Report (CSV)", csv, "pre_ukvi_interview_report.csv", "text/csv")

    else:
        idx = st.session_state.idx
        category = st.session_state.current_category
        question = st.session_state.current_question
        total_q = len(QUESTION_ORDER)
        remaining, t_str = time_left()

        if remaining == 0 and not st.session_state.get("question_expired", False):
            st.session_state.question_expired = True
            auto_expire_question(idx, category, question)

        st.progress(idx / total_q if total_q else 0, text=f"Question {idx + 1} of {total_q}")

        if mode == "Advisor (typed)":
            left, right = st.columns([2.35, 1])

            with left:
                st.markdown(f"**Topic:** `{category}`")
                st.markdown("### Interview Question")
                st.write(question)

                st.info(QUESTION_HINTS.get(category, "Give a clear, specific answer."))
                st.caption(ANSWER_TIPS.get(category, ANSWER_TIPS["default"]))

                selected_track = st.session_state.profile.get("course_track")
                if selected_track and selected_track in COURSE_PROFILES:
                    cluster = COURSE_PROFILES[selected_track]
                    st.caption(
                        f"Course track recommendation ({selected_track}): {cluster['extra_tip']} "
                        f"Example programmes include: {cluster['examples']}."
                    )

                answer_text = st.text_area(
                    "Applicant answer",
                    key=f"answer_{idx}",
                    height=280,
                    placeholder="Type the applicant's answer here...",
                )

                st.caption(
                    "Please type the applicant's answer in your own words. "
                    "Copied text or templates will be flagged as weak."
                )

                if remaining == 0:
                    st.warning("Time is up for this question. The app will move to the next question.")

                c_submit, c_skip = st.columns(2)
                with c_submit:
                    if st.button(
                        "Submit typed answer →",
                        type="primary",
                        use_container_width=True,
                        key=f"submit_typed_{idx}",
                    ):
                        if not answer_text.strip():
                            st.warning("Please type an answer before submitting.")
                        else:
                            submit_answer(answer_text, idx, category, question)
                with c_skip:
                    if st.button(
                        "Skip Question →",
                        use_container_width=True,
                        key=f"skip_{idx}",
                    ):
                        st.session_state.log.append(
                            {
                                "Question #": idx + 1,
                                "Category": category,
                                "Question": question,
                                "Answer": answer_text.strip(),
                                "Score": 1,
                                "Feedback": "Question skipped by user.",
                                "Student Tip": "Attempt every question with a direct and specific answer.",
                                "Risk Flags": "Skipped",
                                "Missing Points": "No complete response provided",
                                "Counsellor Note": "User skipped this question.",
                                "Readiness": "Elevated risk",
                                "Red Flag": False,
                                "Generic Positives": 0,
                                "Cluster Hits": 0,
                            }
                        )
                        st.session_state.scores.append(1)
                        st.session_state.idx += 1
                        pick_question()
                        st.rerun()

            with right:
                timer_class = "timer-green"
                if remaining <= 60:
                    timer_class = "timer-amber"
                if remaining <= 30:
                    timer_class = "timer-red"

                st.markdown(
                    f"""
                    <div class="timer-card">
                        <div class="timer-value {timer_class}">{t_str}</div>
                        <div class="timer-label">Time left</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.subheader("Live Scores")
                for i, sc in enumerate(st.session_state.scores):
                    bar = "█" * sc + "░" * (5 - sc)
                    cat = QUESTION_ORDER[i] if i < len(QUESTION_ORDER) else ""
                    row = st.session_state.log[i]
                    flag = " 🚩" if row.get("Red Flag") else ""
                    gp = row.get("Generic Positives", 0)
                    ch = row.get("Cluster Hits", 0)
                    st.markdown(f"`Q{i+1}` {bar} **{sc}/5**{flag}  \n_{cat}_")
                    st.caption(f"Signals: {gp} generic positives, {ch} cluster hits.")

                st.divider()
                profile = st.session_state.profile
                st.markdown(f"👤 **{profile.get('name', 'Applicant')}**")
                st.markdown(f"🎓 {profile.get('course', '')}")
                st.markdown(f"🏫 {profile.get('university', '')}")
                st.markdown(f"🌍 {profile.get('country', '')}")
                if profile.get("experience"):
                    st.markdown(f"💼 {profile['experience']}")
                if profile.get("course_track"):
                    st.markdown(f"📚 Track: {profile['course_track']}")

        else:  # Student speaking mode
            st.markdown(f"**Topic:** `{category}`")
            st.markdown("### Interview Question")
            st.write(question)

            st.info("Speak naturally as you would in a real UKVI interview. Avoid memorised scripts.")
            st.caption("You have about 3 minutes. Click the mic, speak your answer, then submit.")

            try:
                from audio_recorder_streamlit import audio_recorder
            except ImportError:
                st.error("Audio recorder package not installed. Please ask your advisor to enable speaking mode.")
                remaining, t_str = time_left()
                st.caption(f"Time left: {t_str}")
                st.stop()

            audio_bytes = audio_recorder(
                pause_threshold=2.0,
                energy_threshold=0.01,
                sample_rate=16000,
            )

            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                if st.button(
                    "Submit spoken answer →",
                    use_container_width=True,
                    key=f"submit_spoken_{idx}",
                ):
                    try:
                        with st.spinner("Transcribing and scoring your spoken answer..."):
                            transcript = transcribe_audio_bytes(audio_bytes)

                        st.markdown("**Transcript (what UKVI would hear):**")
                        st.write(transcript)

                        cleaned = transcript.strip()
                        local = bespoke_score(cleaned, category, st.session_state.profile)
                        final_score = local["score"]
                        feedback = local["feedback"]
                        student_tip = local["student_tip"]

                        if final_score <= 2:
                            try:
                                oa = openai_evaluate_answer(cleaned, category, question, st.session_state.profile)
                                final_score = int(oa.get("score", final_score))
                                feedback = oa.get("feedback", feedback)
                                student_tip = oa.get("student_tip", student_tip)
                            except Exception:
                                pass

                        st.markdown(f"**Score:** {final_score}/5 — {feedback}")
                        st.caption(f"Tip: {student_tip}")

                        st.session_state.scores.append(final_score)
                        st.session_state.log.append(
                            {
                                "Question #": idx + 1,
                                "Category": category,
                                "Question": question,
                                "Answer": cleaned,
                                "Score": final_score,
                                "Feedback": feedback,
                                "Student Tip": student_tip,
                                "Risk Flags": ", ".join(local.get("risk_flags", [])),
                                "Missing Points": ", ".join(local.get("missing_points", [])),
                                "Counsellor Note": local.get("counsellor_note", ""),
                                "Readiness": local.get("readiness", "Moderate risk"),
                                "Red Flag": local.get("red_flag", False),
                                "Generic Positives": local.get("generic_pos", 0),
                                "Cluster Hits": local.get("cluster_hits", 0),
                            }
                        )

                        time.sleep(DEFAULT_THINK_TIME)
                        st.session_state.idx += 1
                        pick_question()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")

            remaining, t_str = time_left()
            st.caption(f"Time left: {t_str}")toggle and shells out a Student speaking page
