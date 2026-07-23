# session.py

import time
import random

from questions import QUESTION_ORDER, QUESTION_BANK, QUESTION_TIME_SECONDS


def init_session_state(st):
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


def reset_interview_state(st):
    keys_to_clear = list(st.session_state.keys())
    for key in keys_to_clear:
        if key.startswith("answer_") or key in [
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
        ]:
            del st.session_state[key]
    init_session_state(st)


def pick_question(st):
    idx = st.session_state.idx
    if idx >= len(QUESTION_ORDER):
        st.session_state.completed = True
        return
    category = QUESTION_ORDER[idx]
    st.session_state.current_category = category
    st.session_state.current_question = random.choice(QUESTION_BANK[category])
    st.session_state.question_start = time.time()
    st.session_state.question_expired = False


def time_left(st):
    start = st.session_state.get("question_start")
    if not start:
        return QUESTION_TIME_SECONDS, f"{QUESTION_TIME_SECONDS // 60:02d}:00"
    elapsed = time.time() - start
    remaining = max(0, int(QUESTION_TIME_SECONDS - elapsed))
    return remaining, f"{remaining // 60:02d}:{remaining % 60:02d}"


def verdict(avg: float) -> str:
    if avg >= 4.5:
        return "✅ Strong Pre-CAS performance"
    if avg >= 3.5:
        return "🟡 Borderline — strengthen weak areas"
    if avg >= 2.5:
        return "🟠 At risk — more practice needed"
    return "🔴 High risk — urgent coaching required"