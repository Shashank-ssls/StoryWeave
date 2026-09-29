"""Would R4's validator accept the 19 hand-curated seed edges? (R4 integrity rule 3.)

    .\\dev.ps1
    python tools/r4_curated_check.py

The curated edges are NOT extraction output -- a person wrote them from a story bible --
so they are excluded from every R4 score. That exclusion is only honest if the curated
edges are also reported somewhere, which is what this does: it runs each one through the
same validator the extractor's proposals face, using its stored ``evidence_span`` as the
quote, and prints the verdict and reason.

The frozen baseline is opened READ-ONLY. Nothing is written anywhere.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import LEGACY_RELATION_MAP  # noqa: E402
from storyweave.extract.validator import (  # noqa: E402
    RelationProposal,
    ValidationContext,
    validate,
)
from tools import swconfig  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "evidence" / "v1_ninth_house.db"
SLUG = "the-ninth-house"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--slug", default=SLUG)
    args = ap.parse_args(argv)

    repo = swconfig.open_readonly(args.db)
    try:
        work = repo.get_work_by_slug(args.slug)
        assert work is not None and work.id is not None
        nodes = {n.id: n for n in repo.list_nodes(work.id) if n.id is not None}
        chapters = {c.ordinal: c.clean_text for c in repo.list_chapters(work.id)}
        labels: dict[int, list[str]] = {}
        for nid, node in nodes.items():
            names = [node.name]
            names.extend(lab.label for lab in repo.list_entity_labels(nid))
            labels[nid] = sorted({n for n in names if n}, key=len, reverse=True)
        curated = [
            e
            for e in repo.list_edges(work.id)
            if e.extraction_method.value in {"curated", "llm"}
            and e.extraction_method.value != "rule"
        ]
    finally:
        repo.close()

    context = ValidationContext(
        clean_text=chapters,
        node_types={nid: n.type for nid, n in nodes.items()},
        labels=labels,
    )

    print("=" * 78)
    print("CURATED SEED EDGES vs THE R4 VALIDATOR")
    print("=" * 78)
    print(
        "\nThese are hand-written records, not extraction output. They are EXCLUDED "
        "from\nevery R4 score; this table exists so that exclusion is auditable.\n"
    )
    print(f"curated/llm edges in {args.db.name}: {len(curated)}\n")

    verdicts: Counter[str] = Counter()
    for edge in curated:
        entry = LEGACY_RELATION_MAP.get(edge.relation)
        src = nodes.get(edge.source_id)
        tgt = nodes.get(edge.target_id)
        label = (
            f"{src.name if src else edge.source_id} -{edge.relation}-> "
            f"{tgt.name if tgt else edge.target_id}"
        )
        if entry is None or entry[1] is None:
            fate = entry[0].value if entry else "UNKNOWN"
            verdicts[f"NOT_IN_THE_TWELVE ({fate})"] += 1
            print(f"  REJECT  {label}\n            not one of the twelve [{fate}]")
            continue
        _fate, new, reverse = entry
        assert new is not None  # narrowed by the branch above
        source_id, target_id = edge.source_id, edge.target_id
        if reverse:
            source_id, target_id = target_id, source_id
        result = validate(
            RelationProposal(
                relation=new.value,
                source_id=source_id,
                target_id=target_id,
                quote=edge.evidence_span or "",
                quote_chapter=edge.revealed_chapter,
            ),
            context,
        )
        if result.ok:
            grade = result.grade.value if result.grade else "NONE"
            verdicts[f"ACCEPT ({grade})"] += 1
            print(f"  ACCEPT  {label} -> {new.value} [{grade}]")
        else:
            reason = result.reason.value if result.reason else "UNKNOWN"
            verdicts[f"REJECT ({reason})"] += 1
            print(f"  REJECT  {label} -> {new.value}\n            {reason}: {result.detail}")

    print("\nsummary:")
    for verdict, n in sorted(verdicts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {verdict:<40} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
