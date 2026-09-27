"""Graph-density metrics for one filter configuration, at a set of chapters.

DELIVERABLE 1 of the measurement harness. For each requested chapter this computes the
metrics over exactly the node/edge set the chosen configuration would put in front of the
reader -- the fenced payload for ``api_payload``, or the payload after the frontend's own
client-side filters for ``rendered_view`` (see ``tools/swconfig.py``).

The fenced set is obtained by CALLING the real query layer (``query/fence.py`` over
``db/repository.py``), not by re-implementing its SQL, so the harness measures what the
app actually sends. ``rendered_view`` mirrors the TypeScript view model; its provenance is
named in ``swconfig.FILTER_DESCRIPTIONS``.

Usage:
    python tools/graph_metrics.py --db storyweave-demo.sqlite --label api_payload \
        --config api_payload --slug the-ninth-house --chapters 10,20,30,40 \
        --out evidence/metrics_api_payload.csv

``--label`` is free text and is what lands in the CSV's ``label`` column, so the same tool
can be pointed at a future rebuilt database with e.g. ``--label v2_fence_salience_backbone``.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# Make the repo root importable when run as `python tools/graph_metrics.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.query import fence  # noqa: E402

from tools import swconfig  # noqa: E402
from tools.swconfig import (  # noqa: E402
    API_PAYLOAD,
    IDENTITY_RELATIONS,
    NODE_KIND,
    PRINCIPAL_MIN_DEGREE,
    RENDERED_EVERYONE,
    RENDERED_VIEW,
)

#: CSV columns, in order. `label` and `config` identify the measured configuration.
FIELDNAMES: tuple[str, ...] = (
    "label",
    "config",
    "slug",
    "chapter",
    "nodes",
    "edges",
    "distinct_pairs",
    "parallel_edges",
    "self_loops",
    "mean_degree",
    "median_degree",
    "max_degree",
    "edge_density",
    "isolated_nodes",
    "degree1_nodes",
)


@dataclass
class VisibleSet:
    """The nodes and edges one configuration would send/draw at a chapter.

    ``edges`` are unordered endpoint pairs, one entry per edge actually sent (so parallel
    edges appear more than once in ``api_payload``). ``node_type`` and ``relation`` carry
    the breakdown keys.
    """

    node_ids: list[int] = field(default_factory=list)
    node_type: dict[int, str] = field(default_factory=dict)
    edges: list[tuple[int, int]] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)


# --- configuration: api_payload ---------------------------------------------- #


def payload_edges(repo: object, work_id: int, chapter: int) -> list[tuple[int, int, str, str]]:
    """The fenced edges AS THE ENDPOINT ACTUALLY SENDS THEM.

    ``graph/serialize.py:build_graph`` projects into an ``nx.DiGraph``, which cannot hold
    parallel edges: a second ``add_edge(s, t)`` for the same ORDERED pair overwrites the
    first, so same-direction duplicates never reach the client and the later row's
    attributes win. Reciprocal pairs (s,t) and (t,s) DO both survive, because the graph is
    directed. Measured on the-ninth-house at chapter 40: 1326 fenced edge rows collapse to
    the 1316 edges the API serves. The harness must measure the 1316, so the collapse is
    replicated here rather than counting raw rows.

    Returns (source_id, target_id, relation, evidence_span) in payload order.
    """
    collapsed: dict[tuple[int, int], tuple[str, str]] = {}
    for edge in fence.visible_edges(repo, work_id, chapter):  # type: ignore[arg-type]
        # dict assignment mirrors DiGraph.add_edge: last write for an ordered pair wins.
        collapsed[(edge.source_id, edge.target_id)] = (edge.relation, edge.evidence_span or "")
    return [(s, t, rel, span) for (s, t), (rel, span) in collapsed.items()]


def visible_api_payload(repo: object, work_id: int, chapter: int) -> VisibleSet:
    """Exactly what the /graph endpoint sends: the fence and nothing else."""
    out = VisibleSet()
    for node in fence.visible_nodes(repo, work_id, chapter):  # type: ignore[arg-type]
        assert node.id is not None
        out.node_ids.append(node.id)
        out.node_type[node.id] = node.type.value
    for source, target, relation, _span in payload_edges(repo, work_id, chapter):
        out.edges.append((source, target))
        out.relations.append(relation)
    return out


# --- configuration: rendered_view -------------------------------------------- #


def _pair_key(a: int, b: int) -> tuple[int, int]:
    """viewModel.ts pairKey(): the unordered endpoint pair."""
    return (a, b) if a < b else (b, a)


def visible_rendered(
    repo: object, work_id: int, chapter: int, cast: str = "principal"
) -> VisibleSet:
    """The fenced payload after the frontend's client-side filters.

    Mirrors ``buildViewModel`` (viewModel.ts) then ``visibleGraph`` (stemmaModel.ts) with
    all three kind toggles on. ``cast='principal'`` applies the degree/identity
    cast-reduction; ``cast='everyone'`` keeps every drawable node. Focus is None: the full
    shot is captured with no focus, and focusing only dims, so no node is kept by the focus
    clause in either case.
    """
    # (1) drop Concept/Event ("Also mentioned") and Title/unknown (never a node).
    kinds: dict[int, str] = {}
    node_type: dict[int, str] = {}
    for node in fence.visible_nodes(repo, work_id, chapter):  # type: ignore[arg-type]
        assert node.id is not None
        kind = NODE_KIND.get(node.type.value)
        if kind is None:
            continue
        kinds[node.id] = kind
        node_type[node.id] = node.type.value

    # (2)+(3) citation gate, then the parallel-edge merge on the unordered pair. This
    # consumes the PAYLOAD edges (post-DiGraph collapse), because that is what the browser
    # hands to buildViewModel -- not the raw fenced rows.
    merged: dict[tuple[int, int], str] = {}
    for source, target, relation, span in payload_edges(repo, work_id, chapter):
        if source not in kinds or target not in kinds:
            continue  # an endpoint is not drawn
        is_identity = relation in IDENTITY_RELATIONS
        if is_identity and not span.strip():
            continue  # R8 citation gate: an uncited identity edge is not drawn
        key = _pair_key(source, target)
        existing = merged.get(key)
        if existing is None:
            merged[key] = relation
        elif is_identity and existing not in IDENTITY_RELATIONS:
            merged[key] = relation  # identity absorbs the social/structural edge

    # Degree is computed over MERGED edges, exactly as viewModel.ts does.
    degree: Counter[int] = Counter()
    for a, b in merged:
        degree[a] += 1
        degree[b] += 1

    # (4) cast='principal': degree >= 2 OR touches an identity edge OR is the focus.
    identity_endpoints: set[int] = set()
    for (a, b), relation in merged.items():
        if relation in IDENTITY_RELATIONS:
            identity_endpoints.add(a)
            identity_endpoints.add(b)
    if cast == "everyone":
        visible = set(kinds)
    elif cast == "principal":
        visible = {
            nid
            for nid in kinds
            if degree[nid] >= PRINCIPAL_MIN_DEGREE or nid in identity_endpoints
        }
    else:
        raise ValueError(f"unknown cast {cast!r}; expected 'principal' or 'everyone'")

    # (5) keep an edge only when both endpoints survived.
    out = VisibleSet()
    out.node_ids = sorted(visible)
    out.node_type = {nid: node_type[nid] for nid in out.node_ids}
    for (a, b), relation in merged.items():
        if a in visible and b in visible:
            out.edges.append((a, b))
            out.relations.append(relation)
    return out


def visible_rendered_principal(repo: object, work_id: int, chapter: int) -> VisibleSet:
    return visible_rendered(repo, work_id, chapter, cast="principal")


def visible_rendered_everyone(repo: object, work_id: int, chapter: int) -> VisibleSet:
    return visible_rendered(repo, work_id, chapter, cast="everyone")


VISIBLE_FN = {
    API_PAYLOAD: visible_api_payload,
    RENDERED_VIEW: visible_rendered_principal,
    RENDERED_EVERYONE: visible_rendered_everyone,
}


# --- metrics ------------------------------------------------------------------ #


def compute_metrics(vs: VisibleSet) -> dict[str, object]:
    """Density metrics over a visible set. Raises on an impossible value."""
    n = len(vs.node_ids)
    e = len(vs.edges)
    if n < 0 or e < 0:
        raise ValueError(f"negative count: nodes={n} edges={e}")

    self_loops = sum(1 for a, b in vs.edges if a == b)
    distinct_pairs = len({_pair_key(a, b) for a, b in vs.edges if a != b})
    parallel_edges = e - self_loops - distinct_pairs

    # Degree = number of incident edges (a self-loop contributes 2, as 2E/N implies).
    degree: Counter[int] = Counter({nid: 0 for nid in vs.node_ids})
    for a, b in vs.edges:
        degree[a] += 1
        degree[b] += 1
    degrees = [degree[nid] for nid in vs.node_ids]

    mean_degree = (2 * e / n) if n else 0.0
    median_degree = statistics.median(degrees) if degrees else 0.0
    max_degree = max(degrees) if degrees else 0

    # Density is computed on DISTINCT simple pairs, so it is a true [0,1] density even for
    # `api_payload`, whose edge list contains parallel and reciprocal edges. The raw edge
    # count and the parallel surplus are reported alongside, so nothing is hidden.
    edge_density = (2 * distinct_pairs / (n * (n - 1))) if n >= 2 else 0.0

    if edge_density > 1.0:
        raise ValueError(
            f"impossible edge_density={edge_density!r} (n={n}, distinct_pairs={distinct_pairs})"
        )
    if max_degree < 0 or mean_degree < 0:
        raise ValueError(f"impossible degree: mean={mean_degree} max={max_degree}")

    return {
        "nodes": n,
        "edges": e,
        "distinct_pairs": distinct_pairs,
        "parallel_edges": parallel_edges,
        "self_loops": self_loops,
        "mean_degree": round(mean_degree, 4),
        "median_degree": round(float(median_degree), 4),
        "max_degree": max_degree,
        "edge_density": round(edge_density, 6),
        "isolated_nodes": sum(1 for d in degrees if d == 0),
        "degree1_nodes": sum(1 for d in degrees if d == 1),
    }


def breakdowns(vs: VisibleSet) -> tuple[Counter[str], Counter[str]]:
    """(count by node type, count by relation type) for this visible set."""
    return Counter(vs.node_type.values()), Counter(vs.relations)


# --- CLI ---------------------------------------------------------------------- #


def parse_chapters(raw: str) -> list[int]:
    chapters = [int(p) for p in raw.split(",") if p.strip()]
    if not chapters:
        raise ValueError("--chapters produced no chapter numbers")
    if any(c < 1 for c in chapters):
        raise ValueError(f"--chapters must all be >= 1, got {chapters}")
    return chapters


def collect(
    db: str | Path, config: str, label: str, slug: str, chapters: list[int]
) -> tuple[list[dict[str, object]], dict[int, Counter[str]], dict[int, Counter[str]]]:
    """Measure every chapter. Returns (rows, node-type breakdown, relation breakdown)."""
    if config not in VISIBLE_FN:
        raise ValueError(f"unknown --config {config!r}; expected one of {list(VISIBLE_FN)}")

    repo = swconfig.open_readonly(db)
    try:
        work = repo.get_work_by_slug(slug)
        if work is None or work.id is None:
            raise ValueError(f"work {slug!r} not found in {db}")
        chapter_count = len(repo.list_chapters(work.id))

        rows: list[dict[str, object]] = []
        by_type: dict[int, Counter[str]] = {}
        by_relation: dict[int, Counter[str]] = {}
        for chapter in chapters:
            vs = VISIBLE_FN[config](repo, work.id, chapter)
            metrics = compute_metrics(vs)
            # A populated work with nothing visible at its last chapter means the harness
            # (or the fence) is broken -- fail loudly rather than write the row.
            if metrics["nodes"] == 0 and chapter >= chapter_count:
                raise ValueError(
                    f"{config}: 0 visible nodes at chapter {chapter} of {chapter_count} "
                    f"for {slug!r} -- refusing to write the row"
                )
            rows.append(
                {"label": label, "config": config, "slug": slug, "chapter": chapter, **metrics}
            )
            by_type[chapter], by_relation[chapter] = breakdowns(vs)
        return rows, by_type, by_relation
    finally:
        repo.close()


def write_csv(rows: list[dict[str, object]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(FIELDNAMES))
        writer.writeheader()
        writer.writerows(rows)


def write_breakdown_csv(
    breakdown: dict[int, Counter[str]], kind: str, label: str, config: str, out: Path
) -> None:
    keys = sorted({k for counter in breakdown.values() for k in counter})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["label", "config", "chapter", kind, "count"])
        for chapter in sorted(breakdown):
            for key in keys:
                writer.writerow([label, config, chapter, key, breakdown[chapter].get(key, 0)])


def print_table(rows: list[dict[str, object]]) -> None:
    cols = list(FIELDNAMES)
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols} if rows else {}
    print(" | ".join(c.ljust(widths[c]) for c in cols))
    print("-+-".join("-" * widths[c] for c in cols))
    for row in rows:
        print(" | ".join(str(row[c]).ljust(widths[c]) for c in cols))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="SQLite database (opened read-only)")
    ap.add_argument("--config", required=True, choices=sorted(VISIBLE_FN), help="which filter set to apply")
    ap.add_argument("--label", default=None, help="label for the CSV rows (default: the config name)")
    ap.add_argument("--slug", default="the-ninth-house", help="work slug to measure")
    ap.add_argument("--chapters", default="10,20,30,40", help="comma-separated chapter numbers")
    ap.add_argument("--out", required=True, type=Path, help="output CSV path")
    args = ap.parse_args(argv)

    label = args.label or args.config
    rows, by_type, by_relation = collect(
        args.db, args.config, label, args.slug, parse_chapters(args.chapters)
    )
    write_csv(rows, args.out)
    stem = args.out.with_suffix("")
    write_breakdown_csv(by_type, "node_type", label, args.config, Path(f"{stem}_by_node_type.csv"))
    write_breakdown_csv(by_relation, "relation", label, args.config, Path(f"{stem}_by_relation.csv"))

    print(f"\n=== {label} ({args.config}) — {args.slug} ===")
    print_table(rows)
    print(f"\nwrote {args.out}")
    print(f"wrote {stem}_by_node_type.csv")
    print(f"wrote {stem}_by_relation.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
