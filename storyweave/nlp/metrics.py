"""Pure precision/recall/F1 metrics for NER evaluation (Phase 2).

Set-based, entity-level: an entity is the pair (normalized_surface, type). No ML
here, so this is fully unit-tested in the light venv; the GLiNER run that produces
predictions lives in ``eval/ner_eval.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

Item = tuple[str, str]  # (normalized_surface, type_value)


@dataclass(frozen=True)
class PRF1:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int

    def as_row(self, label: str) -> str:
        return (
            f"{label:14} P={self.precision:5.2f} R={self.recall:5.2f} "
            f"F1={self.f1:5.2f}  (tp={self.tp} fp={self.fp} fn={self.fn})"
        )


def prf1[T](gold: set[T], pred: set[T]) -> PRF1:
    tp = len(gold & pred)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PRF1(precision, recall, f1, tp, fp, fn)


def per_type_prf1(gold_items: list[Item], pred_items: list[Item]) -> dict[str, PRF1]:
    """Per-type metrics plus a micro-averaged ``ALL`` row.

    Entities are de-duplicated within each (type) before scoring.
    """
    types = sorted({t for _, t in gold_items} | {t for _, t in pred_items})
    report: dict[str, PRF1] = {}
    for t in types:
        gold_t = {s for s, ty in gold_items if ty == t}
        pred_t = {s for s, ty in pred_items if ty == t}
        report[t] = prf1(gold_t, pred_t)
    report["ALL"] = prf1(set(gold_items), set(pred_items))
    return report
