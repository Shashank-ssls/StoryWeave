"""Score StoryWeave v1 against the reference annotation (v1 evaluation, phase 2).

The reference annotation in ``evidence/annotation/ch{09,17,37}.json`` is
**MODEL-GENERATED (GPT-5)**, one fresh session per chapter, single run each, with
paragraph indices, alias positions and evidence spans verified and corrected by hand
afterwards. See ``evidence/annotation/PROVENANCE.md``.

Everything this script prints is therefore **AGREEMENT between two systems**, v1 and
GPT-5 — not accuracy against human ground truth. The unqualified phrase "ground truth"
is not used. Every figure is reported per chapter as well as pooled.

The annotation files are opened read-only and are never modified. Validation failures
are LOGGED and the offending records EXCLUDED from scoring; nothing is repaired.

v1's side comes from the live database through the real ``Repository`` (no SQL is
re-implemented) and the real ``query/fence.py``, via ``tools/swconfig.open_readonly``.

Usage:
    python tools/eval_score.py --db storyweave-demo.sqlite --out evidence/scores_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

# Make the repo root importable when run as `python tools/eval_score.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import ALL_RELATIONS, NodeType  # noqa: E402
from storyweave.db.repository import Repository  # noqa: E402
from tools import swconfig  # noqa: E402
from tools.graph_metrics import payload_edges  # noqa: E402

CHAPTERS: tuple[int, ...] = (9, 17, 37)
SLUG = "the-ninth-house"
ANNOTATION_DIR = Path("evidence/annotation")

#: Stated verbatim in the output. Changing this changes every entity and relation score.
NORMALISATION_RULE = (
    "normalise(s): Unicode NFKC; replace the curly apostrophe U+2019 with '; casefold; "
    "strip surrounding whitespace and the characters \"'`.,;:!?()[]{}<>; collapse every "
    "internal whitespace run to one space; drop a leading article 'the ', 'a ' or 'an '; "
    "drop a trailing possessive \"'s\"."
)
ENTITY_MATCH_RULE = (
    "PRIMARY (strict): a v1 entity matches a reference entity iff "
    "normalise(v1.name) == normalise(reference.name) AND v1.type == reference.type. "
    "One-to-one: each reference entity is consumed by at most one v1 entity. "
    "SECONDARY (alias-aware, reported alongside, never instead): additionally allow a "
    "match when normalise(v1.name) equals the normalisation of ANY of the reference "
    "entity's surface_forms, with the type still required to be equal."
)
RELATION_MATCH_RULE = (
    "A v1 edge matches a reference relation iff their source entities matched, their "
    "target entities matched, and the relation string is equal. Reference relations with "
    "directed=true are matched on the ORDERED pair; with directed=false, either order is "
    "accepted. Endpoints that could not be matched to a v1 entity make the relation "
    "unmatchable, and it is counted as a reference-side miss."
)

FIELDNAMES: tuple[str, ...] = (
    "chapter", "section", "variant", "key", "metric", "value", "detail",
)


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #

_STRIP_CHARS = " \t\n\"'`.,;:!?()[]{}<>"


def normalise(s: str) -> str:
    text = unicodedata.normalize("NFKC", s).replace("’", "'").casefold()
    text = text.strip(_STRIP_CHARS)
    text = re.sub(r"\s+", " ", text)
    for article in ("the ", "a ", "an "):
        if text.startswith(article):
            text = text[len(article):]
            break
    if text.endswith("'s"):
        text = text[:-2]
    return text.strip(_STRIP_CHARS)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


@dataclass
class Failure:
    file: str
    field: str
    value: str
    reason: str
    fatal: bool


@dataclass
class Annotation:
    chapter: int
    path: Path
    data: dict[str, Any]
    text: str
    paragraphs: list[str]
    failures: list[Failure] = field(default_factory=list)
    #: indices into data["relations"] excluded from scoring by validation
    excluded_relations: set[int] = field(default_factory=set)
    excluded_entities: set[int] = field(default_factory=set)
    excluded_aliases: set[int] = field(default_factory=set)
    excluded_rejected: set[int] = field(default_factory=set)

    @property
    def scored_entities(self) -> list[dict[str, Any]]:
        return [
            e for i, e in enumerate(self.data["entities"])
            if i not in self.excluded_entities
        ]

    @property
    def scored_relations(self) -> list[dict[str, Any]]:
        return [
            r for i, r in enumerate(self.data["relations"])
            if i not in self.excluded_relations
        ]


def load_paragraphs(text: str) -> list[str]:
    """The numbered chapter text, split back into its [k] paragraphs."""
    out: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        match = re.match(r"^\[(\d+)\]\s*(.*)$", block, flags=re.S)
        if match is None:
            raise ValueError(f"paragraph block is not numbered: {block[:60]!r}")
        out.append(match.group(2))
    return out


def _quote_present(needle: str, haystack: str) -> bool:
    """Verbatim check, tolerant only of whitespace runs and apostrophe shape."""
    def flat(s: str) -> str:
        return re.sub(
            r"\s+", " ", unicodedata.normalize("NFKC", s).replace("’", "'")
        ).strip()

    return flat(needle) in flat(haystack)


def validate(chapter: int, directory: Path) -> Annotation:
    """Run every check in the brief. Fatal failures are flagged, not acted on here."""
    path = directory / f"ch{chapter:02d}.json"
    text_path = directory / f"ch{chapter:02d}_text.txt"
    raw = path.read_text(encoding="utf-8")
    text = text_path.read_text(encoding="utf-8")

    failures: list[Failure] = []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        ann = Annotation(chapter, path, {}, text, [], [
            Failure(path.name, "<file>", str(exc), "does not parse as JSON", True)
        ])
        return ann

    paragraphs = load_paragraphs(text)
    n_paragraphs = len(paragraphs)
    ann = Annotation(chapter, path, data, text, paragraphs)

    valid_types = {t.value for t in NodeType}
    valid_relations = set(ALL_RELATIONS)
    entity_names = {e.get("name", "") for e in data.get("entities", [])}

    # --- entities ---------------------------------------------------------- #
    for i, entity in enumerate(data.get("entities", [])):
        name = str(entity.get("name", ""))
        etype = str(entity.get("type", ""))
        if etype not in valid_types:
            failures.append(Failure(
                path.name, f"entities[{i}].type", etype,
                f"not one of v1's eight node types {sorted(valid_types)}", True,
            ))
        para = entity.get("first_paragraph")
        if not isinstance(para, int) or not (1 <= para <= n_paragraphs):
            failures.append(Failure(
                path.name, f"entities[{i}].first_paragraph ({name})", str(para),
                f"outside 1..{n_paragraphs}", False,
            ))
            ann.excluded_entities.add(i)

    # --- aliases ----------------------------------------------------------- #
    for i, alias in enumerate(data.get("aliases", [])):
        para = alias.get("first_paragraph")
        label = f"{alias.get('canonical')!r}<-{alias.get('alias')!r}"
        if not isinstance(para, int) or not (1 <= para <= n_paragraphs):
            failures.append(Failure(
                path.name, f"aliases[{i}].first_paragraph ({label})", str(para),
                f"outside 1..{n_paragraphs}", False,
            ))
            ann.excluded_aliases.add(i)
        if alias.get("canonical") not in entity_names:
            failures.append(Failure(
                path.name, f"aliases[{i}].canonical", str(alias.get("canonical")),
                "not present in entities[]", False,
            ))
            ann.excluded_aliases.add(i)

    # --- rejected_mentions -------------------------------------------------- #
    for i, rejected in enumerate(data.get("rejected_mentions", [])):
        para = rejected.get("paragraph")
        if not isinstance(para, int) or not (1 <= para <= n_paragraphs):
            failures.append(Failure(
                path.name, f"rejected_mentions[{i}].paragraph "
                f"({rejected.get('surface')!r})", str(para),
                f"outside 1..{n_paragraphs}", False,
            ))
            ann.excluded_rejected.add(i)

    # --- relations ---------------------------------------------------------- #
    for i, relation in enumerate(data.get("relations", [])):
        label = (
            f"{relation.get('source')!r} -{relation.get('relation')}-> "
            f"{relation.get('target')!r}"
        )
        rel = str(relation.get("relation", ""))
        if rel not in valid_relations:
            failures.append(Failure(
                path.name, f"relations[{i}].relation", rel,
                f"not one of v1's {len(ALL_RELATIONS)} relation names", True,
            ))
        for role in ("source", "target"):
            if relation.get(role) not in entity_names:
                failures.append(Failure(
                    path.name, f"relations[{i}].{role} ({label})",
                    str(relation.get(role)), "not present in entities[]", False,
                ))
                ann.excluded_relations.add(i)
        para = relation.get("paragraph")
        if not isinstance(para, int) or not (1 <= para <= n_paragraphs):
            failures.append(Failure(
                path.name, f"relations[{i}].paragraph ({label})", str(para),
                f"outside 1..{n_paragraphs}", False,
            ))
            ann.excluded_relations.add(i)
        evidence = str(relation.get("evidence", ""))
        if evidence and not _quote_present(evidence, text):
            failures.append(Failure(
                path.name, f"relations[{i}].evidence ({label})", evidence,
                "does not appear verbatim in the chapter text", False,
            ))
            ann.excluded_relations.add(i)

    ann.failures = failures
    return ann


# --------------------------------------------------------------------------- #
# v1's side
# --------------------------------------------------------------------------- #


@dataclass
class V1Chapter:
    """What v1 holds for one chapter."""

    chapter: int
    #: node_id -> canonical name / type, for nodes mentioned in this chapter
    names: dict[int, str]
    types: dict[int, str]
    #: node_id -> the distinct surface strings v1 saw for it in this chapter
    surfaces: dict[int, set[str]]
    #: surface strings in this chapter that never got clustered to a node
    unclustered: list[str]
    #: edges whose first_seen_chapter == this chapter
    edges_local: list[tuple[int, int, str, int]]
    #: edges between any two nodes mentioned in this chapter, any first_seen
    edges_cumulative: list[tuple[int, int, str, int]]
    #: fenced payload degree at this chapter, for the ranking metric
    degree: dict[int, int]


def load_v1(repo: Repository, work_id: int, chapters: tuple[int, ...]) -> dict[int, V1Chapter]:
    mentions = repo.list_mentions(work_id)
    nodes = {n.id: n for n in repo.list_nodes(work_id)}
    edges = repo.list_edges(work_id)

    out: dict[int, V1Chapter] = {}
    for chapter in chapters:
        chapter_mentions = [m for m in mentions if m.chapter_ordinal == chapter]
        surfaces: dict[int, set[str]] = defaultdict(set)
        unclustered: list[str] = []
        for m in chapter_mentions:
            if m.node_id is None:
                unclustered.append(m.surface)
            else:
                surfaces[m.node_id].add(m.surface)
        node_ids = set(surfaces)
        names = {i: nodes[i].name for i in node_ids}
        types = {i: nodes[i].type.value for i in node_ids}

        local = [
            (e.source_id, e.target_id, e.relation, int(e.tier))
            for e in edges if e.first_seen_chapter == chapter
        ]
        cumulative = [
            (e.source_id, e.target_id, e.relation, int(e.tier))
            for e in edges
            if e.source_id in node_ids and e.target_id in node_ids
        ]

        degree: Counter[int] = Counter({i: 0 for i in node_ids})
        for source, target, _rel, _span in payload_edges(repo, work_id, chapter):
            degree[source] += 1
            degree[target] += 1

        out[chapter] = V1Chapter(
            chapter, names, types, dict(surfaces), unclustered, local, cumulative,
            dict(degree),
        )
    return out


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


@dataclass
class EntityMatch:
    """Result of aligning v1's chapter entities with the reference's."""

    pairs: dict[int, int]  # v1 node_id -> reference entity index
    reverse: dict[int, int]  # reference index -> v1 node_id
    false_positives: list[int]  # v1 node ids with no reference counterpart
    false_negatives: list[int]  # reference indices with no v1 counterpart
    name_only: list[tuple[int, int]]  # (v1 node id, ref index) same name, DIFFERENT type


def match_entities(v1: V1Chapter, ann: Annotation, alias_aware: bool) -> EntityMatch:
    reference = ann.scored_entities
    ref_by_key: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, entity in enumerate(reference):
        ref_by_key[(normalise(str(entity["name"])), str(entity["type"]))].append(i)
    if alias_aware:
        for i, entity in enumerate(reference):
            for surface in entity.get("surface_forms") or []:
                key = (normalise(str(surface)), str(entity["type"]))
                if i not in ref_by_key[key]:
                    ref_by_key[key].append(i)

    # Name-only index, for separating "missed" from "found, typed differently".
    ref_by_name: dict[str, list[int]] = defaultdict(list)
    for i, entity in enumerate(reference):
        ref_by_name[normalise(str(entity["name"]))].append(i)

    used: set[int] = set()
    pairs: dict[int, int] = {}
    false_positives: list[int] = []
    name_only: list[tuple[int, int]] = []
    for node_id in sorted(v1.names):
        key = (normalise(v1.names[node_id]), v1.types[node_id])
        candidates = [i for i in ref_by_key.get(key, []) if i not in used]
        if candidates:
            chosen = candidates[0]
            used.add(chosen)
            pairs[node_id] = chosen
            continue
        false_positives.append(node_id)
        for i in ref_by_name.get(normalise(v1.names[node_id]), []):
            name_only.append((node_id, i))

    false_negatives = [i for i in range(len(reference)) if i not in used]
    reverse = {v: k for k, v in pairs.items()}
    return EntityMatch(pairs, reverse, false_positives, false_negatives, name_only)


def alias_pairwise(v1: V1Chapter, ann: Annotation) -> dict[str, Any]:
    """Pairwise same-cluster agreement over surface strings both sides know."""
    # Reference clusters: entity name + its surface_forms + any alias rows.
    ref_cluster: dict[str, str] = {}
    for entity in ann.scored_entities:
        canonical = str(entity["name"])
        ref_cluster[normalise(canonical)] = canonical
        for surface in entity.get("surface_forms") or []:
            ref_cluster[normalise(str(surface))] = canonical
    for i, alias in enumerate(ann.data.get("aliases", [])):
        if i in ann.excluded_aliases:
            continue
        ref_cluster[normalise(str(alias["alias"]))] = str(alias["canonical"])

    v1_cluster: dict[str, int] = {}
    for node_id, surfaces in v1.surfaces.items():
        v1_cluster[normalise(v1.names[node_id])] = node_id
        for surface in surfaces:
            v1_cluster[normalise(surface)] = node_id

    universe = sorted(set(ref_cluster) & set(v1_cluster))
    tp = fp = fn = tn = 0
    over: list[tuple[str, str, str]] = []
    under: list[tuple[str, str, str]] = []
    for a, b in combinations(universe, 2):
        same_ref = ref_cluster[a] == ref_cluster[b]
        same_v1 = v1_cluster[a] == v1_cluster[b]
        if same_ref and same_v1:
            tp += 1
        elif same_v1 and not same_ref:
            fp += 1
            over.append((a, b, f"v1 merged into {v1.names[v1_cluster[a]]!r}; reference "
                               f"keeps {ref_cluster[a]!r} and {ref_cluster[b]!r} apart"))
        elif same_ref and not same_v1:
            fn += 1
            under.append((a, b, f"reference groups both under {ref_cluster[a]!r}; v1 "
                                f"keeps {v1.names[v1_cluster[a]]!r} and "
                                f"{v1.names[v1_cluster[b]]!r} apart"))
        else:
            tn += 1
    precision, recall, f1 = prf(tp, fp, fn)
    return {
        "universe": universe, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "over_merges": over, "under_merges": under,
    }


@dataclass
class RelationScore:
    """Counts for one chapter.

    ``fn`` counts EVERY reference relation v1 does not have, including those whose
    endpoints v1 never found ("unmatchable"). Excluding those would flatter recall by
    scoring v1 only on the relations it had already half-solved, so they are counted as
    misses and also listed separately. ``fn_matchable_only`` is the narrower figure,
    reported alongside and never instead.
    """

    tp: int
    fp: int
    fn: int
    fn_matchable_only: int
    per_relation: dict[str, tuple[int, int, int]]
    per_tier: dict[int, tuple[int, int, int]]
    false_positives: list[str]
    false_negatives: list[str]
    unmatchable: list[str]


def score_relations(
    v1: V1Chapter, ann: Annotation, match: EntityMatch, edges: list[tuple[int, int, str, int]]
) -> RelationScore:
    reference = ann.scored_relations
    # Reference relations expressed in v1 node ids, where both endpoints matched.
    wanted: list[tuple[frozenset[int] | tuple[int, int], str, int, str]] = []
    unmatchable: list[str] = []
    unmatchable_keys: list[tuple[str, int, str]] = []  # (relation, tier, label)
    ref_index: dict[str, int] = {
        str(e["name"]): i for i, e in enumerate(ann.scored_entities)
    }
    for relation in reference:
        source_i = ref_index.get(str(relation["source"]))
        target_i = ref_index.get(str(relation["target"]))
        label = (
            f"{relation['source']} -{relation['relation']}-> {relation['target']}"
        )
        rel_name = str(relation["relation"])
        tier_no = int(relation["tier"])
        if source_i is None or target_i is None:
            unmatchable.append(f"{label} [endpoint missing from entities[]]")
            unmatchable_keys.append((rel_name, tier_no, label))
            continue
        source_v1 = match.reverse.get(source_i)
        target_v1 = match.reverse.get(target_i)
        if source_v1 is None or target_v1 is None:
            missing = []
            if source_v1 is None:
                missing.append(f"source {relation['source']!r}")
            if target_v1 is None:
                missing.append(f"target {relation['target']!r}")
            unmatchable.append(f"{label} [{' and '.join(missing)} not found by v1]")
            unmatchable_keys.append((rel_name, tier_no, label))
            continue
        key: frozenset[int] | tuple[int, int] = (
            (source_v1, target_v1) if relation.get("directed", True)
            else frozenset({source_v1, target_v1})
        )
        wanted.append((key, rel_name, tier_no, label))

    v1_keys: dict[tuple[int, int, str], int] = {}
    for source, target, rel, _tier in edges:
        v1_keys[(source, target, rel)] = v1_keys.get((source, target, rel), 0) + 1

    consumed: set[tuple[int, int, str]] = set()
    tp = 0
    per_relation: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    per_tier: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])
    false_negatives: list[str] = []
    for key, rel, tier, label in wanted:
        if isinstance(key, tuple):
            candidates = [(key[0], key[1], rel)]
        else:
            a, b = sorted(key)
            candidates = [(a, b, rel), (b, a, rel)]
        hit = next((c for c in candidates if c in v1_keys and c not in consumed), None)
        if hit is not None:
            consumed.add(hit)
            tp += 1
            per_relation[rel][0] += 1
            per_tier[tier][0] += 1
        else:
            per_relation[rel][2] += 1
            per_tier[tier][2] += 1
            false_negatives.append(label)

    false_positives: list[str] = []
    fp = 0
    for source, target, rel, tier in edges:
        if (source, target, rel) in consumed:
            continue
        fp += 1
        per_relation[rel][1] += 1
        per_tier[tier][1] += 1
        false_positives.append(
            f"{v1.names.get(source, source)} -{rel}-> {v1.names.get(target, target)}"
        )

    fn_matchable_only = len(false_negatives)
    # An unmatchable reference relation is still a relation v1 does not have.
    for rel_name, tier_no, label in unmatchable_keys:
        per_relation[rel_name][2] += 1
        per_tier[tier_no][2] += 1
        false_negatives.append(f"{label} [unmatchable: endpoint not found by v1]")
    fn = len(false_negatives)
    return RelationScore(
        tp, fp, fn, fn_matchable_only,
        {k: (v[0], v[1], v[2]) for k, v in per_relation.items()},
        {k: (v[0], v[1], v[2]) for k, v in per_tier.items()},
        false_positives, false_negatives, unmatchable,
    )


def ranking_metrics(labels: list[int]) -> dict[str, float | str]:
    """P@10, P@20, R@20, MAP and AUC for one ranked list of 0/1 labels."""
    n = len(labels)
    total_pos = sum(labels)
    out: dict[str, float | str] = {}

    for k in (10, 20):
        if n < k:
            out[f"P@{k}"] = f"not measured: only {n} ranked entities, fewer than {k}"
        else:
            out[f"P@{k}"] = sum(labels[:k]) / k
    if n < 20:
        out["Recall@20"] = f"not measured: only {n} ranked entities, fewer than 20"
    elif total_pos == 0:
        out["Recall@20"] = "not measured: no positive entities in this chapter"
    else:
        out["Recall@20"] = sum(labels[:20]) / total_pos

    if total_pos == 0:
        out["MAP"] = "not measured: no positive entities in this chapter"
        out["AUC"] = "not measured: no positive entities in this chapter"
        return out
    hits = 0
    precision_sum = 0.0
    for i, label in enumerate(labels, 1):
        if label:
            hits += 1
            precision_sum += hits / i
    out["MAP"] = precision_sum / total_pos

    negatives = n - total_pos
    if negatives == 0:
        out["AUC"] = "not measured: every ranked entity is positive"
    else:
        # Mann-Whitney U on the ranking positions (rank 1 = best), ties averaged.
        scores = np.asarray([n - i for i in range(n)], dtype=float)
        order = np.argsort(-scores, kind="stable")
        ranks = np.empty(n, dtype=float)
        ranks[order] = np.arange(1, n + 1, dtype=float)
        pos_rank_sum = float(sum(ranks[i] for i in range(n) if labels[i]))
        u = total_pos * negatives + total_pos * (total_pos + 1) / 2 - pos_rank_sum
        out["AUC"] = u / (total_pos * negatives)
    return out


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

PROVENANCE_BANNER = (
    "REFERENCE ANNOTATION: model-generated (GPT-5), one fresh session per chapter, "
    "single run each; paragraph indices, alias positions and evidence spans verified "
    "and corrected by hand; ch09 reindexed from 0- to 1-indexed. Every score below is "
    "AGREEMENT between two systems (StoryWeave v1 and GPT-5), NOT accuracy against "
    "human ground truth. See evidence/annotation/PROVENANCE.md."
)


class Report:
    """Accumulates CSV rows while the sections print themselves."""

    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def add(
        self, chapter: object, section: str, key: str, metric: str, value: object,
        detail: str = "", variant: str = "",
    ) -> None:
        self.rows.append({
            "chapter": chapter, "section": section, "variant": variant, "key": key,
            "metric": metric, "value": value, "detail": detail,
        })


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0915 - a report, read top to bottom
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="storyweave-demo.sqlite", type=Path)
    ap.add_argument("--annotations", default=ANNOTATION_DIR, type=Path)
    ap.add_argument("--slug", default=SLUG)
    ap.add_argument("--out", default=Path("evidence/scores_v1.csv"), type=Path)
    args = ap.parse_args(argv)

    report = Report()
    print(PROVENANCE_BANNER)
    print()

    # --- validation -------------------------------------------------------- #
    print("=" * 76)
    print("VALIDATION")
    print("=" * 76)
    annotations: dict[int, Annotation] = {}
    fatal = False
    for chapter in CHAPTERS:
        ann = validate(chapter, args.annotations)
        annotations[chapter] = ann
        fatals = [f for f in ann.failures if f.fatal]
        soft = [f for f in ann.failures if not f.fatal]
        print(f"\nch{chapter:02d}.json — {len(ann.data.get('entities', []))} entities, "
              f"{len(ann.data.get('relations', []))} relations, "
              f"{len(ann.paragraphs)} paragraphs")
        print(f"  parses as JSON: {'yes' if ann.data else 'NO'}")
        if not fatals and not soft:
            print("  all checks passed")
        for failure in fatals:
            print(f"  FATAL   {failure.field} = {failure.value!r}: {failure.reason}")
            fatal = True
        for failure in soft:
            print(f"  EXCLUDE {failure.field} = {failure.value!r}: {failure.reason}")
        for failure in ann.failures:
            report.add(chapter, "validation",
                       failure.field, "FATAL" if failure.fatal else "EXCLUDED",
                       failure.value, failure.reason)
        print(f"  excluded from scoring: {len(ann.excluded_entities)} entities, "
              f"{len(ann.excluded_relations)} relations, "
              f"{len(ann.excluded_aliases)} aliases, "
              f"{len(ann.excluded_rejected)} rejected_mentions")
        report.add(chapter, "validation", "excluded_entities", "count",
                   len(ann.excluded_entities))
        report.add(chapter, "validation", "excluded_relations", "count",
                   len(ann.excluded_relations))
        report.add(chapter, "validation", "excluded_aliases", "count",
                   len(ann.excluded_aliases))
        report.add(chapter, "validation", "excluded_rejected_mentions", "count",
                   len(ann.excluded_rejected))
        n_uncertain = len(ann.data.get("uncertain", []))
        print(f"  uncertain records (excluded from all scoring): {n_uncertain}")
        report.add(chapter, "uncertain", "records_excluded", "count", n_uncertain,
                   "free-text item/paragraph/question notes; they contain no entity or "
                   "relation records, so nothing was scored from them")

    if fatal:
        print("\nSTOPPING: a fatal validation failure (bad JSON, or an out-of-vocabulary "
              "type/relation) was found. No scores computed.")
        return 2

    # --- v1's side --------------------------------------------------------- #
    repo = swconfig.open_readonly(args.db)
    try:
        work = repo.get_work_by_slug(args.slug)
        if work is None or work.id is None:
            raise ValueError(f"work {args.slug!r} not found in {args.db}")
        v1_all = load_v1(repo, work.id, CHAPTERS)
    finally:
        repo.close()

    print()
    print("=" * 76)
    print("MATCH RULES (stated verbatim, as required)")
    print("=" * 76)
    print(f"\n{NORMALISATION_RULE}\n")
    print(f"{ENTITY_MATCH_RULE}\n")
    print(f"{RELATION_MATCH_RULE}\n")
    print("v1's entity set for a chapter = every canonical node with at least one row in")
    print("`mentions` for that chapter (repository.list_mentions). v1's relation set is")
    print("reported two ways: `chapter_local` = edges with first_seen_chapter == N, and")
    print("`cumulative` = every edge whose BOTH endpoints are mentioned in chapter N")
    print("regardless of when v1 first recorded it. Neither is privileged; the strict one")
    print("penalises v1 for relations it recorded in an earlier chapter, the generous one")
    print("credits v1 for relations this chapter's text may not support.")
    report.add("all", "match_rule", "normalisation", "text", NORMALISATION_RULE)
    report.add("all", "match_rule", "entity", "text", ENTITY_MATCH_RULE)
    report.add("all", "match_rule", "relation", "text", RELATION_MATCH_RULE)

    # --- entity detection --------------------------------------------------- #
    print()
    print("=" * 76)
    print("ENTITY DETECTION — agreement with the model-generated reference")
    print("=" * 76)
    pooled: dict[str, list[int]] = {"strict": [0, 0, 0], "alias_aware": [0, 0, 0]}
    pooled_by_type: dict[str, dict[str, list[int]]] = {
        "strict": defaultdict(lambda: [0, 0, 0]),
        "alias_aware": defaultdict(lambda: [0, 0, 0]),
    }
    matches: dict[int, EntityMatch] = {}
    for chapter in CHAPTERS:
        ann, v1 = annotations[chapter], v1_all[chapter]
        print(f"\n--- chapter {chapter} "
              f"(v1: {len(v1.names)} entities, reference: {len(ann.scored_entities)}) ---")
        for variant in ("strict", "alias_aware"):
            match = match_entities(v1, ann, alias_aware=(variant == "alias_aware"))
            if variant == "strict":
                matches[chapter] = match
            tp = len(match.pairs)
            fp = len(match.false_positives)
            fn = len(match.false_negatives)
            precision, recall, f1 = prf(tp, fp, fn)
            pooled[variant][0] += tp
            pooled[variant][1] += fp
            pooled[variant][2] += fn
            print(f"  [{variant}] TP={tp} FP={fp} FN={fn}  "
                  f"P={precision:.4f} R={recall:.4f} F1={f1:.4f}")
            for metric, value in (("precision", precision), ("recall", recall),
                                  ("f1", f1), ("tp", tp), ("fp", fp), ("fn", fn)):
                report.add(chapter, "entity", "ALL", metric, round(value, 6)
                           if isinstance(value, float) else value, variant=variant)

            # per node type
            by_type: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
            for node_id in match.pairs:
                by_type[v1.types[node_id]][0] += 1
            for node_id in match.false_positives:
                by_type[v1.types[node_id]][1] += 1
            for ref_i in match.false_negatives:
                by_type[str(ann.scored_entities[ref_i]["type"])][2] += 1
            for node_type in sorted(by_type):
                t, f_, n_ = by_type[node_type]
                p_, r_, f1_ = prf(t, f_, n_)
                pooled_by_type[variant][node_type][0] += t
                pooled_by_type[variant][node_type][1] += f_
                pooled_by_type[variant][node_type][2] += n_
                if variant == "strict":
                    print(f"      {node_type:<13} TP={t:<3} FP={f_:<3} FN={n_:<3} "
                          f"P={p_:.3f} R={r_:.3f} F1={f1_:.3f}")
                for metric, value in (("precision", p_), ("recall", r_), ("f1", f1_),
                                      ("tp", t), ("fp", f_), ("fn", n_)):
                    report.add(chapter, "entity", node_type, metric,
                               round(value, 6) if isinstance(value, float) else value,
                               variant=variant)

        match = matches[chapter]
        if match.false_positives:
            print("    v1 entities with no reference counterpart (strict FP):")
            for node_id in match.false_positives:
                print(f"      {v1.names[node_id]!r} ({v1.types[node_id]})")
                report.add(chapter, "entity_false_positive", v1.names[node_id],
                           "v1_type", v1.types[node_id], variant="strict")
        if match.false_negatives:
            print("    reference entities v1 did not produce (strict FN):")
            for ref_i in match.false_negatives:
                entity = ann.scored_entities[ref_i]
                print(f"      {entity['name']!r} ({entity['type']})")
                report.add(chapter, "entity_false_negative", str(entity["name"]),
                           "reference_type", str(entity["type"]), variant="strict")
        if match.name_only:
            print("    same name, DIFFERENT type (counted as both FP and FN above):")
            for node_id, ref_i in match.name_only:
                entity = ann.scored_entities[ref_i]
                print(f"      {v1.names[node_id]!r}: v1={v1.types[node_id]} "
                      f"reference={entity['type']}")
                report.add(chapter, "entity_type_disagreement", v1.names[node_id],
                           "v1_vs_reference",
                           f"{v1.types[node_id]} vs {entity['type']}")

    print("\n--- pooled over chapters 9, 17, 37 ---")
    for variant in ("strict", "alias_aware"):
        tp, fp, fn = pooled[variant]
        precision, recall, f1 = prf(tp, fp, fn)
        print(f"  [{variant}] TP={tp} FP={fp} FN={fn}  "
              f"P={precision:.4f} R={recall:.4f} F1={f1:.4f}")
        for metric, value in (("precision", precision), ("recall", recall), ("f1", f1),
                              ("tp", tp), ("fp", fp), ("fn", fn)):
            report.add("pooled", "entity", "ALL", metric,
                       round(value, 6) if isinstance(value, float) else value,
                       variant=variant)
        for node_type in sorted(pooled_by_type[variant]):
            t, f_, n_ = pooled_by_type[variant][node_type]
            p_, r_, f1_ = prf(t, f_, n_)
            if variant == "strict":
                print(f"      {node_type:<13} TP={t:<3} FP={f_:<3} FN={n_:<3} "
                      f"P={p_:.3f} R={r_:.3f} F1={f1_:.3f}")
            for metric, value in (("precision", p_), ("recall", r_), ("f1", f1_),
                                  ("tp", t), ("fp", f_), ("fn", n_)):
                report.add("pooled", "entity", node_type, metric,
                           round(value, 6) if isinstance(value, float) else value,
                           variant=variant)

    # --- alias clustering --------------------------------------------------- #
    print()
    print("=" * 76)
    print("ALIAS CLUSTERING — pairwise same-cluster agreement")
    print("=" * 76)
    print("Universe = surface strings BOTH sides know (v1 saw them as mentions in that")
    print("chapter, and the reference lists them as a name, surface_form or alias).")
    pooled_alias = [0, 0, 0]
    for chapter in CHAPTERS:
        result = alias_pairwise(v1_all[chapter], annotations[chapter])
        n = len(result["universe"])
        print(f"\n--- chapter {chapter}: {n} shared surface strings, "
              f"{n * (n - 1) // 2} pairs ---")
        print(f"  TP={result['tp']} FP={result['fp']} FN={result['fn']} "
              f"TN={result['tn']}")
        print(f"  P={result['precision']:.4f} R={result['recall']:.4f} "
              f"F1={result['f1']:.4f}")
        print(f"  over-merges (v1 joined what the reference separates): "
              f"{len(result['over_merges'])}")
        for a, b, why in result["over_merges"]:
            print(f"      {a!r} + {b!r} — {why}")
            report.add(chapter, "alias_over_merge", f"{a} + {b}", "detail", why)
        print(f"  under-merges (reference joined what v1 separates): "
              f"{len(result['under_merges'])}")
        for a, b, why in result["under_merges"]:
            print(f"      {a!r} + {b!r} — {why}")
            report.add(chapter, "alias_under_merge", f"{a} + {b}", "detail", why)
        pooled_alias[0] += int(result["tp"])
        pooled_alias[1] += int(result["fp"])
        pooled_alias[2] += int(result["fn"])
        for metric in ("precision", "recall", "f1", "tp", "fp", "fn", "tn"):
            value = result[metric]
            report.add(chapter, "alias", "pairwise", metric,
                       round(value, 6) if isinstance(value, float) else value)
        report.add(chapter, "alias", "pairwise", "over_merges",
                   len(result["over_merges"]))
        report.add(chapter, "alias", "pairwise", "under_merges",
                   len(result["under_merges"]))
        report.add(chapter, "alias", "pairwise", "shared_surface_strings", n)
    precision, recall, f1 = prf(*pooled_alias)
    print(f"\n--- pooled --- TP={pooled_alias[0]} FP={pooled_alias[1]} "
          f"FN={pooled_alias[2]}  P={precision:.4f} R={recall:.4f} F1={f1:.4f}")
    for metric, value in (("precision", precision), ("recall", recall), ("f1", f1),
                          ("tp", pooled_alias[0]), ("fp", pooled_alias[1]),
                          ("fn", pooled_alias[2])):
        report.add("pooled", "alias", "pairwise", metric,
                   round(value, 6) if isinstance(value, float) else value)

    # --- relations ----------------------------------------------------------- #
    print()
    print("=" * 76)
    print("RELATIONS — agreement with the model-generated reference")
    print("=" * 76)
    for variant in ("chapter_local", "cumulative"):
        print(f"\n######## variant: {variant} ########")
        pooled_rel = [0, 0, 0]
        pooled_per_relation: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
        pooled_per_tier: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])
        for chapter in CHAPTERS:
            ann, v1 = annotations[chapter], v1_all[chapter]
            edges = v1.edges_local if variant == "chapter_local" else v1.edges_cumulative
            score = score_relations(v1, ann, matches[chapter], edges)
            precision, recall, f1 = prf(score.tp, score.fp, score.fn)
            print(f"\n--- chapter {chapter} (v1: {len(edges)} edges, reference: "
                  f"{len(ann.scored_relations)} relations, "
                  f"{len(score.unmatchable)} unmatchable) ---")
            print(f"  micro: TP={score.tp} FP={score.fp} FN={score.fn}  "
                  f"P={precision:.4f} R={recall:.4f} F1={f1:.4f}")
            p_m, r_m, f1_m = prf(score.tp, score.fp, score.fn_matchable_only)
            print(f"  micro, counting ONLY reference relations whose endpoints v1 "
                  f"found (narrower, reported alongside): FN={score.fn_matchable_only} "
                  f"P={p_m:.4f} R={r_m:.4f} F1={f1_m:.4f}")
            for metric, value in (("micro_precision_matchable_only", p_m),
                                  ("micro_recall_matchable_only", r_m),
                                  ("micro_f1_matchable_only", f1_m),
                                  ("fn_matchable_only", score.fn_matchable_only)):
                report.add(chapter, "relation", "ALL", metric,
                           round(value, 6) if isinstance(value, float) else value,
                           variant=variant)
            f1s = []
            for rel in sorted(score.per_relation):
                t, f_, n_ = score.per_relation[rel]
                p_, r_, rf1 = prf(t, f_, n_)
                f1s.append(rf1)
                print(f"      {rel:<16} TP={t:<3} FP={f_:<4} FN={n_:<3} "
                      f"P={p_:.3f} R={r_:.3f} F1={rf1:.3f}")
                pooled_per_relation[rel][0] += t
                pooled_per_relation[rel][1] += f_
                pooled_per_relation[rel][2] += n_
                for metric, value in (("precision", p_), ("recall", r_), ("f1", rf1),
                                      ("tp", t), ("fp", f_), ("fn", n_)):
                    report.add(chapter, "relation", rel, metric,
                               round(value, 6) if isinstance(value, float) else value,
                               variant=variant)
            macro = sum(f1s) / len(f1s) if f1s else 0.0
            print(f"  macro-F1 over {len(f1s)} relation types: {macro:.4f}")
            print(f"  micro-F1: {f1:.4f}")
            report.add(chapter, "relation", "ALL", "macro_f1", round(macro, 6),
                       f"over {len(f1s)} relation types", variant=variant)
            for metric, value in (("micro_precision", precision),
                                  ("micro_recall", recall), ("micro_f1", f1),
                                  ("tp", score.tp), ("fp", score.fp), ("fn", score.fn)):
                report.add(chapter, "relation", "ALL", metric,
                           round(value, 6) if isinstance(value, float) else value,
                           variant=variant)
            for tier in sorted(score.per_tier):
                t, f_, n_ = score.per_tier[tier]
                p_, r_, tf1 = prf(t, f_, n_)
                print(f"      tier {tier}: TP={t} FP={f_} FN={n_} "
                      f"P={p_:.3f} R={r_:.3f} F1={tf1:.3f}")
                pooled_per_tier[tier][0] += t
                pooled_per_tier[tier][1] += f_
                pooled_per_tier[tier][2] += n_
                for metric, value in (("precision", p_), ("recall", r_), ("f1", tf1),
                                      ("tp", t), ("fp", f_), ("fn", n_)):
                    report.add(chapter, "relation_tier", f"tier{tier}", metric,
                               round(value, 6) if isinstance(value, float) else value,
                               variant=variant)
            if score.unmatchable:
                print("    reference relations that could not be matched (an endpoint "
                      "is not in v1's entity set):")
                for label in score.unmatchable:
                    print(f"      {label}")
                    report.add(chapter, "relation_unmatchable", label, "reason",
                               "endpoint not found by v1", variant=variant)
            if score.false_negatives:
                print("    reference relations v1 lacks (FN):")
                for label in score.false_negatives:
                    print(f"      {label}")
                    report.add(chapter, "relation_false_negative", label, "detail", "",
                               variant=variant)
            if score.false_positives:
                shown = score.false_positives[:15]
                print(f"    v1 relations with no reference counterpart (FP), showing "
                      f"{len(shown)} of {len(score.false_positives)}:")
                for label in shown:
                    print(f"      {label}")
                for label in score.false_positives:
                    report.add(chapter, "relation_false_positive", label, "detail", "",
                               variant=variant)
            pooled_rel[0] += score.tp
            pooled_rel[1] += score.fp
            pooled_rel[2] += score.fn

        precision, recall, f1 = prf(*pooled_rel)
        macro_f1s = [
            prf(*pooled_per_relation[r])[2] for r in sorted(pooled_per_relation)
        ]
        macro = sum(macro_f1s) / len(macro_f1s) if macro_f1s else 0.0
        print(f"\n--- pooled [{variant}] --- TP={pooled_rel[0]} FP={pooled_rel[1]} "
              f"FN={pooled_rel[2]}")
        print(f"  micro P={precision:.4f} R={recall:.4f} F1={f1:.4f}   "
              f"macro-F1 over {len(macro_f1s)} relation types: {macro:.4f}")
        for rel in sorted(pooled_per_relation):
            t, f_, n_ = pooled_per_relation[rel]
            p_, r_, rf1 = prf(t, f_, n_)
            print(f"      {rel:<16} TP={t:<3} FP={f_:<4} FN={n_:<3} F1={rf1:.3f}")
            for metric, value in (("precision", p_), ("recall", r_), ("f1", rf1),
                                  ("tp", t), ("fp", f_), ("fn", n_)):
                report.add("pooled", "relation", rel, metric,
                           round(value, 6) if isinstance(value, float) else value,
                           variant=variant)
        for tier in sorted(pooled_per_tier):
            t, f_, n_ = pooled_per_tier[tier]
            p_, r_, tf1 = prf(t, f_, n_)
            print(f"      tier {tier}: TP={t} FP={f_} FN={n_} F1={tf1:.3f}")
            for metric, value in (("precision", p_), ("recall", r_), ("f1", tf1),
                                  ("tp", t), ("fp", f_), ("fn", n_)):
                report.add("pooled", "relation_tier", f"tier{tier}", metric,
                           round(value, 6) if isinstance(value, float) else value,
                           variant=variant)
        for metric, value in (("micro_precision", precision), ("micro_recall", recall),
                              ("micro_f1", f1), ("macro_f1", macro)):
            report.add("pooled", "relation", "ALL", metric, round(value, 6),
                       variant=variant)

    # --- Tier 3 identity ------------------------------------------------------ #
    print()
    print("=" * 76)
    print("TIER-3 IDENTITY — reported as COUNTS, not F1")
    print("=" * 76)
    total_ref = total_v1 = total_matched = 0
    for chapter in CHAPTERS:
        ann, v1 = annotations[chapter], v1_all[chapter]
        ref_t3 = [r for r in ann.scored_relations if int(r["tier"]) == 3]
        v1_t3_local = [e for e in v1.edges_local if e[3] == 3]
        v1_t3_cum = [e for e in v1.edges_cumulative if e[3] == 3]
        matched = 0
        for relation in ref_t3:
            if any(e[2] == str(relation["relation"]) for e in v1_t3_cum):
                matched += 1
        print(f"\n  chapter {chapter}: reference Tier-3 records = {len(ref_t3)}; "
              f"v1 Tier-3 edges first_seen here = {len(v1_t3_local)} "
              f"(among this chapter's entities, any chapter: {len(v1_t3_cum)}); "
              f"matched = {matched}")
        for t3_source, t3_target, rel, _tier in v1_t3_local:
            print(f"      v1 holds: {rel} {v1.names.get(t3_source, t3_source)} -> "
                  f"{v1.names.get(t3_target, t3_target)}")
        report.add(chapter, "tier3", "reference_count", "count", len(ref_t3))
        report.add(chapter, "tier3", "v1_count_chapter_local", "count",
                   len(v1_t3_local))
        report.add(chapter, "tier3", "v1_count_cumulative", "count", len(v1_t3_cum))
        report.add(chapter, "tier3", "matched_count", "count", matched)
        total_ref += len(ref_t3)
        total_v1 += len(v1_t3_local)
        total_matched += matched

    v1_ch37 = [e for e in v1_all[37].edges_local if e[3] == 3]
    ref_ch37_t3 = [r for r in annotations[37].scored_relations if int(r["tier"]) == 3]
    has_transmigrated = any(e[2] == "TRANSMIGRATED_INTO" for e in v1_ch37)
    print(f"\n  REQUIRED STATEMENT — v1 holds TRANSMIGRATED_INTO at ch37: "
          f"{has_transmigrated}.")
    for source, target, rel, _tier in v1_ch37:
        print(f"      {rel}: {v1_all[37].names.get(source, source)} -> "
              f"{v1_all[37].names.get(target, target)}")
    print(f"  The reference for ch37 contains {len(ref_ch37_t3)} Tier-3 record(s), "
          f"so a matching Tier-3 record is "
          f"{'PRESENT' if ref_ch37_t3 else 'ABSENT'}.")
    print(f"  Pooled: reference Tier-3 = {total_ref}, v1 Tier-3 (chapter-local) = "
          f"{total_v1}, matched = {total_matched}.")
    report.add(37, "tier3", "v1_holds_TRANSMIGRATED_INTO", "bool", has_transmigrated)
    report.add(37, "tier3", "reference_has_matching_tier3", "bool",
               bool(ref_ch37_t3))
    report.add("pooled", "tier3", "reference_count", "count", total_ref)
    report.add("pooled", "tier3", "v1_count_chapter_local", "count", total_v1)
    report.add("pooled", "tier3", "matched_count", "count", total_matched)

    # --- significance ranking -------------------------------------------------- #
    print()
    print("=" * 76)
    print("SIGNIFICANCE RANKING — v1 entities ranked by fenced degree at chapter N")
    print("=" * 76)
    print("Positive class = reference entity with significant=true, transferred onto the")
    print("v1 entity it matched (strict match). A v1 entity with no reference")
    print("counterpart is a negative.")
    pooled_labels: list[int] = []
    for chapter in CHAPTERS:
        ann, v1 = annotations[chapter], v1_all[chapter]
        match = matches[chapter]
        ranked = sorted(v1.names, key=lambda i: (-v1.degree.get(i, 0), v1.names[i]))
        labels: list[int] = []
        for node_id in ranked:
            matched_ref = match.pairs.get(node_id)
            positive = (
                matched_ref is not None
                and bool(ann.scored_entities[matched_ref].get("significant"))
            )
            labels.append(1 if positive else 0)
        metrics = ranking_metrics(labels)
        print(f"\n--- chapter {chapter}: {len(ranked)} v1 entities ranked, "
              f"{sum(labels)} positive ---")
        for rank, node_id in enumerate(ranked[:20], 1):
            flag = "+" if labels[rank - 1] else " "
            print(f"    {rank:>2} {flag} {v1.names[node_id]:<22} "
                  f"degree={v1.degree.get(node_id, 0)}")
        for metric, rank_value in metrics.items():
            shown_value = (
                f"{rank_value:.4f}" if isinstance(rank_value, float) else rank_value
            )
            print(f"  {metric}: {shown_value}")
            report.add(chapter, "ranking", metric, "value",
                       round(rank_value, 6)
                       if isinstance(rank_value, float) else rank_value)
        report.add(chapter, "ranking", "ranked_entities", "count", len(ranked))
        report.add(chapter, "ranking", "positive_entities", "count", sum(labels))
        pooled_labels += labels

    print(f"\n--- pooled (the three ranked lists concatenated in chapter order, "
          f"{len(pooled_labels)} entities, {sum(pooled_labels)} positive) ---")
    print("  NOTE: concatenating ranked lists is not a single ranking; these pooled")
    print("  figures describe the concatenation and nothing more.")
    for metric, rank_value in ranking_metrics(pooled_labels).items():
        shown_value = (
            f"{rank_value:.4f}" if isinstance(rank_value, float) else rank_value
        )
        print(f"  {metric}: {shown_value}")
        report.add("pooled", "ranking", metric, "value",
                   round(rank_value, 6)
                   if isinstance(rank_value, float) else rank_value)

    # --- rejected mentions ------------------------------------------------------ #
    print()
    print("=" * 76)
    print("REJECTED MENTIONS — strings the reference says should NOT be entities")
    print("=" * 76)
    total_rejected = total_emitted = 0
    for chapter in CHAPTERS:
        ann, v1 = annotations[chapter], v1_all[chapter]
        rejected = [
            r for i, r in enumerate(ann.data.get("rejected_mentions", []))
            if i not in ann.excluded_rejected
        ]
        # Two ways v1 can have emitted a rejected string: as an entity's canonical
        # name, or as a mention surface it clustered into some entity. Both count,
        # and which one it was is stated -- they are different failures.
        v1_strings: dict[str, tuple[int, str]] = {}
        for node_id, surfaces in v1.surfaces.items():
            for surface in surfaces:
                v1_strings[normalise(surface)] = (node_id, "mention surface")
        for node_id in v1.names:
            v1_strings[normalise(v1.names[node_id])] = (node_id, "canonical name")
        emitted = []
        for record in rejected:
            key = normalise(str(record["surface"]))
            if key in v1_strings:
                emitted.append((record, *v1_strings[key]))
        print(f"\n--- chapter {chapter}: {len(rejected)} rejected strings scored, "
              f"v1 emitted {len(emitted)} of them ---")
        for record, node_id, how in emitted:
            print(f"      {record['surface']!r} -> v1 {how} of entity "
                  f"{v1.names[node_id]!r} ({v1.types[node_id]})")
            print(f"          reference reason: {record['why']}")
            report.add(chapter, "rejected_mention_emitted", str(record["surface"]),
                       f"v1_{how.replace(' ', '_')}",
                       f"{v1.names[node_id]} ({v1.types[node_id]})",
                       str(record["why"]))
        rate = len(emitted) / len(rejected) if rejected else 0.0
        print(f"  emitted-rate on rejected strings: {rate:.4f}")
        report.add(chapter, "rejected_mentions", "scored", "count", len(rejected))
        report.add(chapter, "rejected_mentions", "emitted_by_v1", "count", len(emitted))
        report.add(chapter, "rejected_mentions", "emitted_rate", "value",
                   round(rate, 6))
        total_rejected += len(rejected)
        total_emitted += len(emitted)
    rate = total_emitted / total_rejected if total_rejected else 0.0
    print(f"\n--- pooled --- {total_emitted} of {total_rejected} rejected strings were "
          f"emitted by v1 (rate {rate:.4f})")
    report.add("pooled", "rejected_mentions", "scored", "count", total_rejected)
    report.add("pooled", "rejected_mentions", "emitted_by_v1", "count", total_emitted)
    report.add("pooled", "rejected_mentions", "emitted_rate", "value", round(rate, 6))

    # --- write --------------------------------------------------------------- #
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(FIELDNAMES))
        writer.writeheader()
        writer.writerows(report.rows)
    print(f"\nwrote {args.out} ({len(report.rows)} rows)")
    print(f"\n{PROVENANCE_BANNER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
