"""R4c probe 2: is input_spans really inert, and where do relations actually come from?

    .\\dev.ps1 -Ml
    python tools/r4c_api_probe2.py

Probe 1 showed ``input_spans`` changing nothing. Two things follow that must be checked
before R4c commits to a design:

1. Is ``input_spans`` inert in every mode, or only with ``flat_ner=False``? If it works
   under flat NER, the primary path is still available.
2. Probe 1's sentence produced ZERO relations even though both participants were returned
   as entities. If that is typical, then grounding was never the binding constraint and
   R4c's premise is wrong -- so this sweeps the relation threshold as a DIAGNOSTIC (it
   does not choose the shipped value, which stays at the configured 0.6) and reports how
   many relations exist at each level on real corpus sentences.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.config import get_settings  # noqa: E402
from storyweave.db.repository import Repository  # noqa: E402
from storyweave.nlp.extractor import configure_hf_cache  # noqa: E402
from storyweave.nlp.relex import ENTITY_LABELS, R4_RELATION_PROMPTS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r4b.db"

TEXT = (
    "Warden-Captain Orin Drask ran the Salt Quarter watch, and Juno Stray served "
    "under him for three years."
)


def main() -> int:
    settings = get_settings()
    configure_hf_cache(settings)
    from gliner import GLiNER  # noqa: PLC0415

    model = GLiNER.from_pretrained(settings.relex_model)
    prompts = list(R4_RELATION_PROMPTS)

    print("=" * 78)
    print("1. IS input_spans INERT IN BOTH NER MODES?")
    print("=" * 78)
    spans = [
        {"start": TEXT.index("Orin Drask"), "end": TEXT.index("Orin Drask") + 10},
        {"start": TEXT.index("Salt Quarter watch"), "end": TEXT.index("Salt Quarter watch") + 18},
        {"start": TEXT.index("Juno Stray"), "end": TEXT.index("Juno Stray") + 10},
    ]
    for flat in (False, True):
        base, _ = model.inference(
            texts=[TEXT], labels=ENTITY_LABELS, relations=prompts, threshold=0.3,
            relation_threshold=0.6, return_relations=True, flat_ner=flat)
        withs, _ = model.inference(
            texts=[TEXT], labels=ENTITY_LABELS, relations=prompts, threshold=0.3,
            relation_threshold=0.6, return_relations=True, flat_ner=flat,
            input_spans=[spans])
        b = sorted((e["start"], e["end"], e["text"]) for e in base[0])
        w = sorted((e["start"], e["end"], e["text"]) for e in withs[0])
        verdict = "IDENTICAL -> input_spans IGNORED" if b == w else "DIFFERENT -> honoured"
        print(f"  flat_ner={flat!s:<5}  free={len(b):>3} entities, "
              f"with input_spans={len(w):>3}   {verdict}")

    print("\n" + "=" * 78)
    print("2. DIAGNOSTIC relation-threshold sweep on real corpus chunks")
    print("   (diagnostic only -- the shipped threshold stays at the configured 0.6)")
    print("=" * 78)
    repo = Repository(DB)
    work = repo.get_work_by_slug("the-ninth-house")
    assert work is not None and work.id is not None
    chunks: list[str] = []
    for chapter in repo.list_chapters(work.id)[:6]:
        assert chapter.id is not None
        chunks.extend(c.text for c in repo.list_chunks(chapter.id))
    repo.close()
    print(f"\n  sampling {len(chunks)} chunks from the first 6 chapters\n")
    print(f"  {'rel_threshold':>14} {'relations returned':>20}")
    print("  " + "-" * 36)
    for rel_t in (0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1):
        total = 0
        for text in chunks:
            _e, r = model.inference(
                texts=[text], labels=ENTITY_LABELS, relations=prompts, threshold=0.3,
                relation_threshold=rel_t, return_relations=True, flat_ner=False)
            total += len(r[0])
        marker = "   <== SHIPPED" if abs(rel_t - 0.6) < 1e-9 else ""
        print(f"  {rel_t:>14.1f} {total:>20}{marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
