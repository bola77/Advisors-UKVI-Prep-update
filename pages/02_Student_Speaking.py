# pages/02_Student_Speaking.py

import time
import os
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

from advisors_theme import apply_advisors_theme
from questions import (
    QUESTION_ORDER,
    QUESTION_HINTS,
    ANSWER_TIPS,
    COURSE_PROFILES,
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


# ------------------------
# Page setup and styling
# ------------------------

st.set_page_config(
    page_title="Pre UKVI Compliance Interview – Student Speaking",
    page_icon="🎓",
    layout="wide",
)

st.markdown(
    """
    <style>
        div[data-testid="stToolbar"] {display: none !important;}
        button[kind="header"] {display: none !important;}
        .stDeployButton {display: none !important;}
        [data-testid="stStatusWidget"] {display: none !important;}
        header[data-testid="stHeader"] {background: white !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .block-container {padding-top: 1.2rem !important;}
        .top-right-cover {
            position: fixed;
            top: 0;
            right: 0;
            width: 260px;
            height: 70px;
            background: white;
            z-index: 999999;
            pointer-events: none;
        }
    </style>
    <div class="top-right-cover"></div>
    """,
    unsafe_allow_html=True,
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
            color: #15803d;
        }
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


# ------------------------
# Helper functions
# ------------------------

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)

    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = "recording.wav"

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_buffer,
        language="en",
    )
    text = getattr(transcript, "text", "") or ""
    return text.strip()


def render_js_timer():
    remaining = st.session_state.get("current_remaining_secs", 0)
    question_idx = st.session_state.get("current_question_idx", 0)
    dom_id = f"ukvi-timer-{question_idx}"

    html = f"""
    <html>
    <head>
      <style>
        body {{
          margin: 0;
          font-family: sans-serif;
          background: transparent;
        }}
        .big-timer-wrap {{
          border-radius: 22px;
          padding: 1.25rem 1rem 1rem 1rem;
          background: rgba(15, 23, 42, 0.06);
          text-align: center;
          margin: 0;
          border: 1px solid rgba(15, 23, 42, 0.08);
        }}
        .big-timer-label {{
          font-size: 1rem;
          opacity: 0.75;
          margin-bottom: 0.35rem;
          font-weight: 600;
          letter-spacing: 0.02em;
        }}
        .big-timer-value {{
          font-size: 4.8rem;
          line-height: 1;
          font-weight: 900;
          margin: 0;
          color: #15803d;
        }}
        .big-timer-note {{
          margin-top: 0.35rem;
          font-size: 0.95rem;
          opacity: 0.75;
        }}
      </style>
    </head>
    <body>
      <div id="{dom_id}" class="big-timer-wrap">
        <div class="big-timer-label">Time left for this question</div>
        <div id="{dom_id}-value" class="big-timer-value">--:--</div>
        <div id="{dom_id}-note" class="big-timer-note">
          Speak clearly and support your answer with specific details.
        </div>
      </div>

      <script>
        (function() {{
          const valueEl = document.getElementById("{dom_id}-value");
          const noteEl = document.getElementById("{dom_id}-note");
          let secs = {remaining};

          function updateDisplay() {{
            if (secs < 0) secs = 0;
            const mm = Math.floor(secs / 60);
            const ss = secs % 60;
            valueEl.textContent =
              mm.toString().padStart(2, "0") + ":" + ss.toString().padStart(2, "0");

            if (secs > 90) {{
              valueEl.style.color = "#15803d";
              noteEl.textContent = "Speak clearly and support your answer with specific details.";
            }} else if (secs > 30) {{
              valueEl.style.color = "#d97706";
              noteEl.textContent = "Add one final concrete point and prepare to submit.";
            }} else {{
              valueEl.style.color = "#dc2626";
              noteEl.textContent = "Finish your answer and click submit.";
            }}
          }}

          updateDisplay();

          const intervalId = setInterval(function() {{
            secs = secs - 1;
            updateDisplay();
            if (secs <= 0) {{
              clearInterval(intervalId);
            }}
          }}, 1000);
        }})();
      </script>
    </body>
    </html>
    """
    components.html(html, height=170)


# ------------------------
# Session state init
# ------------------------

init_session_state(st)

if "spoken_audio_bytes" not in st.session_state:
    st.session_state.spoken_audio_bytes = None
if "pending_audio_bytes" not in st.session_state:
    st.session_state.pending_audio_bytes = None
if "pending_typed_answer" not in st.session_state:
    st.session_state.pending_typed_answer = ""
if "is_submitting" not in st.session_state:
    st.session_state.is_submitting = False
if "current_remaining_secs" not in st.session_state:
    st.session_state.current_remaining_secs = 0
if "current_question_idx" not in st.session_state:
    st.session_state.current_question_idx = 0
if "audio_error_message" not in st.session_state:
    st.session_state.audio_error_message = ""
if "saved_to_master_reports" not in st.session_state:
    st.session_state.saved_to_master_reports = False
if "show_feedback_gate" not in st.session_state:
    st.session_state.show_feedback_gate = False


# ------------------------
# Sidebar profile, including study level & course track
# ------------------------

with st.sidebar:
    st.header("Applicant Profile")

    study_level = st.radio("Study level", ["UG", "PG"], horizontal=True)

    all_tracks = list(COURSE_PROFILES.keys())
    filtered_tracks = [track for track in all_tracks if track.startswith(study_level)]
    if not filtered_tracks:
        filtered_tracks = all_tracks

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
        reset = st.button("Reset Session", use_container_width=True)

    if reset:
        reset_interview_state(st)
        st.session_state.spoken_audio_bytes = None
        st.session_state.pending_audio_bytes = None
        st.session_state.pending_typed_answer = ""
        st.session_state.is_submitting = False
        st.session_state.audio_error_message = ""
        st.session_state.saved_to_master_reports = False
        st.session_state.show_feedback_gate = False
        st.rerun()

    total_sections = len(QUESTION_ORDER)
    approx_minutes = total_sections * 4
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
    st.session_state.pending_audio_bytes = None
    st.session_state.pending_typed_answer = ""
    st.session_state.is_submitting = False
    st.session_state.audio_error_message = ""
    st.session_state.saved_to_master_reports = False
    st.session_state.show_feedback_gate = False

    st.session_state.profile = {
        "name": s_name or "Applicant",
        "university": s_university or "your university",
        "course": s_course or "your course",
        "country": s_country or "Nigeria",
        "experience": s_experience or "",
        "course_track": course_track,
        "study_level": study_level,
    }

    pick_question(st)
    st.rerun()


# ------------------------
# Scoring explainer
# ------------------------

with st.expander("How your spoken answers are scored"):
    st.markdown(
        """
- **5/5** Excellent — clear, specific, credible, and well aligned with your course and future plans.
- **4/5** Good — relevant and believable, but still needs one or two stronger details.
- **3/5** Average — acceptable, but still generic or underdeveloped.
- **2/5** Weak — vague, incomplete, or poorly supported.
- **1/5** High risk — serious credibility, clarity, or red-flag concerns.

Your answer is assessed on relevance, specificity, credibility, and clarity.
        """
    )


# ------------------------
# Main flow
# ------------------------

if not st.session_state.started:
    total_sections = len(QUESTION_ORDER)
    approx_minutes = total_sections * 4
    st.info(
        f"Fill in your profile on the left, then click Start Speaking Interview. "
        f"Estimated duration: about {approx_minutes} minutes."
    )

elif st.session_state.completed:
    scores = st.session_state.scores
    avg = sum(scores) / len(scores) if scores else 0
    overall_verdict = verdict(avg)

    st.subheader("Speaking Interview Summary")

    profile = st.session_state.get("profile", {})
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Applicant", profile.get("name", "Applicant"))
    m2.metric("Study level", profile.get("study_level", "UG"))
    m3.metric("Questions", len(scores))
    m4.metric("Average Score", f"{avg:.1f} / 5")

    if st.session_state.log:
        reports_file = "data/all_student_reports.csv"
        os.makedirs("data", exist_ok=True)

        df = pd.DataFrame(st.session_state.log.copy())

        applicant_name = profile.get("name", "Applicant")
        university = profile.get("university", "")
        course = profile.get("course", "")
        country = profile.get("country", "")
        course_track = profile.get("course_track", "")
        study_level = profile.get("study_level", "UG")
        session_identifier = f"{applicant_name}-{int(time.time())}"

        df.insert(0, "Applicant", applicant_name)
        df.insert(1, "University", university)
        df.insert(2, "Course", course)
        df.insert(3, "Country", country)
        df.insert(4, "Study Level", study_level)
        df.insert(5, "Course Track", course_track)
        df.insert(6, "Session ID", session_identifier)

        expected_columns = [
            "Applicant",
            "University",
            "Course",
            "Country",
            "Study Level",
            "Course Track",
            "Session ID",
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
            "Red Flag",
            "Generic Positives",
            "Cluster Hits",
            "Relevance",
            "Specificity",
            "Credibility",
            "Clarity",
            "Better Version",
        ]

        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""

        df = df[expected_columns]

        if not st.session_state.saved_to_master_reports:
            file_exists = os.path.exists(reports_file)
            file_has_content = file_exists and os.path.getsize(reports_file) > 0
            df.to_csv(
                reports_file,
                mode="a",
                header=not file_has_content,
                index=False,
            )
            st.session_state.saved_to_master_reports = True

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
                    "Relevance",
                    "Specificity",
                    "Credibility",
                    "Clarity",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Speaking Interview Report CSV",
            csv,
            "pre_ukvi_speaking_report.csv",
            "text/csv",
        )

else:
    idx = st.session_state.idx
    category = st.session_state.current_category
    question = st.session_state.current_question
    total_q = len(QUESTION_ORDER)

    remaining, _ = time_left(st)  # 3 + 1 minutes from session.py
    st.session_state.current_remaining_secs = remaining
    st.session_state.current_question_idx = idx

    st.progress(idx / total_q if total_q else 0, text=f"Question {idx + 1} of {total_q}")
    st.markdown(f"### Topic: {category}")
    st.markdown("#### Interview Question")
    st.write(question)

    if not st.session_state.is_submitting:
        render_js_timer()

    st.caption("You have about 4 minutes per answer. Use the extra time to add specific evidence and clear reasons.")
    st.info("Speak naturally, as you would with a visa officer. Avoid memorised scripts.")
    st.caption(QUESTION_HINTS.get(category, "Give a clear, specific answer."))
    st.caption(ANSWER_TIPS.get(category, ANSWER_TIPS["default"]))

    selected_track = st.session_state.profile.get("course_track")
    if selected_track and selected_track in COURSE_PROFILES:
        cluster = COURSE_PROFILES[selected_track]
        st.caption(
            f"Course track recommendation: {selected_track}. "
            f"{cluster['extra_tip']} Example programmes include: {cluster['examples']}."
        )

    st.info("Click the recorder below to start speaking, then click it again to stop.")
    st.caption("For reliability, keep recordings short. If recording fails, type your answer in the box below.")

    if st.session_state.audio_error_message:
        st.warning(st.session_state.audio_error_message)

    submit_now = st.button(
        "Submit spoken answer",
        use_container_width=True,
        key=f"submitspoken{idx}",
        type="primary",
    )

    if mic_recorder is None:
        st.warning("Microphone recorder is not installed in this deployment.")
    else:
        audio_data = mic_recorder(
            start_prompt="🎙️ Click to start recording",
            stop_prompt="⏹️ Click to stop recording",
            just_once=True,
            use_container_width=True,
            key=f"mic{idx}",
        )

        if audio_data and isinstance(audio_data, dict):
            new_audio = audio_data.get("bytes")
            sr = audio_data.get("sample_rate", "unknown")
            audio_error = audio_data.get("error")

            if audio_error:
                st.session_state.spoken_audio_bytes = None
                st.session_state.audio_error_message = (
                    f"Recording failed: {audio_error}. Please type your answer below."
                )

            elif new_audio and isinstance(new_audio, (bytes, bytearray)):
                st.session_state.spoken_audio_bytes = bytes(new_audio)
                st.session_state.audio_error_message = ""
                st.success(f"Recorded audio ready. Sample rate: {sr} Hz.")

            else:
                st.session_state.spoken_audio_bytes = None
                st.session_state.audio_error_message = (
                    "Recording format was not recognised. Please type your answer below and submit."
                )

    audio_bytes = st.session_state.spoken_audio_bytes
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")

    st.text_area(
        "Fallback: type your answer here if microphone capture fails",
        height=120,
        key=f"typedfallback{idx}",
    )

    if submit_now:
        st.session_state.pending_audio_bytes = st.session_state.spoken_audio_bytes
        st.session_state.pending_typed_answer = st.session_state.get(
            f"typedfallback{idx}", ""
        ).strip()
        st.session_state.is_submitting = True
        st.session_state.show_feedback_gate = False
        st.rerun()

    if st.session_state.is_submitting:
        st.info("Processing your answer...")

        try:
            audio_bytes = st.session_state.pending_audio_bytes
            typed_fallback = st.session_state.pending_typed_answer
            cleaned = ""

            if audio_bytes:
                try:
                    with st.spinner("Transcribing and scoring your spoken answer..."):
                        transcript = transcribe_audio_bytes(audio_bytes)
                    cleaned = (transcript or "").strip()
                except Exception as transcribe_error:
                    st.session_state.audio_error_message = (
                        f"Audio could not be processed: {transcribe_error}. "
                        f"Typed answer will be used if provided."
                    )

            if not cleaned:
                cleaned = typed_fallback.strip()

            if not cleaned:
                cleaned = ""
                st.error("No usable spoken or typed answer was captured for this question.")

            st.markdown("### Transcript (what UKVI would hear)")
            st.write(cleaned if cleaned else "_No transcript captured._")

            local = bespoke_score(cleaned, category, st.session_state.profile)

            final_score = local["score"]
            feedback = local["feedback"]
            student_tip = local["student_tip"]
            risk_flags = local.get("risk_flags", [])
            missing_points = local.get("missing_points", [])
            readiness = local.get("readiness", "Moderate risk")
            dimension_scores = local.get("dimension_scores", {})
            better_version = local.get("better_version", "")
            counsellor_note = local.get("counsellor_note", "")
            red_flag = local.get("red_flag", False)

            if not cleaned:
                final_score = 1
                feedback = "No usable response was captured for this question."
                student_tip = "Keep your recording shorter, or type your answer if recording fails."
                risk_flags = list(set(risk_flags + ["No valid audio submission"]))
                missing_points = list(set(missing_points + ["No usable spoken or typed response"]))
                readiness = "Elevated risk"
                dimension_scores = {
                    "relevance": 1,
                    "specificity": 1,
                    "credibility": 1,
                    "clarity": 1,
                }
                better_version = "Answer directly in your own words and add one clear reason plus one concrete detail."

            if not red_flag:
                try:
                    oa = openai_evaluate_answer(
                        cleaned,
                        category,
                        question,
                        st.session_state.profile,
                    )
                    final_score = int(oa.get("score", final_score))
                    feedback = oa.get("feedback", feedback)
                    student_tip = oa.get("student_tip", student_tip)
                    risk_flags = oa.get("risk_flags", risk_flags) or risk_flags
                    missing_points = oa.get("missing_points", missing_points) or missing_points
                    readiness = oa.get("readiness", readiness)
                    dimension_scores = oa.get("dimension_scores", dimension_scores) or dimension_scores
                    better_version = oa.get("better_version", better_version) or better_version
                except Exception as e:
                    st.caption(
                        f"Model-based evaluation unavailable, using local scoring only. ({e})"
                    )

            if red_flag:
                st.error("Your answer contains high-risk language and must be reframed.")

            st.markdown(f"### Score: {final_score}/5")
            st.write(feedback)
            st.caption(f"Tip: {student_tip}")

            strengths = []
            if local.get("cluster_hits", 0) > 0:
                strengths.append("You referenced course-related details.")
            if local.get("generic_pos", 0) > 0:
                strengths.append("Your answer included positive intent signals.")
            if dimension_scores.get("clarity", 0) >= 4:
                strengths.append("Your answer was clear and easy to follow.")
            if dimension_scores.get("credibility", 0) >= 4:
                strengths.append("Your response sounded broadly credible.")

            if strengths:
                st.success("What worked: " + " ".join(strengths[:2]))

            if missing_points:
                st.warning("What is missing: " + ", ".join(missing_points))

            if risk_flags:
                st.error("Risk flags: " + ", ".join(risk_flags))

            if dimension_scores:
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Relevance", dimension_scores.get("relevance", 0))
                d2.metric("Specificity", dimension_scores.get("specificity", 0))
                d3.metric("Credibility", dimension_scores.get("credibility", 0))
                d4.metric("Clarity", dimension_scores.get("clarity", 0))

            if better_version:
                st.info(f"Stronger example answer: {better_version}")

            st.caption(
                f"Signals: {local.get('generic_pos', 0)} generic positives, "
                f"{local.get('cluster_hits', 0)} course-track keywords."
            )

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
                    "Counsellor Note": counsellor_note,
                    "Readiness": readiness,
                    "Red Flag": red_flag,
                    "Generic Positives": local.get("generic_pos", 0),
                    "Cluster Hits": local.get("cluster_hits", 0),
                    "Relevance": dimension_scores.get("relevance", ""),
                    "Specificity": dimension_scores.get("specificity", ""),
                    "Credibility": dimension_scores.get("credibility", ""),
                    "Clarity": dimension_scores.get("clarity", ""),
                    "Better Version": better_version,
                }
            )

            st.session_state.spoken_audio_bytes = None
            st.session_state.pending_audio_bytes = None
            st.session_state.pending_typed_answer = ""
            st.session_state.is_submitting = False
            st.session_state.audio_error_message = ""
            st.session_state.show_feedback_gate = True

        except Exception as e:
            st.session_state.is_submitting = False
            st.session_state.pending_audio_bytes = None
            st.session_state.pending_typed_answer = ""
            st.error(f"Transcription or scoring failed: {e}")

    if st.session_state.show_feedback_gate:
        if st.button(
            "Continue to next question",
            key=f"nextq_{idx}",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.show_feedback_gate = False
            st.session_state.idx += 1
            pick_question(st)
            st.rerun()
        st.stop()
