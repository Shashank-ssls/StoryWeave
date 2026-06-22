"""Tier-2 relation benchmark: learned GLiNER-RelEx vs hand-written rules (Phase 7a).

The deliverable is the COMPARISON. We score, on the CC0 sample, two relation systems
against the same hand-labeled social-relation gold:

  * GLiNER-RelEx (Tier-2, learned): per-relation precision/recall/F1.
  * Phase-3 co-occurrence rules (Tier-1, hand-written): the same metric — which is ~0
    on social relations *by construction*, because proximity rules can only emit
    structural labels (MemberOf, LocatedIn, …). To be fair to the rules we also report
    their "pair coverage": the share of gold social PAIRS they connect by some edge —
    i.e. rules find the right entities are related but cannot name *how*. That gap is
    exactly the job of the learned layer.

Runs under .venv-ml (loads GLiNER NER + the relex checkpoint). Weights cache to F:.

    .venv-ml\\Scripts\\python eval\\relex_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from storyweave.config import get_settings
from storyweave.db.models import Edge, RelationTier
from storyweave.db.repository import Repository
from storyweave.graph.builder import build_relationships
from storyweave.ingest.pipeline import ingest
from storyweave.ingest.work_config import find_work_config, load_work_config
from storyweave.nlp.cluster import normalize_surface
from storyweave.nlp.pipeline import extract_work
from storyweave.nlp.relex import (
    SYMMETRIC_RELATIONS,
    RelexExtractor,
    _node_surface_index,
    extract_social_relations,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "samples" / "the-hollow-crown"
GOLD_PATH = REPO_ROOT / "data" / "labels" / "the-hollow-crown_relations.json"

# Inverse relations are canonicalized to one direction so naming variants still match.
INVERSE: dict[str, str] = {"Child": "Parent", "Student": "Mentor"}

Triple = tuple[str, str, str]


def _norm_triple(src: str, rel: str, tgt: str) -> Triple:
    """Canonical comparable form: fold inverses, order-independent for symmetric rels."""
    if rel in INVERSE:
        rel, src, tgt = INVERSE[rel], tgt, src
    if rel in SYMMETRIC_RELATIONS:
        src, tgt = sorted((src, tgt))
    return (src, rel, tgt)


def _build_resolver(aliases: dict[str, list[str]]) -> dict[str, str]:
    """normalized surface -> canonical gold key."""
    out: dict[str, str] = {}
    for canon, variants in aliases.items():
        out[normalize_surface(canon)] = canon
        for v in variants:
            out[normalize_surface(v)] = canon
    return out


def _pred_triples(
    edges: list[Edge], id_to_name: dict[int, str], resolver: dict[str, str]
) -> set[Triple]:
    """Predicted edges -> canonical gold-keyed triples (drops edges to off-gold entities)."""
    triples: set[Triple] = set()
    for e in edges:
        s = resolver.get(normalize_surface(id_to_name.get(e.source_id, "")))
        t = resolver.get(normalize_surface(id_to_name.get(e.target_id, "")))
        if s and t and s != t:
            triples.add(_norm_triple(s, e.relation, t))
    return triples


def _prf1(gold: set[Triple], pred: set[Triple]) -> tuple[float, float, float, int, int, int]:
    tp = len(gold & pred)
    fp = len(pred - gold)
    fn = len(gold - pred)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f1, tp, fp, fn


def _report(title: str, gold: set[Triple], pred: set[Triple]) -> None:
    print(f"\n=== {title} ===")
    print(f"gold={len(gold)}  predicted={len(pred)}")
    relations = sorted({rel for _, rel, _ in gold} | {rel for _, rel, _ in pred})
    print(f"{'relation':<12}{'P':>6}{'R':>6}{'F1':>7}{'tp':>4}{'fp':>4}{'fn':>4}")
    for rel in relations:
        g = {x for x in gold if x[1] == rel}
        pr = {x for x in pred if x[1] == rel}
        p, r, f1, tp, fp, fn = _prf1(g, pr)
        print(f"{rel:<12}{p:>6.2f}{r:>6.2f}{f1:>7.2f}{tp:>4}{fp:>4}{fn:>4}")
    p, r, f1, tp, fp, fn = _prf1(gold, pred)
    print(f"{'ALL':<12}{p:>6.2f}{r:>6.2f}{f1:>7.2f}{tp:>4}{fp:>4}{fn:>4}")


def run() -> int:
    gold_raw = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    resolver = _build_resolver(gold_raw["aliases"])
    gold: set[Triple] = {
        _norm_triple(g["source"], g["relation"], g["target"]) for g in gold_raw["relations"]
    }
    gold_pairs = {tuple(sorted((s, t))) for s, _, t in gold}

    cfg = load_work_config(find_work_config(SAMPLE_DIR))
    settings = get_settings()

    with Repository(":memory:") as repo:
        repo.initialize_schema()
        report = ingest(SAMPLE_DIR, repo, cfg)
        wid = report.work_id
        extract_work(wid, repo, cfg, settings)          # GLiNER NER floor
        build_relationships(wid, repo, cfg)             # Tier-1 rules
        social = extract_social_relations(wid, repo, cfg, settings)  # Tier-2 relex

        id_to_name = {n.id: n.name for n in repo.list_nodes(wid) if n.id is not None}
        tier1 = repo.list_edges_by_tier(wid, RelationTier.STRUCTURAL)
        tier2 = repo.list_edges_by_tier(wid, RelationTier.SOCIAL)

    relex_pred = _pred_triples(tier2, id_to_name, resolver)
    rule_pred = _pred_triples(tier1, id_to_name, resolver)

    print(f"Relation benchmark — {gold_raw['work_slug']} (relex={settings.relex_model})")
    _report("LEARNED — GLiNER-RelEx (Tier-2)", gold, relex_pred)
    _report("HAND-WRITTEN — co-occurrence rules (Tier-1) on the SAME social gold", gold, rule_pred)

    # Fair-to-rules secondary metric: do rules at least connect the right pairs?
    rule_pairs = {tuple(sorted((x[0], x[2]))) for x in rule_pred}
    covered = len(gold_pairs & rule_pairs)
    print(
        f"\nTier-1 pair coverage: {covered}/{len(gold_pairs)} gold social pairs are "
        f"connected by SOME structural edge (rules find the link, not its social nature)."
    )
    print(f"\nTier-2 edges produced by relex: {social.edges_added}")
    return 0 if social.edges_added > 0 else 1


def diagnose(dump: bool, sweep: bool, rel_min: float = 0.05) -> int:
    """One low-threshold relex pass; dump anchored candidates and/or sweep thresholds.

    Efficient: runs inference ONCE at ``rel_min`` (floods candidates with scores) and
    post-filters in memory, so a full threshold sweep costs one model load, not N.
    """
    gold_raw = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    resolver = _build_resolver(gold_raw["aliases"])
    gold: set[Triple] = {
        _norm_triple(g["source"], g["relation"], g["target"]) for g in gold_raw["relations"]
    }
    cfg = load_work_config(find_work_config(SAMPLE_DIR))
    settings = get_settings()

    candidates: list[tuple[float, str, str, str]] = []  # (score, src_name, relation, tgt_name)
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = ingest(SAMPLE_DIR, repo, cfg).work_id
        extract_work(wid, repo, cfg, settings)
        build_relationships(wid, repo, cfg)
        surface_to_node = _node_surface_index(repo, wid)
        id_to_name = {n.id: n.name for n in repo.list_nodes(wid) if n.id is not None}

        ext = RelexExtractor(
            model_name=cfg.relations.relex_model,
            ner_threshold=cfg.relations.relex_ner_threshold or settings.relex_ner_threshold,
            rel_threshold=rel_min,
            settings=settings,
        )
        for chapter in repo.list_chapters(wid):
            assert chapter.id is not None
            for chunk in repo.list_chunks(chapter.id):
                for span in ext.extract(chunk.text):
                    s = surface_to_node.get(normalize_surface(span.source_surface))
                    t = surface_to_node.get(normalize_surface(span.target_surface))
                    if s and t and s != t:
                        candidates.append(
                            (span.score, id_to_name[s], span.relation, id_to_name[t])
                        )

    if dump:
        print(f"\n=== anchored relation candidates (rel_threshold>={rel_min}) ===")
        for score, sn, rel, tn in sorted(candidates, reverse=True):
            print(f"  {score:5.2f}  {sn} --[{rel}]--> {tn}")

    if sweep:
        print(f"\n=== threshold sweep (model={settings.relex_model}) ===")
        key_rels = ["Ally", "Betrayed", "Family", "Parent", "Serves"]
        per_rel = "".join(f"{r[:4]:>6}" for r in key_rels)
        header = f"{'thr':>5}{'P':>6}{'R':>6}{'F1':>7}   " + per_rel
        print(header + "   (per-relation = recall)")
        for thr in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90):
            pred: set[Triple] = set()
            for score, sn, rel, tn in candidates:
                if score < thr:
                    continue
                cs = resolver.get(normalize_surface(sn))
                ct = resolver.get(normalize_surface(tn))
                if cs and ct and cs != ct:
                    pred.add(_norm_triple(cs, rel, ct))
            p, r, f1, _tp, _fp, _fn = _prf1(gold, pred)
            recalls = ""
            for kr in key_rels:
                g = {x for x in gold if x[1] == kr}
                pr = {x for x in pred if x[1] == kr}
                rr = len(g & pr) / len(g) if g else 0.0
                recalls += f"{rr:>6.2f}"
            print(f"{thr:>5.2f}{p:>6.2f}{r:>6.2f}{f1:>7.2f}   {recalls}")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tier-2 relation benchmark / tuning.")
    parser.add_argument("--sweep", action="store_true", help="threshold sweep table")
    parser.add_argument("--dump", action="store_true", help="dump anchored candidates + scores")
    args = parser.parse_args()
    if args.sweep or args.dump:
        sys.exit(diagnose(dump=args.dump, sweep=args.sweep))
    sys.exit(run())
