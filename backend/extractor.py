import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import dateparser
from normalizer import normalize_job_title, normalize_skills
from nlp import extract_dates, guess_company_and_title
from nlp import collect_skills


@dataclass
class ExperienceItem:
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""

@dataclass
class EducationItem:
    school: str = ""
    degree: str = ""
    field: str = ""
    start_year: str = ""
    end_year: str = ""

@dataclass
class Profile:
    summary: str
    experience: List[ExperienceItem]
    education: List[EducationItem]
    skills: List[str]

def _iso_ym(text: str) -> str:
    if not text:
        return ""
    dt = dateparser.parse(text)
    if not dt:
        return ""
    return f"{dt.year:04d}-{dt.month:02d}"


# --- insert new Helpers below ---

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def _iso_ym_fallback(year: str, month: str | None) -> str:
    try:
        y = int(re.sub(r"\D", "", year))  # handle '2018' / '2018.' etc.
        m = 1
        if month:
            key = month.strip().lower()
            m = MONTHS.get(key[:3], 1)
        return f"{y:04d}-{m:02d}"
    except Exception:
        return ""

DATE_SEP = re.compile(r"\s*[-–]\s*", re.I)

def parse_date_range(s: str) -> tuple[str, str]:
    """
    Unterstützt:
    - 'Jan 2021 - Present'
    - '2018 - 2020'
    - 'Jun 2019–Dec 2020'
    - '2022 – Present'
    """
    if not s:
        return "", ""
    parts = DATE_SEP.split(s.strip(), maxsplit=1)
    start_raw = parts[0] if parts else ""
    end_raw = parts[1] if len(parts) > 1 else ""

    # try with dateparser
    def parse_one(x: str) -> str:
        if not x:
            return ""
        if re.search(r"present|now|current", x, re.I):
            return ""
        # 1. try: normal
        dt = dateparser.parse(x)
        if dt:
            return f"{dt.year:04d}-{dt.month:02d}"
        # 2. try: '2018' -> '2018-01'
        m = re.search(r"(\d{4})", x)
        if m:
            return f"{int(m.group(1)):04d}-01"
        # 3. try: 'Jan 2018' as Tokens
        m2 = re.search(r"([A-Za-z]{3,9})\s+(\d{4})", x)
        if m2:
            return _iso_ym_fallback(m2.group(2), m2.group(1))
        return ""

    return parse_one(start_raw), parse_one(end_raw)

EXPERIENCE_LINE_PATTERNS = [
    # A: "Title at Company (Dates) – Location?"
    re.compile(r"^(?P<title>.+?)\s+at\s+(?P<company>.+?)\s*\((?P<dates>[^)]+)\)\s*(?P<rest>.*)$", re.I),
    # B: "Company — Title (Dates)"
    re.compile(r"^(?P<company>.+?)\s+[—-]\s+(?P<title>.+?)\s*\((?P<dates>[^)]+)\)\s*(?P<rest>.*)$", re.I),
    # C: "Title, Company (Dates)"
    re.compile(r"^(?P<title>.+?),\s+(?P<company>.+?)\s*\((?P<dates>[^)]+)\)\s*(?P<rest>.*)$", re.I),
]

LOCATION_TAIL = re.compile(r"(?:\s*[\u2013\u00B7\-]\s*|\s+\|\s+)(?P<loc>[^|\u00B7\u2013\-]+)$")

def parse_experience_block(block: str) -> dict:
    item = ExperienceItem()
    if not block:
        return asdict(item)

    first_line, *rest_lines = [l.strip() for l in block.splitlines() if l.strip()]
    matched = None
    for pat in EXPERIENCE_LINE_PATTERNS:
        m = pat.match(first_line)
        if m:
            matched = m
            break

    if matched:
        gd = matched.groupdict()
        item.title = (gd.get("title") or "").strip()
        item.company = (gd.get("company") or "").strip()
        start, end = parse_date_range(gd.get("dates") or "")
        item.start_date, item.end_date = start, end
        tail = gd.get("rest") or ""
        lm = LOCATION_TAIL.search(tail)
        if lm:
            item.location = lm.group("loc").strip()
        desc = []
        if tail and not lm:
            desc.append(tail.strip())
        if rest_lines:
            desc.append(" ".join(rest_lines))
        item.description = " ".join([d for d in desc if d]).strip()
    else:
        # Fallback
        lines = [l for l in block.splitlines() if l.strip()]
        if lines:
            item.title = lines[0]
        if len(lines) > 1:
            item.company = lines[1]
        if len(lines) > 2:
            item.description = " ".join(lines[2:])

    return asdict(item)


# ---------- Very-Initial Heuristics ----------

SECTION_REGEX = re.compile(r'(Experience|Education|Skills)', re.IGNORECASE)

def split_sections(text: str) -> Dict[str, Any]:
    sections = {"summary": "", "experience": [], "education": [], "skills": []}
    parts = re.split(SECTION_REGEX, text)
    # parts -> [<pre>, "Experience", <content>, "Education", <content>, "Skills", <content> ...]
    if parts:
        sections["summary"] = parts[0].strip()

    for i in range(1, len(parts), 2):
        name = parts[i].lower()
        content = parts[i+1].strip() if i+1 < len(parts) else ""

        if "experience" in name:
            for block in re.split(r'\n{2,}', content):
                block = block.strip()
                if not block:
                    continue
                sections["experience"].append(parse_experience_block(block))

        elif "education" in name:
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                # naive: "School – Degree, Field (2018–2022)"
                m = re.search(r'^(?P<school>.+?)\s+[–-]\s+(?P<degree>.+?)(?:,\s*(?P<field>[^()]+))?\s*(?:\((?P<years>[^)]+)\))?$', line)
                item = EducationItem()
                if m:
                    item.school = (m.group('school') or "").strip()
                    item.degree = (m.group('degree') or "").strip()
                    item.field = (m.group('field') or "").strip()
                    years = (m.group('years') or "").strip()
                    ym = re.search(r'(?P<start>\d{4})\s*[–-]\s*(?P<end>\d{4}|present)', years, re.I)
                    if ym:
                        item.start_year = ym.group('start')
                        item.end_year = "" if ym.group('end').lower() == "present" else ym.group('end')
                else:
                    # Fallback
                    item.school = line
                sections["education"].append(asdict(item))

        elif "skills" in name:
            skills = [s.strip() for s in re.split(r'[,\n;]', content) if s.strip()]
            seen = set()
            clean = []
            for s in skills:
                k = s.lower()
                if k not in seen:
                    seen.add(k)
                    clean.append(s)
            sections["skills"].extend(clean)

    return sections


def _enrich_experience_with_ner(item: dict) -> dict:

    blob = " ".join(filter(None, [
        item.get("title",""), item.get("company",""), item.get("description","")
    ]))
    # guess title/ company if empty
    if not item.get("title") or not item.get("company"):
        guessed = guess_company_and_title(blob)
        item["title"] = item.get("title") or guessed.get("title","")
        item["company"] = item.get("company") or guessed.get("company","")

    if not item.get("start_date") and not item.get("end_date"):
        dr = extract_dates(blob)
        if dr.get("start"):
            item["start_date"] = _iso_ym(dr["start"])
        if dr.get("end"):
            # present -> ""
            item["end_date"] = "" if re.search(r'present|now|current', dr["end"], re.I) else _iso_ym(dr["end"])
    return item

def _normalize_structured(sections: dict) -> dict:
    extra_skill_text = " ".join([
        sections.get("summary", ""),
        *[e.get("description", "") or "" for e in sections.get("experience", [])]
    ])
    ner_skills = collect_skills(extra_skill_text)
    merged = [*sections.get("skills", []), *ner_skills]

    seen, dedup = set(), []
    for s in merged:
        k = s.strip().lower()
        if k and k not in seen:
            seen.add(k)
            dedup.append(s.strip())

    sections["skills"] = normalize_skills(dedup)

    for exp in sections.get("experience", []):
        exp["title"] = normalize_job_title(exp.get("title", ""))
    return sections

def extract_structured_profile(text: str) -> Dict[str, Any]:

    sections = split_sections(text)

    # enrich experience with NER/heuristic
    enriched = []
    for exp in sections.get("experience", []):
        enriched.append(_enrich_experience_with_ner(exp))
    sections["experience"] = enriched

    # normalize
    sections = _normalize_structured(sections)
    return sections