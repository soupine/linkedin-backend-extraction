from rapidfuzz import process, fuzz
from typing import List

CANONICAL_TITLES = [
    "Software Engineer", "Data Scientist", "Machine Learning Engineer",
    "Data Engineer", "Product Manager", "Research Scientist",
]

CANONICAL_SKILLS = [
    "Python", "Java", "C++", "SQL", "TensorFlow", "PyTorch", "spaCy",
    "NLP", "Computer Vision", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
]

def normalize_job_title(raw: str, min_score: int = 80) -> str:
    if not raw:
        return raw
    match, score, _ = process.extractOne(
        raw, CANONICAL_TITLES, scorer=fuzz.WRatio
    ) or (None, 0, None)
    return match if score >= min_score else raw

def normalize_skills(raw_skills: List[str], min_score: int = 85) -> List[str]:
    out = []
    seen = set()
    for s in raw_skills:
        if not s:
            continue
        match, score, _ = process.extractOne(
            s, CANONICAL_SKILLS, scorer=fuzz.WRatio
        ) or (None, 0, None)
        norm = match if score >= min_score else s
        key = norm.lower()
        if key not in seen:
            seen.add(key)
            out.append(norm)
    return out
