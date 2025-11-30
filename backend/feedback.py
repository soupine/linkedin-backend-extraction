from typing import Dict, Any, List

from nlp import (
    evaluate_summary_text,
    evaluate_experience_text,
    evaluate_skills_list,
)


def _build_experience_feedback(experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run NLP quality evaluation for each experience item.
    """
    feedback_items: List[Dict[str, Any]] = []

    for idx, exp in enumerate(experiences or []):
        exp = exp or {}

        title = exp.get("title", "") or ""
        company = exp.get("company", "") or ""
        description = exp.get("description", "") or ""

        # Build a text we can evaluate
        parts: List[str] = []
        if description:
            parts.append(description)
        if title:
            parts.append(f"Title: {title}")
        if company:
            parts.append(f"Company: {company}")

        combined_text = "\n".join(parts).strip()
        result = evaluate_experience_text(combined_text)

        # Add metadata so frontend can link feedback to this experience
        result["index"] = idx
        result["meta"] = {
            "title": title,
            "company": company,
            "location": exp.get("location", "") or "",
            "start_date": exp.get("start_date", "") or "",
            "end_date": exp.get("end_date", "") or "",
        }

        feedback_items.append(result)

    return feedback_items


def build_profile_feedback(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the final AI feedback object from the structured profile.

    Expected profile format (from extractor.extract_structured_profile):
    {
        "summary": str,
        "experience": [ {title, company, description, ...}, ... ],
        "education": [...],
        "skills": [ "Python", "Machine Learning", ... ]
    }
    """
    profile = profile or {}

    # --- Summary ---
    summary_text = profile.get("summary", "") or ""
    summary_feedback = evaluate_summary_text(summary_text)

    # --- Experience ---
    experience_items = profile.get("experience", []) or []
    experience_feedback = _build_experience_feedback(experience_items)

    # --- Skills ---
    skills_list = profile.get("skills", []) or []
    skills_feedback = evaluate_skills_list(skills_list)

    # --- Overall score (simple average over sections that have numeric scores) ---
    scores: List[float] = []

    # summary score
    summary_score = summary_feedback.get("quality", {}).get("overall_score", 0.0) or 0.0
    if summary_score > 0:
        scores.append(summary_score)

    # experience scores
    for item in experience_feedback:
        s = item.get("quality", {}).get("overall_score", 0.0) or 0.0
        if s > 0:
            scores.append(s)

    overall_score = sum(scores) / len(scores) if scores else 0.0

    overall_info = {
        "overall_score": overall_score,
        "num_experiences": len(experience_feedback),
        "num_skills": skills_feedback.get("num_skills", 0),
    }

    return {
        "overall": overall_info,
        "summary": summary_feedback,
        "experience": experience_feedback,
        "skills": skills_feedback,
    }
