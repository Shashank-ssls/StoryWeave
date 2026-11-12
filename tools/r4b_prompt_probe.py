"""R4b probe: does a GENERAL Organization prompt addition recover the missed class?

    .\\dev.ps1 -Ml
    python tools/r4b_prompt_probe.py

Runs the GLiNER floor over the sentences that contain a group-noun-headed phrase, once
with the shipped R3 label set and once with each candidate addition, and prints what
changes. The candidate prompts are general English descriptors of a collective ("group
of people", "military unit", "institution") -- none of them names anything in this book.

The gold annotation is never opened.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.repository import Repository  # noqa: E402
from storyweave.nlp.labels import DEFAULT_LABELS  # noqa: E402
from tools.r4b_org_diagnosis import GROUP_NOUNS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r3.db"
SLUG = "the-ninth-house"

CANDIDATES: dict[str, list[str]] = {
    "shipped R3 set": [],
    "+ 'group of people'": ["group of people"],
    "+ 'military unit'": ["military unit"],
    "+ 'institution'": ["institution"],
    "+ all three": ["group of people", "military unit", "institution"],
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--slug", default=SLUG)
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args(argv)

    repo = Repository(args.db)
    work = repo.get_work_by_slug(args.slug)
    assert work is not None and work.id is not None
    chapters = {c.ordinal: c.clean_text for c in repo.list_chapters(work.id)}
    repo.close()

    group_alt = "|".join(GROUP_NOUNS)
    phrase = re.compile(rf"\b(?:the\s+)?((?:[A-Z][\w'-]+\s+){{1,3}}(?:{group_alt}))\b")

    # Every sentence in the corpus that contains one of these phrases.
    sentences: list[tuple[str, str]] = []
    for text in chapters.values():
        for match in phrase.finditer(text):
            lo = text.rfind(".", 0, match.start()) + 1
            hi = text.find(".", match.end())
            hi = hi + 1 if hi != -1 else len(text)
            sentences.append((match.group(1).strip(), text[lo:hi].strip()))

    print(f"probing {len(sentences)} sentences, threshold={args.threshold}\n")

    from gliner import GLiNER  # noqa: PLC0415 - lazy, ML venv only

    from storyweave.config import get_settings  # noqa: PLC0415
    from storyweave.nlp.extractor import configure_hf_cache  # noqa: PLC0415

    settings = get_settings()
    configure_hf_cache(settings)
    model = GLiNER.from_pretrained(settings.gliner_model)

    for name, extra in CANDIDATES.items():
        labels = [*DEFAULT_LABELS, *extra]
        print("=" * 74)
        print(f"{name}   labels={labels}")
        print("=" * 74)
        for target, sentence in sentences:
            found = model.predict_entities(sentence, labels, threshold=args.threshold)
            hit = [
                f"{e['text']!r}->{e['label']}"
                for e in found
                if target.lower() in e["text"].lower() or e["text"].lower() in target.lower()
            ]
            status = ", ".join(hit) if hit else "MISSED"
            print(f"  {target!r:<30} {status}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
