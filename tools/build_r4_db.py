"""Build the retrofit R4 database: R3's entities + relex relations + the validator.

    .\\dev.ps1 -Ml
    python tools/check_local_env.py
    python tools/build_r4_db.py

Copies `data/retrofit/ninth_house_r3.db` (entities, labels, no edges) to
`data/retrofit/ninth_house_r4.db` and runs the R4 relation producer over it. The frozen
v1 baseline is never opened for writing and is not an input here at all.

Nothing is downloaded: the relex checkpoint is already in the machine-wide HF cache on
F:, and the run is offline (`HF_HUB_OFFLINE=1`).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.repository import Repository  # noqa: E402
from storyweave.extract.relations import build_relations  # noqa: E402
from storyweave.extract.validator import (  # noqa: E402
    RelationProposal,
    ValidationResult,
)
from storyweave.ingest.work_config import (  # noqa: E402
    find_work_config,
    load_work_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r3.db"
DEFAULT_OUT = REPO_ROOT / "data" / "retrofit" / "ninth_house_r4.db"
DEFAULT_CORPUS = REPO_ROOT / "data" / "samples" / "the-ninth-house"


def build(source_db: Path, out: Path, corpus: Path, dump_proposals: Path | None = None) -> int:
    if not source_db.exists():
        print(f"ERROR: {source_db} does not exist - run tools/build_r3_db.py first")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    shutil.copy(source_db, out)
    out.chmod(0o644)  # the copy must be writable even if the source was not

    config = load_work_config(find_work_config(corpus))
    print(f"source db : {source_db}")
    print(f"output    : {out}")
    print(
        f"config    : relex_rel_threshold="
        f"{config.relations.relex_rel_threshold} (None = the configured default), "
        f"cue overrides={sorted(config.relations.cues)}"
    )

    with Repository(out) as repo:
        # Idempotent: every statement is CREATE ... IF NOT EXISTS, so this adds R4's
        # `validator_rejections` table and its index to the copied R3 database without
        # touching a single existing row. It also runs the additive edge migration.
        repo.initialize_schema()
        added = repo.migrate_edges_r4()
        print(f"migration : added edge columns {added or '(none needed)'}")
        works = repo.list_works()
        if not works:
            print("ERROR: no work in the source database")
            return 1
        work = works[0]
        assert work.id is not None
        print(f"work      : {work.slug} (id={work.id})")
        print(f"entities  : {len(repo.list_nodes(work.id))}")

        # Every proposal and its verdict, for the recall audit. Written whether the
        # proposal was accepted or refused: `validator_rejections` records only the
        # refusals, and "the model never proposed it" is a different loss stage from
        # "the validator refused it".
        sink: Callable[[RelationProposal, ValidationResult], None] | None = None
        dump: TextIO | None = None
        if dump_proposals is not None:
            dump_proposals.parent.mkdir(parents=True, exist_ok=True)
            dump = dump_proposals.open("w", encoding="utf-8")

            def sink(
                proposal: RelationProposal, result: ValidationResult
            ) -> None:
                assert dump is not None
                dump.write(json.dumps({
                    "relation": proposal.relation,
                    "source_id": proposal.source_id,
                    "target_id": proposal.target_id,
                    "source_surface": proposal.source_surface,
                    "target_surface": proposal.target_surface,
                    "quote_chapter": proposal.quote_chapter,
                    "quote": proposal.quote,
                    "score": proposal.score,
                    "ok": result.ok,
                    "reason": result.reason.value if result.reason else None,
                    "grade": result.grade.value if result.grade else None,
                    "final_source_id": result.source_id,
                    "final_target_id": result.target_id,
                    "detail": result.detail,
                }) + chr(10))

        try:
            report = build_relations(work.id, repo, config=config, proposal_sink=sink)
        finally:
            if dump is not None:
                dump.close()
                print(f"proposals : dumped to {dump_proposals}")
        print(f"relations : {report.summary()}")
        if report.degraded:
            print("ERROR: relex unavailable - refusing to report a degraded build")
            return 1
        print("rejections by reason:")
        for reason, n in sorted(
            report.rejections_by_reason.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            print(f"  {reason:<22} {n}")
        edges = repo.list_edges(work.id)
        stated = [e for e in edges if e.grade is not None and e.grade.value == "STATED"]
        print(f"edges     : {len(edges)} total, {len(stated)} STATED")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--dump-proposals",
        type=Path,
        default=None,
        help="write every relex proposal and its verdict as JSONL (the recall audit "
        "reads this)",
    )
    args = parser.parse_args(argv)
    return build(args.source_db, args.out, args.corpus, args.dump_proposals)


if __name__ == "__main__":
    raise SystemExit(main())
