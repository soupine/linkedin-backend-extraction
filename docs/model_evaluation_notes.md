# Model Evaluation Notes

## 1. Skill Extraction (NER / Pattern-based)

- Number of evaluation examples: TODO (e.g., 10 profiles)

### 1.1 Metrics (macro-averaged)

- Precision: TODO
- Recall:    TODO
- F1-score:  TODO

_Description:_  
We evaluated our rule-based skill extractor on N manually annotated profile snippets.
For each snippet, we compared the predicted skills against a gold list of skills and
computed precision, recall, and F1-score on the set level.

### 1.2 Observations

- Strengths:
  - TODO (e.g., works well on standard technical skills like "Python", "Machine Learning")
- Weaknesses:
  - TODO (e.g., misses very long skill phrases or very generic wording)
- Typical error cases:
  - TODO (e.g., splitting multi-word skills incorrectly, duplicates, etc.)


## 2. Text Quality Evaluation (Transformers)

### 2.1 Summary Quality

We use a transformer-based pipeline:

- Sentiment model: DistilBERT sentiment analysis
- Zero-shot model: BART (MNLI) for clarity/professionalism labels

Each summary evaluation returns:

- `overall_score` in [0, 1]
- `tone_label` (e.g., POSITIVE / NEGATIVE)
- `clarity_label` (e.g., "very clear and professional")

Example (good summary):

- Input length: TODO words
- Overall score: TODO
- Tone: TODO
- Clarity: TODO
- Suggestions (excerpt):
  - TODO (e.g., “Add 1–2 concrete achievements with measurable impact.”)

Example (weak summary):

- Input length: TODO words
- Overall score: TODO
- Tone: TODO
- Clarity: TODO
- Suggestions (excerpt):
  - TODO (e.g., “Consider writing in the first person to make your summary more personal.”)


### 2.2 Experience Descriptions

For each experience entry we evaluate:

- Combined text: description + title + company
- Same metrics: overall_score, tone, clarity
- Additional rule-based checks:
  - Bullet points
  - Action verbs
  - Presence of numbers/metrics

Example feedback snippet:

- Detected issues:
  - No action verbs at the beginning of bullet points
  - No numbers / measurable impact
- Suggestions:
  - Start bullet points with verbs like "Implemented", "Developed", "Led"
  - Add concrete metrics (e.g., “reduced runtime by 20%”)


## 3. Overall Profile Score

We compute a simple aggregated score:

- Input:
  - Summary overall_score
  - Average overall_score over all experience entries
- Output:
  - `overall.overall_score` in [0, 1]

Interpretation idea:

- 0.0–0.3: needs major improvements
- 0.3–0.6: okay, but can be improved
- 0.6–0.8: solid professional profile
- 0.8–1.0: very strong profile

(We can describe this mapping qualitatively in the report, even if the thresholds are heuristic.)
