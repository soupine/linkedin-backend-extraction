import json
from typing import List, Set, Dict, Any

from nlp import collect_skills


def _normalize_skill(s: str) -> str:
    """
    Very simple normalization for comparison:
    - lowercase
    - strip spaces
    """
    return (s or "").strip().lower()


def precision_recall_f1(gold: Set[str], pred: Set[str]) -> Dict[str, float]:
    """
    Compute precision, recall, and F1 for one example.
    """
    if not gold and not pred:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not pred:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = len(gold & pred)
    fp = len(pred - gold)
    fn = len(gold - pred)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def load_eval_data(path: str) -> List[Dict[str, Any]]:
    """
    Load JSONL evaluation data from the given path.
    Each line must contain: { "id": ..., "text": ..., "gold_skills": [...] }
    """
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def evaluate_skill_extraction(path: str = "eval_data/skills_eval.jsonl") -> None:
    """
    Run skill extraction on the evaluation dataset and print overall metrics.
    """
    data = load_eval_data(path)
    if not data:
        print("No evaluation data found.")
        return

    all_precisions: List[float] = []
    all_recalls: List[float] = []
    all_f1s: List[float] = []

    for item in data:
        text = item.get("text", "") or ""
        gold_skills = item.get("gold_skills", []) or []

        # Run your skill extraction
        predicted_skills = collect_skills(text)

        gold_set = {_normalize_skill(s) for s in gold_skills}
        pred_set = {_normalize_skill(s) for s in predicted_skills}

        scores = precision_recall_f1(gold_set, pred_set)
        all_precisions.append(scores["precision"])
        all_recalls.append(scores["recall"])
        all_f1s.append(scores["f1"])

        print(f"Example ID {item.get('id')}:")
        print(f"  Gold:      {sorted(gold_set)}")
        print(f"  Predicted: {sorted(pred_set)}")
        print(
            f"  Precision={scores['precision']:.2f}, "
            f"Recall={scores['recall']:.2f}, "
            f"F1={scores['f1']:.2f}"
        )
        print("-" * 60)

    # Macro-average over examples
    avg_precision = sum(all_precisions) / len(all_precisions)
    avg_recall = sum(all_recalls) / len(all_recalls)
    avg_f1 = sum(all_f1s) / len(all_f1s)

    print("=== Overall skill extraction performance (macro-average) ===")
    print(f"Precision: {avg_precision:.3f}")
    print(f"Recall:    {avg_recall:.3f}")
    print(f"F1-score:  {avg_f1:.3f}")


if __name__ == "__main__":
    evaluate_skill_extraction()
