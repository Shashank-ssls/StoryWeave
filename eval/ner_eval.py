"""NER evaluation: GLiNER vs a hand-labeled chapter, per-type P/R/F1 (Phase 2).

Runs under ``.venv-ml`` (loads GLiNER). It ingests the sample with the SAME cleaning
the pipeline uses (so the evaluated text matches what the system stores), runs the
GLiNER floor over the chapter, and scores it against the gold labels at the
(normalized surface, type) level.

    .venv-ml\\Scripts\\python eval\\ner_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from storyweave.config import get_settings
from storyweave.db.repository import Repository
from storyweave.ingest.pipeline import ingest
from storyweave.ingest.work_config import find_work_config, load_work_config
from storyweave.nlp.cluster import normalize_surface
from storyweave.nlp.metrics import Item, per_type_prf1
from storyweave.nlp.pipeline import build_extractor

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "samples" / "the-hollow-crown"
GOLD_PATH = REPO_ROOT / "data" / "labels" / "the-hollow-crown_ch01.json"


def _chapter_clean_text(ordinal: int) -> str:
    """Ingest the sample into an in-memory DB and return a chapter's clean_text."""
    cfg = load_work_config(find_work_config(SAMPLE_DIR))
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        report = ingest(SAMPLE_DIR, repo, cfg)
        for chapter in repo.list_chapters(report.work_id):
            if chapter.ordinal == ordinal:
                return chapter.clean_text
    raise SystemExit(f"chapter {ordinal} not found in sample")


def run() -> dict[str, object]:
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    cfg = load_work_config(find_work_config(SAMPLE_DIR))
    settings = get_settings()

    text = _chapter_clean_text(int(gold["chapter_ordinal"]))
    extractor = build_extractor(cfg, settings)
    spans = extractor.extract(text)

    gold_items: list[Item] = [
        (normalize_surface(e["text"]), e["type"]) for e in gold["entities"]
    ]
    pred_items: list[Item] = [(normalize_surface(s.surface), s.type.value) for s in spans]

    report = per_type_prf1(gold_items, pred_items)

    print(f"NER eval — {gold['work_slug']} ch{gold['chapter_ordinal']} "
          f"(model={extractor.model_name}, threshold={extractor.threshold})")
    print(f"gold entities: {len(gold_items)}   predicted: {len(pred_items)}")
    print("-" * 60)
    for label in [k for k in report if k != "ALL"] + ["ALL"]:
        print(report[label].as_row(label))
    print("-" * 60)
    print("predicted:", sorted({(s, t) for s, t in pred_items}))
    return {"report": report, "n_pred": len(pred_items)}


if __name__ == "__main__":
    result = run()
    # Non-zero exit if nothing was predicted, so CI/gate can catch a dead model.
    sys.exit(0 if int(result["n_pred"]) > 0 else 1)  # type: ignore[call-overload]
