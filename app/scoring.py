# scoring.py

import json
import re

from openai import OpenAI

from questions import RED_FLAGS, POSITIVE, ANSWER_TIPS, COURSE_PROFILES

client = OpenAI()


def is_basic_gibberish(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 10:
        return True

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

    readiness_map = {
        5: "Low risk",
        4: "Moderate risk",
        3: "Moderate risk",
        2: "Elevated risk",
        1: "High risk",
    }

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
        "readiness": readiness_map[score],
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