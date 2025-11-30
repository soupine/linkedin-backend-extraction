import re
import spacy
from typing import Dict, Any, List
from spacy.pipeline import EntityRuler
from patterns import TITLE_PATTERNS, SKILL_PATTERNS
from transformers import pipeline

_NLP = None

def get_nlp():
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except Exception:
            from spacy.lang.en import English
            _NLP = English()
            if "sentencizer" not in _NLP.pipe_names:
                _NLP.add_pipe("sentencizer")

        # EntityRuler before NER (in case NER exists)
        if "ner" in _NLP.pipe_names:
            ruler = _NLP.add_pipe("entity_ruler", before="ner")
        else:
            ruler = _NLP.add_pipe("entity_ruler")
        ruler.add_patterns(TITLE_PATTERNS + SKILL_PATTERNS)
    return _NLP

DATE_RANGE_RE = re.compile(r'(?P<start>[\w\s/.]+?)\s*[-–]\s*(?P<end>Present|Now|Current|[\w\s/.]+)', re.I)

def extract_dates(text: str) -> Dict[str, str]:
    m = DATE_RANGE_RE.search(text or "")
    if not m:
        return {"start": "", "end": ""}
    return {"start": m.group("start").strip(), "end": m.group("end").strip()}

def guess_company_and_title(text: str) -> Dict[str, str]:
    nlp = get_nlp()
    doc = nlp(text or "")
    orgs = [ent.text for ent in getattr(doc, "ents", []) if getattr(ent, "label_", "") == "ORG"]
    titles = [ent.text for ent in getattr(doc, "ents", []) if getattr(ent, "label_", "") == "TITLE"]
    if not titles:
        # Fallback
        first_line = (text or "").splitlines()[0:1]
        titles = [" ".join(first_line[0].split()[:3]).strip()] if first_line else []
    return {"company": (orgs[0].strip() if orgs else ""), "title": (titles[0] if titles else "")}

def collect_skills(text: str) -> List[str]:
    nlp = get_nlp()
    doc = nlp(text or "")
    return [ent.text for ent in getattr(doc, "ents", []) if getattr(ent, "label_", "") == "SKILL"]


# ---------------------------
# Transformer-based quality model
# ---------------------------

_TEXT_SENTIMENT_PIPELINE = None
_TEXT_ZERO_SHOT_PIPELINE = None


def get_sentiment_pipeline():
    """
    Lazy-loads a DistilBERT sentiment analysis pipeline.
    Returns None if loading fails.
    """
    global _TEXT_SENTIMENT_PIPELINE
    if _TEXT_SENTIMENT_PIPELINE is None:
        try:
            _TEXT_SENTIMENT_PIPELINE = pipeline(
                task="sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
            )
        except Exception:
            _TEXT_SENTIMENT_PIPELINE = None
    return _TEXT_SENTIMENT_PIPELINE


def get_zero_shot_pipeline():
    """
    Lazy-loads a zero-shot classification pipeline for text quality labels.
    """
    global _TEXT_ZERO_SHOT_PIPELINE
    if _TEXT_ZERO_SHOT_PIPELINE is None:
        try:
            _TEXT_ZERO_SHOT_PIPELINE = pipeline(
                task="zero-shot-classification",
                model="facebook/bart-large-mnli",
            )
        except Exception:
            _TEXT_ZERO_SHOT_PIPELINE = None
    return _TEXT_ZERO_SHOT_PIPELINE


def evaluate_text_quality(text: str) -> Dict[str, Any]:
    """
    Basic text quality evaluation using transformer pipelines.
    """
    text = (text or "").strip()
    if not text:
        return {
            "input_length": 0,
            "overall_score": 0.0,
            "tone_label": "UNKNOWN",
            "tone_score": 0.0,
            "clarity_label": "UNKNOWN",
            "clarity_score": 0.0,
            "notes": ["Empty or missing text."],
        }

    notes: List[str] = []

    # Heuristic features
    num_chars = len(text)
    num_words = len(text.split())
    num_lines = len(text.splitlines())
    notes.append(f"Text length: {num_words} words, {num_lines} lines.")

    # Sentiment for tone (professional / positive vs negative)
    sentiment_pipe = get_sentiment_pipeline()
    tone_label = "UNKNOWN"
    tone_score = 0.0
    if sentiment_pipe is not None:
        try:
            sent_result = sentiment_pipe(text[:512])[0]  # truncate for speed
            tone_label = sent_result.get("label", "UNKNOWN")
            tone_score = float(sent_result.get("score", 0.0))
            notes.append(f"Sentiment: {tone_label} (score={tone_score:.2f}).")
        except Exception:
            notes.append("Sentiment model failed during inference.")
    else:
        notes.append("Sentiment model not available (could not be loaded).")

    # Zero-shot for clarity and professionalism
    zshot_pipe = get_zero_shot_pipeline()
    clarity_label = "UNKNOWN"
    clarity_score = 0.0
    if zshot_pipe is not None:
        try:
            labels = [
                "very clear and professional",
                "somewhat clear",
                "unclear or unprofessional",
            ]
            zres = zshot_pipe(text[:512], labels)
            # take best label
            best_idx = int(zres["scores"].index(max(zres["scores"])))
            clarity_label = zres["labels"][best_idx]
            clarity_score = float(zres["scores"][best_idx])
            notes.append(
                f"Clarity: {clarity_label} (score={clarity_score:.2f})."
            )
        except Exception:
            notes.append("Zero-shot classification failed during inference.")
    else:
        notes.append("Zero-shot classification model not available.")

    # Simple overall score
    # map tone_score and clarity_score roughly into [0, 1] and average
    overall_score = (tone_score + clarity_score) / 2.0

    return {
        "input_length": num_words,
        "overall_score": overall_score,
        "tone_label": tone_label,
        "tone_score": tone_score,
        "clarity_label": clarity_label,
        "clarity_score": clarity_score,
        "notes": notes,
    }


def generate_improvement_suggestions(section_type: str, text: str, quality: Dict[str, Any]) -> List[str]:
    """
    Rule-based improvement suggestions based on section type (e.g., 'summary', 'experience')
    and the transformer-based quality result.
    """
    suggestions: List[str] = []
    text = (text or "").strip()
    num_words = len(text.split()) if text else 0

    # General checks
    if num_words == 0:
        suggestions.append("Add some content to this section; it is currently empty.")
        return suggestions

    if num_words < 30:
        suggestions.append(
            "The text is very short. Consider adding more detail about your role, skills, and impact."
        )
    elif num_words > 250:
        suggestions.append(
            "The text is quite long. Consider shortening it and focusing on your most important achievements."
        )

    # Use quality information if available
    clarity_label = quality.get("clarity_label", "UNKNOWN")
    clarity_score = quality.get("clarity_score", 0.0)
    tone_label = quality.get("tone_label", "UNKNOWN")

    if clarity_label == "unclear or unprofessional" or clarity_score < 0.5:
        suggestions.append(
            "The text may not be very clear. Try using shorter sentences and more concrete examples."
        )

    if tone_label == "NEGATIVE":
        suggestions.append(
            "The tone seems rather negative. Try to rephrase your statements in a more positive and confident way."
        )

    # Section-specific checks
    lower_text = text.lower()

    # -----------------------
    # Summary-specific rules
    # -----------------------
    if section_type == "summary":
        # Check for first-person perspective
        if "i " not in lower_text and "i'm " not in lower_text and "my " not in lower_text:
            suggestions.append(
                "Consider writing in the first person (e.g., 'I am', 'I have') to make your summary more personal."
            )

        # Check for keywords typical for a professional summary
        has_role = any(
            kw in lower_text
            for kw in ["engineer", "developer", "consultant", "manager", "student", "researcher"]
        )
        has_skills = any(
            kw in lower_text
            for kw in ["machine learning", "data science", "python", "deep learning", "project management"]
        )

        if not has_role:
            suggestions.append(
                "Clearly state your current role or professional identity (e.g., 'Data Scientist', 'Software Engineer')."
            )

        if not has_skills:
            suggestions.append(
                "Mention 2–4 core skills or domains (e.g., 'machine learning', 'backend development')."
            )

        # Check for results/impact wording
        if not any(kw in lower_text for kw in ["results", "impact", "improved", "increased", "reduced"]):
            suggestions.append(
                "Add 1–2 concrete achievements with measurable impact (e.g., 'improved model accuracy by 10%')."
            )

    # -----------------------
    # Experience-specific rules
    # -----------------------
    if section_type == "experience":
        # Check for bullet-style structure
        if "\n" in text and not any(
            line.strip().startswith(("-", "*", "•"))
            for line in text.splitlines()
        ):
            suggestions.append(
                "Use bullet points for responsibilities and achievements to improve readability."
            )

        # Check for action verbs
        action_verbs = [
            "led", "managed", "designed", "implemented", "developed",
            "improved", "reduced", "increased", "optimized", "built",
            "created", "analyzed"
        ]
        if not any(verb in lower_text for verb in action_verbs):
            suggestions.append(
                "Start bullet points with strong action verbs (e.g., 'Implemented', 'Developed', 'Led')."
            )

        # Check for metrics / numbers
        has_number = any(ch.isdigit() for ch in text)
        if not has_number:
            suggestions.append(
                "Add specific metrics or numbers where possible (e.g., 'reduced processing time by 20%')."
            )

    # -----------------------
    # Skills-specific rules
    # -----------------------
    if section_type == "skills":
        # For skills, 'text' may be a comma-separated list
        skills = [s.strip() for s in text.split(",") if s.strip()]
        if len(skills) < 5:
            suggestions.append(
                "Consider adding more relevant skills (5–15 well-chosen skills is typical)."
            )
        elif len(skills) > 25:
            suggestions.append(
                "You listed many skills. Consider focusing on your strongest 10–20 skills."
            )

        # Check for very generic items
        generic = [s for s in skills if s.lower() in ["microsoft office", "office", "microsoft word", "internet"]]
        if generic:
            suggestions.append(
                "Avoid very generic skills like 'Microsoft Office'; focus on tools and technologies that differentiate you."
            )

    return suggestions



def evaluate_summary_text(summary: str) -> Dict[str, Any]:
    """
    High-level helper to evaluate a LinkedIn-style summary section.

    Returns a dictionary with:
    - 'quality': numeric/text metrics from evaluate_text_quality
    - 'suggestions': list of concrete improvement suggestions
    """
    quality = evaluate_text_quality(summary)
    suggestions = generate_improvement_suggestions(
        section_type="summary",
        text=summary,
        quality=quality,
    )

    return {
        "section": "summary",
        "text": summary,
        "quality": quality,
        "suggestions": suggestions,
    }


def evaluate_experience_text(description: str) -> Dict[str, Any]:
    """
    Evaluate a job experience description (e.g., responsibilities + achievements).

    Returns:
    - 'quality': numeric/text metrics from evaluate_text_quality
    - 'suggestions': list of improvement suggestions
    """
    quality = evaluate_text_quality(description)
    suggestions = generate_improvement_suggestions(
        section_type="experience",
        text=description,
        quality=quality,
    )

    return {
        "section": "experience",
        "text": description,
        "quality": quality,
        "suggestions": suggestions,
    }


def evaluate_skills_list(skills: List[str]) -> Dict[str, Any]:
    """
    Evaluate a list of skills extracted from the profile.

    Returns:
    - 'skills': cleaned, unique list
    - 'num_skills': number of unique skills
    - 'suggestions': improvement suggestions (coverage, redundancy, etc.)
    """
    # Normalize and deduplicate skills
    cleaned = []
    seen = set()

    for skill in skills or []:
        s = (skill or "").strip()
        if not s:
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(s)

    num_skills = len(cleaned)

    # Build a pseudo-text for the rules engine
    skills_text = ", ".join(cleaned)
    quality_stub = {
        "clarity_label": "UNKNOWN",
        "clarity_score": 1.0,  # not really used here
        "tone_label": "UNKNOWN",
    }
    suggestions = generate_improvement_suggestions(
        section_type="skills",
        text=skills_text,
        quality=quality_stub,
    )

    # Extra heuristics specific to skills
    if num_skills == 0:
        suggestions.append("Add at least a few skills that reflect your expertise.")
    else:
        # Check length of skill names
        long_skills = [s for s in cleaned if len(s) > 40]
        if long_skills:
            suggestions.append(
                "Some skills are very long; consider shortening them to concise labels."
            )

    return {
        "section": "skills",
        "skills": cleaned,
        "num_skills": num_skills,
        "suggestions": suggestions,
    }

