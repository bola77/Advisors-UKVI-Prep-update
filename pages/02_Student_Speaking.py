# pages/02_Student_Speaking.py

import time
import streamlit as st

from advisors_theme import apply_advisors_theme
from questions import (
    QUESTION_ORDER,
    QUESTION_HINTS,
    ANSWER_TIPS,
    COURSE_PROFILES,
    DEFAULT_THINK_TIME,
)
from session import (
    init_session_state,
    reset_interview_state,
    pick_question,
    time_left,
    verdict,
)
from scoring import bespoke_score, openai_evaluate_answer

try:
    from streamlit_mic_recorder import mic_recorder
except ImportError:
    mic_recorder = None


# ------------ Page setup ------------

st.set_page_config(
    page_title="Pre UKVI Compliance Interview – Student Speaking",
    page_icon="🎓",
    layout="wide",
)

apply_advisors_theme()

st.markdown(
    """
    <style>
    .big-timer-wrap {
        border-radius: 22px;
        padding: 1.25rem 1rem 1rem 1rem;
        background: rgba(15, 23, 42, 0.06);
        text-align: center;
        margin: 0.5rem 0 1rem 0;
        border: 1px solid rgba(15, 23, 42, 0.08);
    }
    .big-timer-label {
        font-size: 1rem;
        opacity: 0.75;
        margin-bottom: 0.35rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .big-timer-value {
        font-size: 4.8rem;
        line-height: 1;
        font-weight: 900;
        margin: 0;
    }
    .big-timer-green { color: #15803d; }
    .big-timer-amber { color: #d97706; }
    .big-timer-red { color: #dc2626; }
    .big-timer-note {
        margin-top: 0.35rem;
        font-size: 0.95rem;
        opacity: 0.75;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Pre UKVI Compliance Interview – Student Speaking Mode")
st.caption("Speak your answers as in a real UKVI interview; get instant feedback.")


# ------------ Simple transcription stub ------------

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    Replace this stub with real speech-to-text later.
    """
    return "This is a placeholder transcript. Replace with real transcription."


# ------------ Session state ------------

init_session_state(st)

if "spoken_audio_bytes" not in st.session_state:
    st.session_state.spoken_audio_bytes = None


# ------------ Live timer fragment ------------

@st.fragment(run_every="1s")
def live_timer():
    if st.session_state.get("started") and not st.session_state.get("completed"):
        remaining, t_str = time_left(st)

        if remaining > 60:
            timer_class = "big-timer-green"
        elif remaining > 20:
            timer_class = "big-timer-amber"
        else:
            timer_class = "big-timer-red"

        st.markdown(
            f"""
            <div class="big-timer-wrap">
                <div class="big-timer-label">Time left for this question</div>
                <div class="big-timer-value {timer_class}">{t_str}</div>
                <div class="big-timer-note">Try to answer clearly before time runs out.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if remaining == 0:
            st.warning("Time is up for this question.")


# ------------ Sidebar: applicant profile & controls ------------

with st.sidebar:
    st.header("👤 Applicant Profile")

    study_level = st.radio("Study level", ["UG", "PG"], horizontal=True)

    filtered_tracks = [
        track for track in COURSE_PROFILES.keys()
        if track.startswith(f"{study_level} –")
    ]
    course_track = st.selectbox(
        "Course track",
        filtered_tracks,
        index=0 if filtered_tracks else None,
        help="Choose the closest cluster for your course.",
    )

    s_name = st.text_input("Full Name")
    s_university = st.text_input("University")
    s_course = st.text_input("Course")
    s_country = st.text_input("Home Country", value="Nigeria")
    s_experience = st.text_input("Experience", placeholder="e.g. 2 years work or study")

    c1, c2 = st.columns(2)
    with c1:
        start = st.button(
            "Start Speaking Interview",
            use_container_width=True,
            type="primary",
        )
    with c2:
        reset = st.button(
            "Reset Session",
            use_container_width=True,
        )

    if reset:
        reset_interview_state(st)
        st.session_state.spoken_audio_bytes = None
        st.rerun()

    total_sections = len(QUESTION_ORDER)
    approx_minutes = total_sections * 3
    st.caption(
        f"Estimated interview duration: about {approx_minutes} minutes "
        f"({total_sections} categories, 1 question per category)."
    )

    if start:
        reset_interview_state(st)
        st.session_state.started = True
        st.session_state.completed = False
        st.session_state.idx = 0
        st.session_state.scores = []
        st.session_state.log = []
        st.session_state.spoken_audio_bytes = None
        st.session_state.profile = {
            "name": s_name or "Applicant",
            "university": s_university or "your university",
            "course": s_course or "your course",
            "country": s_country or "Nigeria",
            "experience": s_experience or "",
            "course_track": course_track,
        }
        pick_question(st)
        st.rerun()


# ------------ Scoring explanation ------------

with st.expander("How your spoken answers are scored"):
    st.markdown(
        """
- 5/5 – Excellent: clear, specific, and aligned with your UK course and career plan.
- 4/5 – Good: strong answer; add one more concrete detail.
- 3/5 – Average: basically correct but still generic.
- 2/5 – Weak: vague or incomplete.
- 1/5 – High risk: unclear or risky language, or UKVI red-flag phrases.

Your transcript (what the visa officer hears) is scored using the same logic as the typed mode.
        """
    )


# ------------ Main speaking UI ------------

if not st.session_state.started:
    st.info(
        f"Fill in your profile on the left, then click 'Start Speaking Interview'. "
        f"Estimated duration: about {approx_minutes} minutes."
    )

elif st.session_state.completed:
    scores = st.session_state.scores
    avg = sum(scores) / len(scores) if scores else 0
    overall_verdict = verdict(avg)

    st.subheader("📊 Speaking Interview Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Applicant", st.session_state.profile.get("name", "Applicant"))
    m2.metric("Questions", len(scores))
    m3.metric("Average Score", f"{avg:.1f} / 5")
    m4.metric("Verdict", overall_verdict)

    if st.session_state.log:
        import pandas as pd

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
                    "Readiness",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        export_cols = [
            "Question #",
            "Category",
            "Question",
            "Answer",
            "Score",
            "Feedback",
            "Student Tip",
            "Risk Flags",
            "Missing Points",
            "Counsellor Note",
            "Readiness",
        ]
        csv = df[export_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Download Speaking Interview Report (CSV)",
            csv,
            "pre_ukvi_speaking_report.csv",
            "text/csv",
        )

else:
    idx = st.session_state.idx
    category = st.session_state.current_category
    question = st.session_state.current_question
    total_q = len(QUESTION_ORDER)
    remaining, _ = time_left(st)

    if remaining == 0 and not st.session_state.get("question_expired", False):
        st.session_state.question_expired = True
        st.session_state.log.append(
            {
                "Question #": idx + 1,
                "Category": category,
                "Question": question,
                "Answer": "",
                "Score": 1,
                "Feedback": "Time expired before answering.",
                "Student Tip": "Start speaking earlier and give a complete answer.",
                "Risk Flags": "Time expired",
                "Missing Points": "No spoken response captured",
                "Counsellor Note": "Question auto-advanced after the timer expired.",
                "Readiness": "Elevated risk",
                "Red Flag": False,
                "Generic Positives": 0,
                "Cluster Hits": 0,
            }
        )
        st.session_state.scores.append(1)
        st.session_state.spoken_audio_bytes = None
        st.session_state.idx += 1
        pick_question(st)
        st.rerun()

    st.progress(
        idx / total_q if total_q else 0,
        text=f"Question {idx + 1} of {total_q}",
    )

    st.markdown(f"**Topic:** `{category}`")
    st.markdown("### Interview Question")
    st.write(question)

    live_timer()

    st.info("Speak naturally, as you would with a visa officer. Avoid memorised scripts.")
    st.caption(QUESTION_HINTS.get(category, "Give a clear, specific answer."))
    st.caption(ANSWER_TIPS.get(category, ANSWER_TIPS["default"]))

    selected_track = st.session_state.profile.get("course_track")
    if selected_track and selected_track in COURSE_PROFILES:
        cluster = COURSE_PROFILES[selected_track]
        st.caption(
            f"Course track recommendation ({selected_track}): {cluster['extra_tip']} "
            f"Example programmes include: {cluster['examples']}."
        )

    st.info("Record a short answer, then click submit.")

    if mic_recorder is None:
        st.warning("Microphone recorder is not installed in this deployment.")
    else:
        audio_data = mic_recorder(
            start_prompt="🎙️ Start recording",
            stop_prompt="⏹️ Stop recording",
            just_once=True,
            use_container_width=True,
            key=f"mic_{idx}",
        )

        if audio_data and isinstance(audio_data, dict):
            new_audio = audio_data.get("bytes")
            if new_audio:
                st.session_state.spoken_audio_bytes = new_audio
                st.caption(
                    f"Recorded audio ready. Sample rate: "
                    f"{audio_data.get('sample_rate', 'unknown')} Hz."
                )

    audio_bytes = st.session_state.spoken_audio_bytes

    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")

    typed_fallback = st.text_area(
        "Fallback: type your answer here if microphone capture fails",
        height=120,
        key=f"typed_fallback_{idx}",
    )

    if st.button(
        "Submit spoken answer →",
        use_container_width=True,
        key=f"submit_spoken_{idx}",
    ):
        try:
            if audio_bytes:
                with st.spinner("Transcribing and scoring your spoken answer..."):
                    transcript = transcribe_audio_bytes(audio_bytes)
                cleaned = transcript.strip()
            else:
                cleaned = typed_fallback.strip()

            if not cleaned:
                st.warning("Please record a short answer or type your response.")
                st.stop()

            st.markdown("**Transcript (what UKVI would hear):**")
            st.write(cleaned)

            local = bespoke_score(cleaned, category, st.session_state.profile)
            final_score = local["score"]
            feedback = local["feedback"]
            student_tip = local["student_tip"]
            risk_flags = local.get("risk_flags", [])
            missing_points = local.get("missing_points", [])
            readiness = local.get("readiness", "Moderate risk")

            if not local.get("red_flag") and final_score <= 2:
                try:
                    oa = openai_evaluate_answer(
                        cleaned, category, question, st.session_state.profile
                    )
                    final_score = int(oa.get("score", final_score))
                    feedback = oa.get("feedback", feedback)
                    student_tip = oa.get("student_tip", student_tip)
                    risk_flags = oa.get("risk_flags", risk_flags) or risk_flags
                    missing_points = oa.get("missing_points", missing_points) or missing_points
                    readiness = oa.get("readiness", readiness)
                except Exception as e:
                    st.caption(
                        f"Model-based evaluation unavailable, using local scoring only. ({e})"
                    )

            if local.get("red_flag"):
                st.error("Your answer contains high-risk language and must be reframed.")

            st.markdown(f"**Score:** {final_score}/5 — {feedback}")
            st.caption(f"Tip: {student_tip}")
            st.caption(
                f"Signals: {local.get('generic_pos', 0)} generic positives, "
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
                    "Red Flag": local.get("red_flag", False),
                    "Generic Positives": local.get("generic_pos", 0),
                    "Cluster Hits": local.get("cluster_hits", 0),
                }
            )

            st.session_state.spoken_audio_bytes = None
            time.sleep(DEFAULT_THINK_TIME)
            st.session_state.idx += 1
            pick_question(st)
            st.rerun()

        except Exception as e:
            st.error(f"Transcription or scoring failed: {e}")
