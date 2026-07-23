# pages/01_Advisor_Interview.py

import time
import json

import pandas as pd
import streamlit as st

from advisors_theme import apply_advisors_theme
from questions import (
    QUESTION_ORDER,
    QUESTION_HINTS,
    ANSWER_TIPS,
    COURSE_PROFILES,
    DEFAULT_THINK_TIME,
    DEFAULT_MIN_WORDS,
)
from session import (
    init_session_state,
    reset_interview_state,
    pick_question,
    time_left,
    verdict,
)
from scoring import bespoke_score, openai_evaluate_answer


# ------------ Page setup ------------

st.set_page_config(
    page_title="Pre UKVI Compliance Interview – Advisor",
    page_icon="🎓",
    layout="wide",
)

apply_advisors_theme()

st.title("Pre UKVI Compliance Interview – Advisor Mode")
st.caption("Typed mock interview with scoring and coaching insights for counsellors.")


# ------------ Sidebar: applicant profile & controls ------------

init_session_state(st)

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
        help="Choose the closest cluster for the applicant's course.",
    )

    s_name = st.text_input("Full Name")
    s_university = st.text_input("University")
    s_course = st.text_input("Course")
    s_country = st.text_input("Home Country", value="Nigeria")
    s_experience = st.text_input("Experience", placeholder="e.g. 2 years work or study")

    c1, c2 = st.columns(2)
    with c1:
        start = st.button(
            "Start Pre UKVI Interview",
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
        st.experimental_rerun()

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
        st.session_state.profile = {
            "name": s_name or "Applicant",
            "university": s_university or "your university",
            "course": s_course or "your course",
            "country": s_country or "Nigeria",
            "experience": s_experience or "",
            "course_track": course_track,
        }
        pick_question(st)
        st.experimental_rerun()

    if st.session_state.started and not st.session_state.completed:
        remaining, t_str = time_left(st)
        st.caption(f"Time left this question: {t_str}")
        if remaining == 0:
            st.warning("Time is up for this question.")


# ------------ Main advisor UI ------------

with st.expander("How answers are scored"):
    st.markdown(
        """
- 5/5 – Excellent: clear, specific, and aligned with the UK course and career plan.
- 4/5 – Good: strong answer; add one more concrete detail.
- 3/5 – Average: basically correct but still generic.
- 2/5 – Weak: vague or incomplete.
- 1/5 – High risk: unclear or risky language, or UKVI red-flag phrases.

Local bespoke scoring runs first. Model-based evaluation is used only for weak answers (score ≤ 2)
without high-risk language, to enrich feedback.
        """
    )

if not st.session_state.started:
    st.info(
        f"Fill in the applicant profile on the left, "
        f"then click 'Start Pre UKVI Interview'. "
        f"Estimated duration: about {approx_minutes} minutes."
    )
elif st.session_state.completed:
    # Summary view
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

    # Category-level performance for advisors
    if not df.empty:
        cat_summary = (
            df.groupby("Category")["Score"]
            .agg(["count", "mean"])
            .reset_index()
            .rename(columns={"count": "Questions", "mean": "Average Score"})
        )
        st.divider()
        st.subheader("Category performance")
        st.dataframe(cat_summary, use_container_width=True, hide_index=True)

        weak_cats = cat_summary[cat_summary["Average Score"] <= 3]["Category"].tolist()
        if weak_cats:
            st.markdown(
                "**Weak categories to revisit:** " +
                ", ".join(f"`{c}`" for c in weak_cats)
            )

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
            "- Strengthen answers for: " +
            ", ".join(f"`{cat}`" for cat in weak_categories)
        )

        missing_all, risk_all = [], []
        for _, row in weak.iterrows():
            if isinstance(row.get("Missing Points"), str) and row["Missing Points"]:
                missing_all.extend(
                    [p.strip() for p in row["Missing Points"].split(",") if p.strip()]
                )
            if isinstance(row.get("Risk Flags"), str) and row["Risk Flags"]:
                risk_all.extend(
                    [p.strip() for p in row["Risk Flags"].split(",") if p.strip()]
                )

        missing_all = sorted(set(missing_all))
        risk_all = sorted(set(risk_all))

        if missing_all:
            st.markdown("**Key gaps to address:** " + ", ".join(missing_all))
        if risk_all:
            st.markdown("**Risk phrases to avoid:** " + ", ".join(risk_all))

        st.markdown(
            """
- Prepare a clear finance story with amounts, sources, how long funds are held, and evidence.
- Memorise 3–4 real modules, assessments and outcomes for the UK course.
- Practise a return-home plan: role, sector, and how this course supports it.
            """
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
        "⬇ Download Advisor Coaching Report (CSV)",
        csv,
        "pre_ukvi_advisor_report.csv",
        "text/csv",
    )

else:
    # Live interview view
    idx = st.session_state.idx
    category = st.session_state.current_category
    question = st.session_state.current_question
    total_q = len(QUESTION_ORDER)
    remaining, t_str = time_left(st)

    if remaining == 0 and not st.session_state.get("question_expired", False):
        # Auto-advance with low score when time expires
        st.session_state.question_expired = True
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
        pick_question(st)
        st.experimental_rerun()

    st.progress(
        idx / total_q if total_q else 0,
        text=f"Question {idx + 1} of {total_q}",
    )

    left, right = st.columns([2.35, 1])

    # Left: question & answer input
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
            "Please type the applicant's answer in their own words. "
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
                cleaned = answer_text.strip()
                wc = len(cleaned.split())
                if not cleaned:
                    st.warning("Please type an answer before submitting.")
                else:
                    if wc < DEFAULT_MIN_WORDS:
                        st.warning(
                            f"Your answer is quite short ({wc} words). "
                            f"Aim for at least {DEFAULT_MIN_WORDS} words."
                        )

                    start_time = st.session_state.get("question_start")
                    elapsed = time.time() - start_time if start_time else None
                    is_paste_like = elapsed is not None and elapsed < 10 and wc > 40

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
                        st.stop()

                    local = bespoke_score(cleaned, category, st.session_state.profile)

                    if local.get("red_flag"):
                        final_score = local["score"]
                        st.error("This answer contains UKVI high-risk language and must be reframed.")
                        st.success(f"Score: {final_score}/5 — {local['feedback']}")
                        st.info(f"Student tip: {local['student_tip']}")
                        if local.get("risk_flags"):
                            st.warning("Risk flags: " + ", ".join(local["risk_flags"]))

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
                        pick_question(st)
                        st.experimental_rerun()
                        st.stop()

                    final_score = local["score"]
                    feedback = local["feedback"]
                    student_tip = local["student_tip"]
                    risk_flags = local.get("risk_flags", [])
                    missing_points = local.get("missing_points", [])
                    readiness = local.get("readiness", "Moderate risk")

                    if final_score <= 2:
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
                    pick_question(st)
                    st.experimental_rerun()

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
                pick_question(st)
                st.experimental_rerun()

    # Right: timer & live scores
    with right:
        remaining, t_str = time_left(st)
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
