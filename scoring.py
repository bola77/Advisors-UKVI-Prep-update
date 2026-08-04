# scoring.py

import json
import re
import streamlit as st
from openai import OpenAI

from questions import RED_FLAGS, POSITIVE, ANSWER_TIPS, COURSE_PROFILES


def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def is_basic_gibberish(text: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < 10:
        return True

    non_alpha = sum(1 for c in cleaned if not c.isalpha() and not c.isspace())
    if len(cleaned) > 0 and non_alpha > len(cleaned) * 0.3:
        return True

    words = cleaned.split()
    long_no_vowel = [
        w for w in words
        if len(w) >= 4 and not re.search(r"[aeiouAEIOU]", w)
    ]
    if len(long_no_vowel) >= 2:
        return True

    return False


def _category_expected_points(category: str):
    mapping = {
        "Personal Background": [
            "Why the student wants to study in the UK",
            "Personal or academic background",
            "A clear study motivation",
        ],
        "Course Choice": [
            "Why this course fits prior study or experience",
            "Why this university was chosen",
            "How the course supports career plans",
        ],
        "Finance": [
            "Who is funding the studies",
            "Tuition and living cost awareness",
            "Evidence of financial preparation",
        ],
        "Career Plans": [
            "Post-study job plan",
            "Connection between course and future career",
            "Intention grounded in home-country progression",
        ],
        "Immigration Intent": [
            "Why the UK was chosen academically",
            "A study-focused reason, not migration language",
            "Comparison with alternatives in a credible way",
        ],
        "Accommodation": [
            "Where the student will stay",
            "Basic location or arrangement details",
            "Preparedness before arrival",
        ],
    }
    return mapping.get(category, ["Specific evidence", "Clear rationale", "Credible explanation"])


def _detect_missing_points(answer: str, category: str, profile: dict):
    lower = (answer or "").lower()
    missing = []

    expected = _category_expected_points(category)

    if len(answer.split()) < 20:
        missing.append("Enough detail to fully answer the question")

    if category == "Course Choice":
        if profile.get("course", "").strip():
            if profile["course"].lower() not in lower:
                missing.append("Your exact course name or field")
        if profile.get("university", "").strip():
            if profile["university"].lower() not in lower:
                missing.append("Why this university specifically")
        if "career" not in lower and "job" not in lower and "future" not in lower:
            missing.append("How the course supports your future career")

    elif category == "Finance":
        finance_words = ["sponsor", "father", "mother", "parents", "savings", "tuition", "fund", "funding"]
        if not any(word in lower for word in finance_words):
            missing.append("Who will pay for your tuition and living costs")
        if "living" not in lower and "accommodation" not in lower and "cost" not in lower:
            missing.append("Awareness of living costs or financial planning")

    elif category == "Career Plans":
        if "return" not in lower and "career" not in lower and "job" not in lower and "future" not in lower:
            missing.append("A clear post-study career plan")
        if profile.get("country", "").strip():
            if profile["country"].lower() not in lower:
                missing.append("How your plan connects to opportunities in your home country")

    elif category == "Immigration Intent":
        if "uk" not in lower and "britain" not in lower and "united kingdom" not in lower:
            missing.append("A direct academic reason for choosing the UK")
        if "quality" not in lower and "course" not in lower and "university" not in lower and "education" not in lower:
            missing.append("A study-focused comparison, not a generic preference")

    elif category == "Accommodation":
        if "stay" not in lower and "accommodation" not in lower and "live" not in lower:
            missing.append("Where you will stay")
        if "near" not in lower and "location" not in lower and "address" not in lower and "campus" not in lower:
            missing.append("Basic location or arrangement details")

    elif category == "Personal Background":
        if "study" not in lower and "course" not in lower:
            missing.append("Your study motivation")
        if "because" not in lower:
            missing.append("A personal reason, not just a general statement")

    for item in expected:
        short_key = item.lower().split()[0]
        if short_key not in lower and len(missing) < 4:
            if item not in missing:
                missing.append(item)

    seen = set()
    deduped = []
    for item in missing:
        if item not in seen:
            deduped.append(item)
            seen.add(item)

    return deduped[:4]


def _build_better_version(category: str, profile: dict):
    course = profile.get("course", "my chosen course")
    university = profile.get("university", "my university")
    country = profile.get("country", "my home country")

    templates = {
        "Personal Background": (
            f"I want to study in the UK because the education system is strong and it matches my academic goals. "
            f"My background has prepared me for {course}, and I want to build skills I can use when I return to {country}."
        ),
        "Course Choice": (
            f"I chose {course} at {university} because it matches my previous background and future career plans. "
            f"The course content is relevant to the skills I need, and this university offers a strong environment for that."
        ),
        "Finance": (
            "My studies will be funded through a clear financial plan that covers both tuition and living costs. "
            "I understand the expenses involved and I am financially prepared."
        ),
        "Career Plans": (
            f"After completing {course}, I plan to apply the knowledge in my career progression in {country}. "
            "My goal is to move into a role where this qualification is directly relevant."
        ),
        "Immigration Intent": (
            f"I chose the UK because of the quality and relevance of the education for {course}. "
            f"My decision is based on academic fit and how the qualification will support my future plans in {country}."
        ),
        "Accommodation": (
            f"I have planned where I will stay when I arrive, and I want accommodation that is practical for my studies at {university}. "
            "I understand the need to settle close enough to support my academic routine."
        ),
    }
    return templates.get(
        category,
        "Give a direct answer, add one concrete detail, and explain how it supports your study and career plan."
    )


def bespoke_score(answer: str, category: str, profile: dict) -> dict:
    answer = (answer or "").strip()
    lower = answer.lower()

    default_tip = ANSWER_TIPS.get(category, ANSWER_TIPS["default"])

    if is_basic_gibberish(answer):
        return {
            "score": 1,
            "feedback": "Answer appears random, too short, or not meaningful enough to assess.",
            "student_tip": "Give a clear answer in full sentences and include one or two concrete details.",
            "risk_flags": ["gibberish"],
            "missing_points": ["Coherent explanation", "Real reasons and examples"],
            "counsellor_note": "Student provided gibberish or unusable content.",
            "red_flag": True,
            "generic_pos": 0,
            "cluster_hits": 0,
            "readiness": "High risk",
            "dimension_scores": {
                "relevance": 1,
                "specificity": 1,
                "credibility": 1,
                "clarity": 1,
            },
            "better_version": _build_better_version(category, profile),
        }

    for flag in RED_FLAGS:
        if flag in lower:
            return {
                "score": 1,
                "feedback": f"High-risk phrase detected: '{flag}'. This wording may raise credibility concerns.",
                "student_tip": "Avoid immigration-led or agent-scripted wording. Explain your own genuine academic reasons.",
                "risk_flags": [flag],
                "missing_points": ["Clear personal rationale", "Evidence that supports your story"],
                "counsellor_note": "High-risk phrase detected and answer should be reframed.",
                "red_flag": True,
                "generic_pos": 0,
                "cluster_hits": 0,
                "readiness": "High risk",
                "dimension_scores": {
                    "relevance": 1,
                    "specificity": 1,
                    "credibility": 1,
                    "clarity": 2,
                },
                "better_version": _build_better_version(category, profile),
            }

    generic_pos = sum(1 for signal in POSITIVE if signal in lower)

    course_track = profile.get("course_track")
    cluster_hits = 0
    if course_track and course_track in COURSE_PROFILES:
        keywords = COURSE_PROFILES[course_track].get("keywords", [])
        cluster_hits = sum(1 for keyword in keywords if keyword.lower() in lower)

    wc = len(answer.split())

    relevance = 4 if wc >= 18 else 2
    if category.lower().split()[0] in lower:
        relevance = min(5, relevance + 1)

    specificity = 2
    if any(x in lower for x in ["because", "for example", "specifically", "for instance"]):
        specificity += 1
    if cluster_hits >= 1:
        specificity += 1
    if profile.get("course", "").lower() in lower or profile.get("university", "").lower() in lower:
        specificity += 1
    specificity = min(5, specificity)

    credibility = 2
    if generic_pos >= 1:
        credibility += 1
    if cluster_hits >= 1:
        credibility += 1
    if any(x in lower for x in ["career", "job", "future", "return", "plan"]):
        credibility += 1
    credibility = min(5, credibility)

    clarity = 2
    if wc >= 20:
        clarity += 1
    if "." in answer or "," in answer:
        clarity += 1
    if any(x in lower for x in ["because", "therefore", "so that"]):
        clarity += 1
    clarity = min(5, clarity)

    avg = round((relevance + specificity + credibility + clarity) / 4, 2)

    if avg >= 4.5:
        score = 5
    elif avg >= 3.6:
        score = 4
    elif avg >= 2.8:
        score = 3
    elif avg >= 2.0:
        score = 2
    else:
        score = 1

    missing_points = _detect_missing_points(answer, category, profile)

    feedback_map = {
        5: "Excellent answer — clear, specific, and credible, with strong alignment to your academic and career plans.",
        4: "Good answer — relevant and believable, but one or two more concrete details would strengthen it.",
        3: "Average answer — broadly acceptable, but still a bit generic or underdeveloped.",
        2: "Weak answer — too vague, too short, or missing important supporting detail.",
        1: "High-risk answer — major credibility, clarity, or relevance concerns were detected.",
    }

    if course_track and course_track in COURSE_PROFILES:
        student_tip = COURSE_PROFILES[course_track].get("extra_tip", default_tip)
    else:
        student_tip = default_tip

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
        "missing_points": missing_points if missing_points else ["Add one or two more specific supporting details"],
        "counsellor_note": "Bespoke scoring used with category-aware rubric.",
        "red_flag": False,
        "generic_pos": generic_pos,
        "cluster_hits": cluster_hits,
        "readiness": readiness_map[score],
        "dimension_scores": {
            "relevance": relevance,
            "specificity": specificity,
            "credibility": credibility,
            "clarity": clarity,
        },
        "better_version": _build_better_version(category, profile),
    }


def openai_evaluate_answer(answer: str, category: str, question: str, profile: dict) -> dict:
    client = get_openai_client()
    fallback_tip = ANSWER_TIPS.get(category, ANSWER_TIPS["default"])

    if client is None:
        return {
            "score": 3,
            "feedback": "Model-based evaluation unavailable because OPENAI_API_KEY is not configured.",
            "student_tip": fallback_tip,
            "risk_flags": [],
            "missing_points": [],
            "readiness": "Moderate risk",
            "dimension_scores": {
                "relevance": 3,
                "specificity": 3,
                "credibility": 3,
                "clarity": 3,
            },
            "better_version": _build_better_version(category, profile),
        }

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

Evaluate the answer for:
1. relevance to the question
2. specificity and detail
3. credibility and consistency
4. clarity and structure

Return compact JSON with keys:
score, feedback, student_tip, risk_flags, missing_points, readiness, dimension_scores, better_version

Rules:
- score must be an integer 1 to 5
- dimension_scores must contain relevance, specificity, credibility, clarity as integers 1 to 5
- better_version must be a short improved sample answer starter, not a long essay
- risk_flags and missing_points must be arrays of short strings
- focus on study credibility, not grammar perfection
"""

    response = client.responses.create(
        model="gpt-5.1-mini",
        input=prompt,
        response_format={"type": "json_object"},
    )

    raw = response.output[0].content[0].text
    data = json.loads(raw)

    dims = data.get("dimension_scores", {}) or {}

    return {
        "score": int(data.get("score", 3)),
        "feedback": data.get("feedback", "Answer evaluated."),
        "student_tip": data.get("student_tip", fallback_tip),
        "risk_flags": data.get("risk_flags", []) or [],
        "missing_points": data.get("missing_points", []) or [],
        "readiness": data.get("readiness", "Moderate risk"),
        "dimension_scores": {
            "relevance": int(dims.get("relevance", 3)),
            "specificity": int(dims.get("specificity", 3)),
            "credibility": int(dims.get("credibility", 3)),
            "clarity": int(dims.get("clarity", 3)),
        },
        "better_version": data.get("better_version", _build_better_version(category, profile)),
    }
