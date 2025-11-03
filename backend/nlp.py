import re
import spacy
from typing import Dict, Any, List
from spacy.pipeline import EntityRuler
from patterns import TITLE_PATTERNS, SKILL_PATTERNS

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
