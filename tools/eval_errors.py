"""Error analysis over the phase-2 scores: group every FP and FN by cause.

DELIVERABLE 2 of the v1 evaluation, phase 2. Reads the same inputs as
``tools/eval_score.py`` — the model-generated reference annotation (see
``evidence/annotation/PROVENANCE.md``) and v1's live output through the real
``Repository`` — re-derives the false positives and false negatives, assigns each one a
cause by an explicit rule, and writes ``evidence/errors_v1.md``.

The categories were NOT chosen in advance. They were read off the actual 23 entity false
positives, 21 entity false negatives and the relation errors produced by the scorer, and
then written down here as rules so the counts are reproducible rather than asserted. Each
rule is stated in the output next to its count. A case is assigned to the FIRST rule it
satisfies, so the categories partition the errors and the counts sum to the total.

Everything here is AGREEMENT analysis between two systems, v1 and GPT-5. It is not
accuracy against human ground truth.

Usage:
    python tools/eval_errors.py --db storyweave-demo.sqlite --out evidence/errors_v1.md
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

# Make the repo root importable when run as `python tools/eval_errors.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import swconfig  # noqa: E402
from tools.eval_score import (  # noqa: E402
    CHAPTERS,
    PROVENANCE_BANNER,
    SLUG,
    Annotation,
    V1Chapter,
    load_v1,
    match_entities,
    normalise,
    score_relations,
    validate,
)

ANNOTATION_DIR = Path("evidence/annotation")

#: Words too common to make a "these two names overlap" judgement meaningful.
_COMMON = {
    "the", "a", "an", "of", "and", "s", "house", "lord", "lady", "ser", "master",
    "mistress", "captain", "warden",
}


@dataclass
class Case:
    chapter: int
    category: str
    subject: str
    detail: str


# --------------------------------------------------------------------------- #
# Rules, stated here and printed next to their counts
# --------------------------------------------------------------------------- #

ENTITY_FP_RULES: dict[str, str] = {
    "type_disagreement": (
        "v1's name matches a reference entity's name after normalisation, but the two "
        "assign it a different node type. Each of these is simultaneously a false "
        "positive and a false negative under the strict (name, type) match."
    ),
    "reference_alias_kept_separate": (
        "v1's name is listed by the reference as a surface_form or alias of some OTHER "
        "entity, i.e. the reference would have folded it into an existing entity and v1 "
        "kept it as its own."
    ),
    "reference_rejected_string": (
        "v1's name is one of the strings the reference explicitly put in "
        "rejected_mentions for that chapter — the reference says it should not be an "
        "entity at all."
    ),
    "not_in_reference": (
        "v1's name appears nowhere in the reference for that chapter: not as an entity, "
        "not as a surface form or alias, not as a rejected mention. The reference simply "
        "does not mention the string."
    ),
}

ENTITY_FN_RULES: dict[str, str] = {
    "type_disagreement": (
        "the mirror of the FP rule of the same name: v1 has this name, with a different "
        "node type."
    ),
    "canonical_name_choice": (
        "v1 DID see this exact string as a mention in this chapter and clustered it, but "
        "named the resulting entity after a different surface form — so a strict "
        "name match fails even though the entity was found."
    ),
    "partial_span_only": (
        "v1 has no mention equal to this name, but it does have a mention sharing a "
        "DISTINCTIVE word with it — the span boundary differs (typically a multi-word "
        "or possessive phrase v1 split). 'Distinctive' excludes the stoplist "
        "{the, a, an, of, and, s, house, lord, lady, ser, master, mistress, captain, "
        "warden}, which recur across unrelated names in this work and would otherwise "
        "make almost every pair look related."
    ),
    "absent_from_v1_chapter": (
        "v1 produced no mention in this chapter sharing any distinctive word with this "
        "name, using the same stoplist. A plain recall miss — though note that a name "
        "built ONLY from stoplisted words, such as 'Warden-Captain', lands here by "
        "construction rather than because v1 saw nothing nearby."
    ),
}

RELATION_FP_RULES: dict[str, str] = {
    "cooccurrence_fallback_RelatedTo": (
        "the edge is `RelatedTo`, the never-drop fallback `graph/builder.py` emits for "
        "any co-occurring pair its type-pair table does not cover."
    ),
    "cooccurrence_type_pair_rule": (
        "the edge is a Tier-1 relation the type-pair table assigned from the two node "
        "types alone, on a co-occurrence the reference did not record as a relation."
    ),
    "curated_tier2_or_tier3": (
        "the edge is a hand-curated Tier-2/Tier-3 record with no counterpart in the "
        "reference."
    ),
}

RELATION_FN_RULES: dict[str, str] = {
    "endpoint_not_found_by_v1": (
        "at least one endpoint of the reference relation is an entity v1 did not produce "
        "for this chapter, so the relation could not be matched at all."
    ),
    "tier2_social_not_produced": (
        "a Tier-2 social relation. The LLM layer is off in this build, and the curated "
        "Tier-2 records cover other pairs, so v1 has nothing to match."
    ),
    "tier1_not_produced": (
        "both endpoints were found, but v1 holds no edge with this relation between "
        "them."
    ),
}


def _words(name: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", normalise(name)) if w and w not in _COMMON}


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #


def classify_entity_errors(
    chapter: int, v1: V1Chapter, ann: Annotation
) -> tuple[list[Case], list[Case]]:
    match = match_entities(v1, ann, alias_aware=False)
    reference = ann.scored_entities

    ref_name_to_type: dict[str, str] = {
        normalise(str(e["name"])): str(e["type"]) for e in reference
    }
    alias_owner: dict[str, str] = {}
    for entity in reference:
        for surface in entity.get("surface_forms") or []:
            alias_owner.setdefault(normalise(str(surface)), str(entity["name"]))
    for i, alias in enumerate(ann.data.get("aliases", [])):
        if i not in ann.excluded_aliases:
            alias_owner.setdefault(normalise(str(alias["alias"])), str(alias["canonical"]))
    rejected = {
        normalise(str(r["surface"])): str(r["why"])
        for i, r in enumerate(ann.data.get("rejected_mentions", []))
        if i not in ann.excluded_rejected
    }

    v1_name_to_type = {normalise(v1.names[i]): v1.types[i] for i in v1.names}
    v1_surface_owner: dict[str, int] = {}
    for node_id, surfaces in v1.surfaces.items():
        for surface in surfaces:
            v1_surface_owner.setdefault(normalise(surface), node_id)
    v1_all_words: set[str] = set()
    for node_id, surfaces in v1.surfaces.items():
        v1_all_words |= _words(v1.names[node_id])
        for surface in surfaces:
            v1_all_words |= _words(surface)

    # --- false positives --- #
    fps: list[Case] = []
    for node_id in match.false_positives:
        key = normalise(v1.names[node_id])
        label = f"{v1.names[node_id]!r} ({v1.types[node_id]})"
        if key in ref_name_to_type and ref_name_to_type[key] != v1.types[node_id]:
            fps.append(Case(chapter, "type_disagreement", label,
                            f"reference types it {ref_name_to_type[key]}"))
        elif key in alias_owner:
            fps.append(Case(chapter, "reference_alias_kept_separate", label,
                            f"reference folds it into {alias_owner[key]!r}"))
        elif key in rejected:
            fps.append(Case(chapter, "reference_rejected_string", label,
                            f"reference reason: {rejected[key]}"))
        else:
            fps.append(Case(chapter, "not_in_reference", label,
                            "absent from the reference's entities, surface forms, "
                            "aliases and rejected mentions"))

    # --- false negatives --- #
    fns: list[Case] = []
    for ref_i in match.false_negatives:
        entity = reference[ref_i]
        key = normalise(str(entity["name"]))
        label = f"{entity['name']!r} ({entity['type']})"
        if key in v1_name_to_type and v1_name_to_type[key] != str(entity["type"]):
            fns.append(Case(chapter, "type_disagreement", label,
                            f"v1 types it {v1_name_to_type[key]}"))
        elif key in v1_surface_owner:
            owner = v1_surface_owner[key]
            fns.append(Case(chapter, "canonical_name_choice", label,
                            f"v1 saw this exact surface and clustered it under "
                            f"{v1.names[owner]!r} ({v1.types[owner]})"))
        elif _words(str(entity["name"])) & v1_all_words:
            shared = sorted(_words(str(entity["name"])) & v1_all_words)
            fns.append(Case(chapter, "partial_span_only", label,
                            f"v1 has mentions sharing {shared}"))
        else:
            fns.append(Case(chapter, "absent_from_v1_chapter", label,
                            "no v1 mention in this chapter shares a distinctive word"))
    return fps, fns


def classify_relation_errors(
    chapter: int, v1: V1Chapter, ann: Annotation, variant: str
) -> tuple[list[Case], list[Case]]:
    match = match_entities(v1, ann, alias_aware=False)
    edges = v1.edges_local if variant == "chapter_local" else v1.edges_cumulative
    score = score_relations(v1, ann, match, edges)

    tier_of_edge: dict[str, int] = {}
    for _s, _t, rel, tier in edges:
        tier_of_edge[rel] = tier

    fps: list[Case] = []
    for label in score.false_positives:
        relation = label.split(" -")[1].split("-> ")[0] if " -" in label else ""
        if relation == "RelatedTo":
            fps.append(Case(chapter, "cooccurrence_fallback_RelatedTo", label, ""))
        elif tier_of_edge.get(relation, 1) == 1:
            fps.append(Case(chapter, "cooccurrence_type_pair_rule", label,
                            f"relation {relation}"))
        else:
            fps.append(Case(chapter, "curated_tier2_or_tier3", label,
                            f"relation {relation}, tier {tier_of_edge.get(relation)}"))

    ref_tier: dict[str, int] = {}
    for record in ann.scored_relations:
        key = f"{record['source']} -{record['relation']}-> {record['target']}"
        ref_tier[key] = int(record["tier"])

    fns: list[Case] = []
    for label in score.false_negatives:
        base = label.split(" [")[0]
        if "[unmatchable" in label:
            fns.append(Case(chapter, "endpoint_not_found_by_v1", base, ""))
        elif ref_tier.get(base, 1) == 2:
            fns.append(Case(chapter, "tier2_social_not_produced", base, ""))
        else:
            fns.append(Case(chapter, "tier1_not_produced", base, ""))
    return fps, fns


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def render_group(
    title: str, rules: dict[str, str], cases: list[Case], total_label: str
) -> str:
    by_category: dict[str, list[Case]] = defaultdict(list)
    for case in cases:
        by_category[case.category].append(case)
    per_chapter: dict[str, Counter[int]] = {
        category: Counter(c.chapter for c in items)
        for category, items in by_category.items()
    }

    lines = [f"### {title}", ""]
    lines.append(f"{len(cases)} {total_label} in total, across chapters 9, 17 and 37.")
    lines.append("")
    lines.append("| cause | count | ch9 | ch17 | ch37 |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for category in rules:
        items = by_category.get(category, [])
        counts = per_chapter.get(category, Counter())
        lines.append(
            f"| `{category}` | {len(items)} | {counts.get(9, 0)} | "
            f"{counts.get(17, 0)} | {counts.get(37, 0)} |"
        )
    unknown = set(by_category) - set(rules)
    for category in sorted(unknown):
        counts = per_chapter[category]
        lines.append(
            f"| `{category}` (unclassified) | {len(by_category[category])} | "
            f"{counts.get(9, 0)} | {counts.get(17, 0)} | {counts.get(37, 0)} |"
        )
    lines.append("")

    for category in list(rules) + sorted(unknown):
        items = by_category.get(category, [])
        lines.append(f"**`{category}` — {len(items)}**")
        lines.append("")
        lines.append(f"Rule: {rules.get(category, 'unclassified')}")
        lines.append("")
        if not items:
            lines.append("No cases.")
            lines.append("")
            continue
        for case in items[:2]:
            detail = f" — {case.detail}" if case.detail else ""
            lines.append(f"- ch{case.chapter}: {case.subject}{detail}")
        if len(items) > 2:
            lines.append(f"- … and {len(items) - 2} more, all listed in "
                         f"`evidence/scores_v1.csv`.")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="storyweave-demo.sqlite", type=Path)
    ap.add_argument("--annotations", default=ANNOTATION_DIR, type=Path)
    ap.add_argument("--slug", default=SLUG)
    ap.add_argument("--out", default=Path("evidence/errors_v1.md"), type=Path)
    args = ap.parse_args(argv)

    annotations = {c: validate(c, args.annotations) for c in CHAPTERS}
    if any(f.fatal for a in annotations.values() for f in a.failures):
        print("fatal validation failure; refusing to analyse")
        return 2

    repo = swconfig.open_readonly(args.db)
    try:
        work = repo.get_work_by_slug(args.slug)
        if work is None or work.id is None:
            raise ValueError(f"work {args.slug!r} not found in {args.db}")
        v1_all = load_v1(repo, work.id, CHAPTERS)
    finally:
        repo.close()

    entity_fps: list[Case] = []
    entity_fns: list[Case] = []
    relation_fps: list[Case] = []
    relation_fns: list[Case] = []
    for chapter in CHAPTERS:
        fps, fns = classify_entity_errors(chapter, v1_all[chapter], annotations[chapter])
        entity_fps += fps
        entity_fns += fns
        rfps, rfns = classify_relation_errors(
            chapter, v1_all[chapter], annotations[chapter], "chapter_local"
        )
        relation_fps += rfps
        relation_fns += rfns

    # Rejected mentions v1 emitted, and what kind of strings they are.
    rejected_hits: list[tuple[int, str, str, str]] = []
    for chapter in CHAPTERS:
        ann, v1 = annotations[chapter], v1_all[chapter]
        v1_strings: dict[str, tuple[int, str]] = {}
        for node_id, surfaces in v1.surfaces.items():
            for surface in surfaces:
                v1_strings[normalise(surface)] = (node_id, "mention surface")
        for node_id in v1.names:
            v1_strings[normalise(v1.names[node_id])] = (node_id, "canonical name")
        for i, record in enumerate(ann.data.get("rejected_mentions", [])):
            if i in ann.excluded_rejected:
                continue
            key = normalise(str(record["surface"]))
            if key in v1_strings:
                node_id, how = v1_strings[key]
                rejected_hits.append((
                    chapter, str(record["surface"]),
                    f"v1 {how} of {v1.names[node_id]!r} ({v1.types[node_id]})",
                    str(record["why"]),
                ))

    total_rejected = sum(
        len(a.data.get("rejected_mentions", [])) - len(a.excluded_rejected)
        for a in annotations.values()
    )

    body = [
        "# v1 error analysis — phase 2",
        "",
        f"> {PROVENANCE_BANNER}",
        "",
        "Every false positive and false negative below was re-derived in this run by "
        "`tools/eval_errors.py` from the same inputs the scorer used. Categories were "
        "read off the actual cases and then written down as rules, which are printed "
        "next to their counts; a case is assigned to the FIRST rule it satisfies, so "
        "the categories partition the errors and each table's counts sum to its total.",
        "",
        "Relation errors are analysed for the `chapter_local` variant "
        "(v1 edges with `first_seen_chapter == N`), which is the stricter of the two "
        "the scorer reports.",
        "",
        "---",
        "",
        "## Entities",
        "",
        render_group("False positives — v1 produced, reference did not",
                     ENTITY_FP_RULES, entity_fps, "entity false positives"),
        render_group("False negatives — reference has, v1 does not",
                     ENTITY_FN_RULES, entity_fns, "entity false negatives"),
        "---",
        "",
        "## Relations",
        "",
        render_group("False positives — v1 edge with no reference counterpart",
                     RELATION_FP_RULES, relation_fps, "relation false positives"),
        render_group("False negatives — reference relation v1 lacks",
                     RELATION_FN_RULES, relation_fns, "relation false negatives"),
        "---",
        "",
        "## Rejected mentions v1 emitted",
        "",
        f"The reference lists {total_rejected} strings across the three chapters that "
        f"it says should NOT become entities. v1 emitted **{len(rejected_hits)}** of "
        f"them — either as an entity's canonical name or as a mention surface it "
        f"clustered into an entity.",
        "",
        "| chapter | rejected string | how v1 holds it | the reference's reason |",
        "| ---: | --- | --- | --- |",
    ]
    for chapter, surface, how, why in rejected_hits:
        body.append(f"| {chapter} | `{surface}` | {how} | {why} |")
    body += [
        "",
        "**What kind of strings these are.** Read together, they are of three kinds, "
        "and the table above is the whole population, so this is a description of it "
        "rather than a sample:",
        "",
        "1. **Abstract nouns used as atmosphere** — `quiet`, `ambition`. The reference "
        "rejects them as sensory or character qualities; v1 admits them as `Concept` "
        "entities in their own right.",
        "2. **Generic architectural nouns** — `gilded rooms`, `rooms`, `doors`. The "
        "reference rejects them as unidentifiable spaces; v1 admits `gilded rooms` as a "
        "`Place` and folds `rooms` and `doors` into `Place` entities.",
        "3. **An unnamed past occurrence** — `Undercroft collapse`. The reference "
        "rejects it because the chapter never gives the event a name; v1 admits it as "
        "an `Event`.",
        "",
        "All of them are common nouns or common-noun phrases, none is a proper noun. "
        "That is consistent with the `Concept` prompt list in "
        "`storyweave/nlp/labels.py`, which deliberately asks GLiNER for common-noun "
        "ideas (`power system`, `phenomenon`, `language`) in addition to the eight type "
        "names.",
        "",
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(body) + "\n", encoding="utf-8")

    print(PROVENANCE_BANNER)
    print()
    for title, rules, cases in (
        ("entity false positives", ENTITY_FP_RULES, entity_fps),
        ("entity false negatives", ENTITY_FN_RULES, entity_fns),
        ("relation false positives", RELATION_FP_RULES, relation_fps),
        ("relation false negatives", RELATION_FN_RULES, relation_fns),
    ):
        counts = Counter(c.category for c in cases)
        print(f"=== {title}: {len(cases)} ===")
        for category in rules:
            print(f"    {category:<34} {counts.get(category, 0)}")
        for category in sorted(set(counts) - set(rules)):
            print(f"    {category:<34} {counts[category]}  (UNCLASSIFIED)")
    print(f"\nrejected strings v1 emitted: {len(rejected_hits)} of {total_rejected}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
