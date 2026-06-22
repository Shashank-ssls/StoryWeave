"""Phase 2: NER P/R/F1 metrics (pure Python, light venv)."""

from __future__ import annotations

from storyweave.nlp.metrics import Item, per_type_prf1, prf1


def test_prf1_perfect() -> None:
    r = prf1({"a", "b"}, {"a", "b"})
    assert (r.precision, r.recall, r.f1) == (1.0, 1.0, 1.0)


def test_prf1_partial() -> None:
    r = prf1({"a", "b", "c"}, {"a", "b", "x"})
    assert r.tp == 2 and r.fp == 1 and r.fn == 1
    assert r.precision == 2 / 3
    assert r.recall == 2 / 3


def test_prf1_empty_pred() -> None:
    r = prf1({"a"}, set())
    assert r.precision == 0.0 and r.recall == 0.0 and r.f1 == 0.0


def test_per_type_report_has_all_and_per_type() -> None:
    gold: list[Item] = [("wren", "Character"), ("aldercross", "Place")]
    pred: list[Item] = [("wren", "Character"), ("coil", "Place")]
    report = per_type_prf1(gold, pred)
    assert report["Character"].f1 == 1.0
    assert report["Place"].tp == 0 and report["Place"].fp == 1 and report["Place"].fn == 1
    assert report["ALL"].tp == 1
