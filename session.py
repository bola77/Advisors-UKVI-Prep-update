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
            "why you want to study in the UK",
            "your academic or personal background",
            "a personal motivation",
        ],
        "Course Choice": [
            "why this course fits your background",
            "why this university was chosen",
            "how the course supports your future plans",
        ],
        "Finance": [
            "who is funding your studies",
            "tuition and living cost awareness",
            "evidence of financial preparedness",
        ],
        "Career Plans": [
            "your post-study career plan",
            "how the course supports that plan",
            "why the plan makes sense in your home country",
        ],
        "Immigration Intent": [
            "a study-focused reason for choosing the UK",
            "a credible comparison with other options",
            "clear non-migration language",
        ],
        "Accommodation": [
            "where you will stay",
            "basic location or housing arrangement",
            "preparedness before arrival",
        ],
    }
    return mapping.get(category, ["specific evidence", "clear rationale", "credible explanation"])


def _detect_missing_points(answer: str, category: str, profile: dict):
    lower = (answer or "").lower()
    missing = []

    if len(answer.split()) < 20:
        missing.append("more supporting detail")

    if category == "Course Choice":
        course = profile.get("course", "").strip().lower()
        university = profile.get("university", "").strip().lower()

        if course and course not in lower:
            missing.append("your exact course name or field")
        if university and university not in lower:
            missing.append("why this university specifically")
        if "career" not in lower and "job" not in lower and "future" not in lower:
            missing.append("how the course supports your future career")

    elif category == "Finance":
        if not any(x in lower for x in ["sponsor", "parents", "father", "mother", "savings", "fund", "tuition"]):
            missing.append("who will pay for your tuition and living costs")
        if not any(x in lower for x in ["living", "cost", "accommodation", "expenses"]):
            missing.append("awareness of living costs and planning")

    elif category == "Career Plans":
        if not any(x in lower for x in ["career", "job", "future", "return", "work", "plan"]):
            missing.append("a clear post-study career plan")
        country = profile.get("country", "").strip().lower()
        if country and country not in lower:
            missing.append("how your plan connects to opportunities in your home country")

    elif category == "Immigration Intent":
        if not any(x in lower for x in ["uk", "britain", "united kingdom"]):
            missing.append("a direct reason for choosing the UK")
        if not any(x in lower for x in ["education", "course", "university", "quality", "academic"]):
            missing.append("an academic reason instead of a generic preference")

    elif category == "Accommodation":
        if not any(x in lower for x in ["stay", "live", "accommodation", "hostel", "apartment"]):
            missing.append("where you will stay")
        if not any(x in lower for x in ["near", "campus", "location", "address", "area"]):
            missing.append("basic location or housing details")

    elif category == "Personal Background":
        if not any(x in lower for x in ["study", "course", "education"]):
            missing.append("your study motivation")
        if "because" not in lower:
            missing.append("a personal reason in your own words")

    if len(missing) < 3:
        for item in _category_expected_points(category):
            if item not in missing:
                missing.append(item)
            if len(missing) >= 3:
                break

    seen = set()
    deduped = []
    for item in missing:
        if item not in seen:
            deduped.append(item)
            seen.add(item)

    return deduped[:3]


def _build_better_version(category: str, profile: dict):
    course = profile.get("course", "my chosen course")
    university = profile.get("university", "my university")
    country = profile.get("country", "my home country")

    templates = {
        "Personal Background": (
            f"I want to study in the UK because the education system is strong and it aligns with my academic goals. "
            f"My background has prepared me for {course}, and I want to use this opportunity to build skills I can apply in {country}."
        ),
        "Course Choice": (
            f"I chose {course} at {university} because it fits my previous background and my future career plans. "
            "The course content is relevant to the practical and academic skills I want to develop."
        ),
        "Finance": (
            "My studies will be funded through a clear financial plan that covers both tuition and living costs. "
            "I understand the expenses involved and I am financially prepared."
        ),
        "Career Plans": (
            f"After completing {course}, I plan to apply the knowledge in my professional development in {country}. "
            "My goal is to move into a role where this qualification will have direct value."
        ),
        "Immigration Intent": (
            f"I chose the UK because of the quality and relevance of the education for {course}. "
            f"My decision is based on academic fit and how the qualification will support my long-term plans in {country}."
        ),
        "Accommodation": (
            f"I have already considered where I will stay when I arrive, and I want accommodation that is practical for my studies at {university}. "
            "I understand the importance of arranging housing that supports my academic routine."
        ),
    }
    return templates.get(
        category,
        "Give a direct answer, add one concrete detail, and explain how it supports your study and career plan."
    )


def _compose_bespoke_feedback(
    score: int,
    category: str,
    answer: str,
    profile: dict,
    generic_pos: int,
    cluster_hits: int,
    dimension_scores: dict,
    missing_points: list,
):
    lower = answer.lower()
    strengths = []
    gaps = []

    course = profile.get("course", "").strip()
    university = profile.get("university", "").strip()

    if course and course.lower() in lower:
        strengths.append(f"you mentioned your course ({course})")
    if university and university.lower() in lower:
        strengths.append(f"you referred to your university ({university})")
    if cluster_hits > 0:
        strengths.append("you used course-related details")
    if generic_pos > 0:
        strengths.append("your answer included positive intent signals")
    if dimension_scores.get("clarity", 0) >= 4:
        strengths.append("your answer was reasonably clear and easy to follow")
    if dimension_scores.get("credibility", 0) >= 4:
        strengths.append("your response sounded broadly credible")

    if dimension_scores.get("specificity", 0) <= 2:
        gaps.append("it needs more concrete detail")
    if dimension_scores.get("relevance", 0) <= 2:
        gaps.append("it does not yet answer the question directly enough")
    if dimension_scores.get("credibility", 0) <= 2:
        gaps.append("it needs a more believable link between your plans and your course")
    if missing_points:
        gaps.append(f"it should also cover {missing_points[0]}")

    if score >= 5:
        opening = "This is a strong answer."
    elif score == 4:
        opening = "This is a good answer."
    elif score == 3:
        opening = "This answer is acceptable, but still generic."
    elif score == 2:
        opening = "This answer is weak."
    else:
        opening = "This answer has serious credibility or clarity concerns."

    feedback_parts = [opening]

    if strengths:
        feedback_parts.append("What works is that " + ", ".join(strengths[:2]) + ".")
    if gaps:
        feedback_parts.append("To improve it, " + " and ".join(gaps[:2]) + ".")

    if not strengths and not gaps:
        feedback_parts.append(
            "Add clearer reasons, more course-specific details, and a stronger connection to your future plans."
        )

    return " ".join(feedback_parts)


def bespoke_score(answer: str, category: str, profile: dict) -> dict:
    answer = (answer or "").strip()
    lower = answer.lower()

    default_tip = ANSWER_TIPS.get(category, ANSWER_TIPS["default"])

    if is_basic_gibberish(answer):
        dimension_scores = {
            "relevance": 1,
            "specificity": 1,
            "credibility": 1,
            "clarity": 1,
        }
        return {
            "score": 1,
            "feedback": "The response could not be meaningfully assessed because it appears random, too short, or unclear.",
            "student_tip": "Give a clear answer in full sentences and include one or two concrete details.",
            "risk_flags": ["gibberish"],
            "missing_points": ["coherent explanation", "real reasons and examples"],
            "counsellor_note": "Student provided gibberish or unusable content.",
            "red_flag": True,
            "generic_pos": 0,
            "cluster_hits": 0,
            "readiness": "High risk",
            "dimension_scores": dimension_scores,
            "better_version": _build_better_version(category, profile),
        }

    for flag in RED_FLAGS:
        if flag in lower:
            dimension_scores = {
                "relevance": 1,
                "specificity": 1,
                "credibility": 1,
                "clarity": 2,
            }
            return {
                "score": 1,
                "feedback": (
                    f"The answer includes the high-risk phrase '{flag}', which can sound immigration-led "
                    "or agent-scripted rather than academically motivated."
                ),
                "student_tip": "Avoid immigration-led or agent-scripted wording. Explain your own genuine academic reasons.",
                "risk_flags": [flag],
                "missing_points": ["clear personal rationale", "evidence that supports your story"],
                "counsellor_note": "High-risk phrase detected and answer should be reframed.",
                "red_flag": True,
                "generic_pos": 0,
                "cluster_hits": 0,
                "readiness": "High risk",
                "dimension_scores": dimension_scores,
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
    if any(x in lower for x in ["because", "my reason", "i chose", "i want"]):
        relevance += 1
    relevance = min(5, relevance)

    specificity = 2
    if any(x in lower for x in ["because", "for example", "specifically", "for instance"]):
        specificity += 1
    if cluster_hits >= 1:
        specificity += 1
    if profile.get("course", "").strip().lower() in lower:
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

    dimension_scores = {
        "relevance": relevance,
        "specificity": specificity,
        "credibility": credibility,
        "clarity": clarity,
    }

    avg = round(sum(dimension_scores.values()) / 4, 2)

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

    feedback = _compose_bespoke_feedback(
        score=score,
        category=category,
        answer=answer,
        profile=profile,
        generic_pos=generic_pos,
        cluster_hits=cluster_hits,
        dimension_scores=dimension_scores,
        missing_points=missing_points,
    )

    return {
        "score": score,
        "feedback": feedback,
        "student_tip": student_tip,
        "risk_flags": [],
        "missing_points": missing_points if missing_points else ["add one or two more specific supporting details"],
        "counsellor_note": "Bespoke scoring used with category-aware and answer-aware feedback.",
        "red_flag": False,
        "generic_pos": generic_pos,
        "cluster_hits": cluster_hits,
        "readiness": readiness_map[score],
        "dimension_scores": dimension_scores,
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

Evaluate the answer in a bespoke and practical way.

Focus on:
1. relevance to the actual question
2. specificity and useful detail
3. credibility and consistency with the applicant profile
4. clarity and structure

Return compact JSON with keys:
score, feedback, student_tip, risk_flags, missing_points, readiness, dimension_scores, better_version

Rules:
- score must be an integer 1 to 5
- dimension_scores must contain relevance, specificity, credibility, clarity as integers 1 to 5
- feedback must mention at least one actual strength or weakness from the answer, not generic wording
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
