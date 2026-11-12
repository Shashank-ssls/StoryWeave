"""Build the retrofit R5 database: R4c's graph plus a local-LLM recall pass.

    .\\dev.ps1 -Ml
    python tools/check_local_env.py
    ollama serve                      # in that same shell, so OLLAMA_MODELS points at F:
    python tools/build_r5_db.py

Copies `ninth_house_r4c.db` to `ninth_house_r5.db` and adds LLM-proposed edges on top.
Every proposal goes through the SAME `extract/validator.py` as R4's relex proposals --
there is no bypass and no LLM-specific leniency. With Ollama unreachable the pass adds
nothing, says so, and leaves the R4c graph intact (rule 4).

The frozen baseline is never opened. Nothing is downloaded.
"""

# ruff: noqa: E501 - the few-shot block below is PROMPT TEXT. Its lines are real
# sentences from the novel and the exact JSON the model must imitate; wrapping them
# would change the prompt, and the prompt is the experiment.

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import (  # noqa: E402
    RELATION_RING,
    Edge,
    ExtractionMethod,
    Relation,
    RelationTier,
)
from storyweave.db.repository import Repository  # noqa: E402
from storyweave.extract.cues import DEFAULT_CUES  # noqa: E402
from storyweave.extract.llm_relations import (  # noqa: E402
    Candidate,
    LlmReport,
    OllamaClient,
    build_prompt,
    find_candidates,
    parse_json_relations,
)
from storyweave.extract.relations import _labels_for_nodes  # noqa: E402
from storyweave.extract.validator import (  # noqa: E402
    RelationProposal,
    ValidationContext,
    validate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data" / "retrofit" / "ninth_house_r4c.db"
DEFAULT_OUT = REPO_ROOT / "data" / "retrofit" / "ninth_house_r5.db"
CACHE = REPO_ROOT / ".local" / "llm_cache"
SLUG = "the-ninth-house"

RELATIONS = [r.value for r in Relation]

_TIER_FOR_RING = {1: RelationTier.SOCIAL, 2: RelationTier.STRUCTURAL}

# Few-shot examples. Sentences are real, from CHAPTERS 2 AND 13 ONLY -- both outside the
# scored set {9, 17, 37}.
#
# The KIN_OF example was CHANGED after the first run, and why matters. It originally used
# "Lord Fennick Oswald and his sister Brenna Oswald" (also ch2). That satisfies the
# chapter rule, but `Lord Fennick Oswald -Sibling-> Brenna Oswald` is a GOLD relation at
# chapter 17, so the example named the exact pair the run was graded on and the single
# true positive could not be called clean. It now uses a different ch2 pair
# (Cassian / Ione Ashcombe), which additionally demonstrates resolving a pronoun ("His")
# to a named entity -- the capability this phase is actually testing. Both runs are
# reported in evidence/retrofit/R5_RESULT.md; run A is kept as the sensitivity check.
# The third is a NEGATIVE: two names in one sentence with no relationship between them,
# which is the co-occurrence mistake that cost v1 160 of its 162 false positives.
FEW_SHOT = '''EXAMPLES:

THE SENTENCE: His sister, Ione Ashcombe, stood behind him rather than beside him, which Sorrel noticed and did not understand.
JSON: [{"relation": "KIN_OF", "head": "Cassian", "tail": "Ione Ashcombe", "quote": "His sister, Ione Ashcombe"}]

THE SENTENCE: Ser Robart Kell, Cassian's guard-captain, stood at the Regent's shoulder the whole sitting and said nothing, which Sorrel decided was probably his job.
JSON: [{"relation": "SERVES", "head": "Ser Robart Kell", "tail": "Cassian", "quote": "Ser Robart Kell, Cassian's guard-captain"}]

THE SENTENCE: Casimir Lowe and Pryn Voss took the eastern stalls.
JSON: []

'''


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--cap", type=int, default=8, help="per-chapter candidate cap")
    ap.add_argument("--slug", default=SLUG)
    ap.add_argument("--dump", type=Path,
                    default=REPO_ROOT / "evidence" / "retrofit" / "R5_proposals.jsonl")
    args = ap.parse_args(argv)

    if not args.source_db.exists():
        print(f"ERROR: {args.source_db} missing")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()
    shutil.copy(args.source_db, args.out)
    args.out.chmod(0o644)

    print(f"source : {args.source_db}")
    print(f"output : {args.out}")
    print(f"model  : {args.model}   cap/chapter: {args.cap}   cache: {CACHE}")

    client = OllamaClient(args.model, cache_dir=CACHE)
    report = LlmReport()
    if not client.available():
        print("\nOLLAMA UNREACHABLE — adding zero LLM edges, R4c graph left intact.")
        print("(this is the graceful-degradation path, not a failure)")
        return 0

    with Repository(args.out) as repo:
        work = repo.get_work_by_slug(args.slug)
        assert work is not None and work.id is not None

        candidates = find_candidates(repo, work.id)
        per_chapter: Counter[int] = Counter()
        capped: list[Candidate] = []
        for cand in candidates:
            if per_chapter[cand.chapter_ordinal] < args.cap:
                per_chapter[cand.chapter_ordinal] += 1
                capped.append(cand)
        report.candidates = len(capped)
        print(f"\ncandidates: {len(candidates)} found, {len(capped)} after the cap "
              f"({len(candidates) - len(capped)} dropped)")

        chapters = repo.list_chapters(work.id)
        context = ValidationContext(
            clean_text={c.ordinal: c.clean_text for c in chapters},
            node_types={n.id: n.type for n in repo.list_nodes(work.id) if n.id is not None},
            labels=_labels_for_nodes(repo, work.id),
            cues=DEFAULT_CUES,
        )
        # name -> node id, restricted to the entities named in each candidate.
        by_name: dict[str, int] = {}
        for node in repo.list_nodes(work.id):
            if node.id is not None:
                by_name.setdefault(node.name.lower(), node.id)
                for lab in repo.list_entity_labels(node.id):
                    by_name.setdefault(lab.label.lower(), node.id)

        args.dump.parent.mkdir(parents=True, exist_ok=True)
        dump = args.dump.open("w", encoding="utf-8")
        added = grade_counts = 0
        per_relation: Counter[str] = Counter()
        grades: Counter[str] = Counter()
        try:
            for i, cand in enumerate(capped, 1):
                raw = client.generate(build_prompt(cand, RELATIONS, FEW_SHOT), report)
                if raw is None:
                    report.note("LLM_UNREACHABLE")
                    continue
                parsed = parse_json_relations(raw)
                if parsed is None:
                    report.note("MALFORMED_JSON")
                    continue
                for item in parsed:
                    report.raw_proposals += 1
                    rel = item.get("relation", "")
                    head = item.get("head", "")
                    tail = item.get("tail", "")
                    quote = item.get("quote", "")
                    src = by_name.get(head.lower())
                    tgt = by_name.get(tail.lower())
                    proposal = RelationProposal(
                        relation=rel, source_id=src, target_id=tgt,
                        quote=quote, quote_chapter=cand.chapter_ordinal,
                        source_surface=head, target_surface=tail,
                    )
                    result = validate(proposal, context)
                    dump.write(json.dumps({
                        "chapter": cand.chapter_ordinal, "sentence": cand.sentence,
                        "context": cand.context, "relation": rel, "head": head,
                        "tail": tail, "quote": quote,
                        "ok": result.ok,
                        "reason": result.reason.value if result.reason else None,
                        "grade": result.grade.value if result.grade else None,
                        "detail": result.detail,
                    }) + "\n")
                    if not result.ok:
                        report.note(result.reason.value if result.reason else "UNKNOWN")
                        repo.add_validator_rejection(
                            work.id, rel,
                            result.reason.value if result.reason else "UNKNOWN",
                            source_surface=head, target_surface=tail,
                            source_id=src, target_id=tgt, quote=quote,
                            quote_chapter=cand.chapter_ordinal, detail=result.detail,
                        )
                        continue
                    assert result.relation and result.source_id and result.target_id
                    existing = repo.get_edge_by_relation_pair(
                        work.id, result.relation.value, result.source_id, result.target_id
                    )
                    if existing is not None:
                        repo.reinforce_edge(
                            existing,
                            first_seen_chapter=cand.chapter_ordinal,
                            revealed_chapter=cand.chapter_ordinal,
                            grade=result.grade, quote=quote,
                            quote_chapter=cand.chapter_ordinal,
                            surface_term=result.surface_term,
                        )
                        report.note("REINFORCED_EXISTING")
                        continue
                    repo.add_edge(Edge(
                        work_id=work.id, source_id=result.source_id,
                        target_id=result.target_id, relation=result.relation.value,
                        tier=_TIER_FOR_RING[RELATION_RING[result.relation]],
                        first_seen_chapter=cand.chapter_ordinal,
                        revealed_chapter=cand.chapter_ordinal,
                        extraction_method=ExtractionMethod.LLM,
                        evidence_span=quote, weight=1, grade=result.grade,
                        quote=quote, quote_chapter=cand.chapter_ordinal,
                        kin_role=result.kin_role, surface_term=result.surface_term,
                    ))
                    added += 1
                    per_relation[result.relation.value] += 1
                    grades[result.grade.value if result.grade else "NONE"] += 1
                if i % 20 == 0:
                    print(f"  {i}/{len(capped)} candidates "
                          f"({report.called} calls, {report.cache_hits} cached)")
        finally:
            dump.close()

        grade_counts = sum(grades.values())
        print(f"\ncalls: {report.called} live, {report.cache_hits} cached")
        print(f"raw LLM proposals: {report.raw_proposals}")
        print(f"edges added: {added} ({grade_counts} graded) -> {dict(per_relation)}")
        print(f"grades: {dict(grades)}")
        print("\nLLM proposal outcomes by reason:")
        for reason, n in sorted(report.per_reason.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {reason:<24} {n}")
        edges = repo.list_edges(work.id)
        stated = [e for e in edges if e.grade is not None and e.grade.value == "STATED"]
        llm = [e for e in edges if e.extraction_method is ExtractionMethod.LLM]
        print(f"\ntotal edges: {len(edges)} ({len(stated)} STATED, {len(llm)} from the LLM)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
