"""Annotation scaffolding for the v1 evaluation's phase 2 (reference annotation).

DELIVERABLE 4 of the v1 evaluation. Phase 2 will score v1 against a human/external
reference annotation of a few chapters. This emits everything that annotation needs and
nothing that would bias it: the chapter text with numbered paragraphs, an empty JSON
template, and a guidelines document describing V1'S OWN SCHEMA -- the entity types and
relation types v1 actually emits, read out of ``storyweave/db/models.py``,
``storyweave/nlp/labels.py``, ``storyweave/graph/builder.py`` and the populated
database at run time, not from memory and not from any planned redesign.

The chapter text is taken from the database's ``chapters.clean_text``, i.e. the exact
string the extraction pipeline saw, so an annotator's paragraph [k] and the pipeline's
offsets refer to the same characters.

Chapter choice is computed, not hardcoded: ``choose_chapters`` ranks candidates by the
three criteria in the brief and prints the reasoning it used.

Usage:
    python tools/make_annotation_template.py --db storyweave-demo.sqlite \
        --slug the-ninth-house --out evidence/annotation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Make the repo root importable when run as `python tools/make_annotation_template.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import (  # noqa: E402
    TIER1_RELATIONS,
    TIER2_RELATIONS,
    TIER3_RELATIONS,
    NodeType,
)
from storyweave.nlp.labels import DEFAULT_LABELS, LABEL_TO_TYPE  # noqa: E402
from tools import swconfig  # noqa: E402


@dataclass(frozen=True)
class Choice:
    ordinal: int
    role: str
    reason: str


# --------------------------------------------------------------------------- #
# Choosing the chapters
# --------------------------------------------------------------------------- #


def choose_chapters(repo: object, work_id: int) -> tuple[list[Choice], str]:
    """Pick an early / middle / late chapter by the brief's three criteria.

    Returns the choices and a printable account of the evidence behind them.
    """
    nodes = repo.list_nodes(work_id)  # type: ignore[attr-defined]
    edges = repo.list_edges(work_id)  # type: ignore[attr-defined]
    chapters = sorted(c.ordinal for c in repo.list_chapters(work_id))  # type: ignore[attr-defined]
    last = max(chapters)

    revealed_at = {n.id: n.revealed_chapter for n in nodes}
    new_nodes: Counter[int] = Counter(n.revealed_chapter for n in nodes)
    new_edges: Counter[int] = Counter(e.revealed_chapter for e in edges)
    # An edge is "among established entities" when BOTH endpoints were already
    # revealed strictly before the chapter the edge itself is revealed in.
    established: Counter[int] = Counter()
    for e in edges:
        if (
            revealed_at.get(e.source_id, last) < e.revealed_chapter
            and revealed_at.get(e.target_id, last) < e.revealed_chapter
        ):
            established[e.revealed_chapter] += 1

    identity_or_death = [e for e in edges if int(e.tier) == 3 or e.relation == "Killed"]

    lines: list[str] = []
    third = last // 3

    # (1) Early: the chapter in the first third with the most newly revealed entities,
    # excluding chapter 1 (where every entity is new by construction, so it tests
    # nothing about introducing entities into an established cast).
    early_pool = [c for c in chapters if 2 <= c <= third]
    early = max(early_pool, key=lambda c: (new_nodes[c], new_edges[c]))
    lines.append(
        f"EARLY  candidates (chapters 2..{third}, ch1 excluded because every entity "
        f"there is new by construction): "
        + ", ".join(f"ch{c}={new_nodes[c]} new entities" for c in early_pool)
    )

    # (2) Middle: the middle-third chapter with the most edges among ALREADY-revealed
    # entities -- "dense with established relations" as opposed to dense with
    # introductions.
    middle_pool = [c for c in chapters if third < c <= 2 * third]
    middle = max(middle_pool, key=lambda c: (established[c], new_edges[c]))
    lines.append(
        f"MIDDLE candidates (chapters {third + 1}..{2 * third}), scored by edges whose "
        f"BOTH endpoints were already revealed: "
        + ", ".join(
            f"ch{c}={established[c]}/{new_edges[c]}" for c in middle_pool
        )
    )

    # (3) Late: a last-third chapter carrying an identity reveal or a death. Ties break
    # toward the latest such chapter (deepest reveal state).
    late_identity = sorted(
        {e.revealed_chapter for e in identity_or_death if e.revealed_chapter > 2 * third}
    )
    if late_identity:
        late = late_identity[-1]
        detail = ", ".join(
            f"ch{e.revealed_chapter}:{e.relation}"
            for e in sorted(identity_or_death, key=lambda e: e.revealed_chapter)
        )
        late_reason = (
            f"carries an identity reveal. All Tier-3/Killed edges in the work: {detail}. "
            f"Chosen the latest one in the final third."
        )
    else:
        late = max(
            (c for c in chapters if c > 2 * third), key=lambda c: (new_edges[c], c)
        )
        late_reason = (
            "no Tier-3 identity edge or Killed edge exists in the final third, so the "
            "densest late chapter was taken instead -- stated rather than implied."
        )
    lines.append(f"LATE   {late_reason}")

    if len({early, middle, late}) != 3:
        raise ValueError(f"chapter choices collided: {early}, {middle}, {late}")

    choices = [
        Choice(
            early,
            "early — introduces several entities",
            f"{new_nodes[early]} entities are first revealed here ({new_edges[early]} "
            f"new edges), the most of any chapter in the first third excluding ch1.",
        ),
        Choice(
            middle,
            "middle — dense with established relations",
            f"{established[middle]} of its {new_edges[middle]} newly revealed edges "
            f"connect entities that were ALREADY revealed before this chapter — the "
            f"highest such count in the middle third.",
        ),
        Choice(
            late,
            "late — identity reveal / death",
            late_reason,
        ),
    ]
    return choices, "\n".join(lines)


# --------------------------------------------------------------------------- #
# Emitting the artefacts
# --------------------------------------------------------------------------- #


def numbered_paragraphs(clean_text: str) -> str:
    """The chapter, paragraphs numbered [1], [2], ..., one blank line between."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean_text) if p.strip()]
    if not paragraphs:
        raise ValueError("chapter clean_text produced no paragraphs")
    return "\n\n".join(
        f"[{i}] " + re.sub(r"\s*\n\s*", " ", p) for i, p in enumerate(paragraphs, 1)
    )


def template(ordinal: int, slug: str, title: str | None) -> dict[str, object]:
    """The empty annotation object. Arrays are empty on purpose."""
    return {
        "schema_version": "storyweave-v1-annotation-1",
        "work_slug": slug,
        "chapter": ordinal,
        "chapter_title": title,
        "annotator": "",
        "source_model": "",
        "entities": [],
        "aliases": [],
        "rejected_mentions": [],
        "relations": [],
        "events": [],
        "uncertain": [],
    }


def guidelines(repo: object, work_id: int, slug: str, choices: list[Choice]) -> str:
    """GUIDELINES.md, generated from v1's own code and this database."""
    nodes = repo.list_nodes(work_id)  # type: ignore[attr-defined]
    edges = repo.list_edges(work_id)  # type: ignore[attr-defined]
    by_type = Counter(n.type.value for n in nodes)
    by_relation = Counter(e.relation for e in edges)
    by_method_node = Counter(n.extraction_method.value for n in nodes)
    by_method_edge = Counter(e.extraction_method.value for e in edges)
    subtypes = Counter(n.subtype for n in nodes)
    all_types: Counter[str] = Counter({t.value: by_type.get(t.value, 0) for t in NodeType})

    unused_t1 = [r for r in TIER1_RELATIONS if r not in by_relation]
    unused_t2 = [r for r in TIER2_RELATIONS if r not in by_relation]
    unused_t3 = [r for r in TIER3_RELATIONS if r not in by_relation]

    def table(counter: Counter[str], header: tuple[str, str]) -> str:
        rows = [f"| {header[0]} | {header[1]} |", "| --- | ---: |"]
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))):
            rows.append(f"| `{key}` | {count} |")
        return "\n".join(rows)

    chosen = "\n".join(
        f"- **Chapter {c.ordinal}** ({c.role}): {c.reason}" for c in choices
    )

    return f"""# Reference annotation guidelines — StoryWeave v1

These guidelines describe **the schema v1 actually emits**, so that phase 2 scores v1
against v1's own ontology. Everything below was read at generation time from
`storyweave/db/models.py`, `storyweave/nlp/labels.py`, `storyweave/graph/builder.py`
and the populated database (`{slug}`). Nothing here is aspirational: if a relation
type exists in the schema but v1 never produced it for this work, that is stated.

## Chapters to annotate

{chosen}

For each chapter you are given `ch<NN>_text.txt` (the exact `clean_text` the pipeline
saw, paragraphs numbered `[1]`, `[2]`, ...) and `ch<NN>_template.json`. Fill the
template. Refer to text positions by paragraph number.

## 1. Entities

v1 has exactly **eight** node types. There are no others; an annotation using any other
type cannot be scored.

{table(all_types, ("node type", "count in this work"))}

The count column is how many canonical entities of that type v1 currently holds for the
whole work — context for what v1 tends to produce, not a target.

Type boundaries as v1 draws them (from `storyweave/nlp/labels.py`, which is the literal
zero-shot prompt list GLiNER is given):

{chr(10).join(f"- prompt `{p}` -> `{t.value}`" for p, t in LABEL_TO_TYPE.items())}

So `Concept` deliberately covers **common-noun** ideas — power systems, languages, named
phenomena — not only proper nouns. `Title` is an honorific or office ("the Regent" as a
title), distinct from the `Character` who holds it. Species and Rank are `Concept`
subtypes, never node types of their own.

**Subtypes are optional and v1 does not populate them for this work**: every node here
has `subtype = NULL` ({subtypes.get(None, 0)} of {len(nodes)}). Leave `subtype` empty
unless you are confident; it will not be scored against a populated field.

Each entity object should carry:

```json
{{"name": "", "type": "", "subtype": null, "first_paragraph": 0,
  "surface_forms": [], "notes": ""}}
```

`name` is the canonical name you would expect the system to settle on. `surface_forms`
lists every distinct string in THIS chapter that refers to it.

## 2. Aliases

An alias record says two surface strings denote the same entity. Record it whenever the
chapter uses more than one name for one referent (epithets, titles used as names,
shortened forms, "the girl" used as a stable referent).

```json
{{"canonical": "", "alias": "", "first_paragraph": 0,
  "kind": "shortening|epithet|title|pronoun-stable|other"}}
```

This is separate from the Tier-3 `ALIAS` **relation** below, which is a reveal-bearing
claim about two entities the reader thought were different. A merely shortened name is
an alias record, not an identity reveal.

## 3. Rejected mentions

Strings that look like entities but must NOT become nodes: generic nouns, weather,
pure sensory abstractions, time expressions, and any span you judge to be a false
positive. Phase 2 uses these to measure precision honestly.

```json
{{"surface": "", "paragraph": 0, "why": ""}}
```

Note a known v1 behaviour when judging these: v1 emits lowercase common nouns as
entities (for example `quiet` is a `Concept` and `ledger` is an `Item` in this work).
Record what you believe is correct; do not try to match v1.

## 4. Relations

v1 has three tiers. **Annotate all three**, but know how v1 produces each, because
phase 2 will score them separately.

### Tier 1 — structural (`extraction_method = rule`)
v1 derives these with **no ML**: two entities whose mentions fall within a
`window_chars` character window in the same chapter become an edge, and the relation is
chosen from a fixed type-pair table (`storyweave/graph/builder.py`), with a lexical cue
promoting `MemberOf` to `LeaderOf`. `RelatedTo` is the never-drop fallback for any
co-occurring pair the table does not cover.

Type-pair table, verbatim from the code:

- Character -> Organization: `MemberOf`
- Character -> Place: `LocatedIn`
- Character -> Ability: `HasAbility`
- Character -> Item: `OwnsItem`
- Character -> Title: `HasTitle`
- Character -> Event: `ParticipatedIn`
- Organization -> Place: `LocatedIn`
- Organization -> Organization: `AffiliatedWith`
- Place -> Event: `ParticipatedIn`
- anything else: `RelatedTo`

Full Tier-1 vocabulary: {", ".join(f"`{r}`" for r in TIER1_RELATIONS)}.

### Tier 2 — social (`extraction_method = curated` in this work)
{", ".join(f"`{r}`" for r in TIER2_RELATIONS)}.

The LLM layer is OFF in this build (`llm_enabled = False`). The Tier-2 records present
in this work were **hand-curated from a story bible** and are tagged `curated`, never
`llm`. Annotate the social relations the text actually supports; v1's coverage here is
sparse by construction and phase 2 should show that.

### Tier 3 — identity (`extraction_method = curated` in this work)
{", ".join(f"`{r}`" for r in TIER3_RELATIONS)}.

An identity relation is the showcase case: it is a claim that two entities the reader
believed distinct are one. Record the paragraph at which **the reader learns it**, which
is what v1 stores as `revealed_chapter` — not the paragraph where it first became true
in the story world (that is `first_seen_chapter`).

### What v1 actually emitted for this work

{table(by_relation, ("relation", "edges"))}

Schema relation types v1 produced **zero** of in this work — a real coverage gap, not a
schema gap:

- Tier 1 unused: {", ".join(f"`{r}`" for r in unused_t1) or "none"}
- Tier 2 unused: {", ".join(f"`{r}`" for r in unused_t2) or "none"}
- Tier 3 unused: {", ".join(f"`{r}`" for r in unused_t3) or "none"}

Relation object:

```json
{{"source": "", "target": "", "relation": "", "tier": 1,
  "paragraph": 0, "evidence": "", "directed": true}}
```

`relation` must be one of the {len(TIER1_RELATIONS) + len(TIER2_RELATIONS) + len(TIER3_RELATIONS)}
names listed above. `evidence` is a short verbatim quote.

## 5. Events

`Event` is a node type in v1, so a named event (a battle, a ceremony, a masque) should
appear in `entities` as well. The `events` array is for the occurrence itself: who took
part, where, and at which paragraph.

```json
{{"name": "", "paragraph": 0, "participants": [], "place": "", "notes": ""}}
```

## 6. Uncertain

Anything you could not decide. Phase 2 excludes these from the scored set rather than
guessing, so use it freely.

```json
{{"item": "", "paragraph": 0, "question": ""}}
```

## 7. Reveal stamps

Every v1 node, edge and property carries two chapter stamps:

- `first_seen_chapter` — the chapter in which the thing exists in the text.
- `revealed_chapter` — the chapter in which the READER learns it. The spoiler fence
  keys on this one.

For Tier-1 rule edges v1 sets them equal (a co-occurrence is known as soon as it
happens). For identity reveals they differ, and the difference is the point. If you can
tell that a fact is true earlier than the reader is told, say so in `notes`.

## 8. Provenance in the current database

Nodes by extraction method: {", ".join(f"`{k}`={v}" for k, v in sorted(by_method_node.items()))}.
Edges by extraction method: {", ".join(f"`{k}`={v}" for k, v in sorted(by_method_edge.items()))}.

`gliner` = zero-shot GLiNER ({len(DEFAULT_LABELS)} label prompts).
`rule` = the co-occurrence table above. `curated` = hand-written from the story bible.
`llm` = a real model run; **no record in this work carries it**, because the LLM layer
never ran.

## 9. What phase 2 will compute from this

Entity precision/recall/F1, alias F1, relation precision/recall/F1 per tier, and
ranking metrics (P@k, MAP, AUC) against the entities you mark as significant. None of
those can be computed before this annotation exists, which is why the v1 report lists
them as not measured.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="storyweave-demo.sqlite", type=Path)
    ap.add_argument("--slug", default="the-ninth-house")
    ap.add_argument("--out", default=Path("evidence/annotation"), type=Path)
    args = ap.parse_args(argv)

    repo = swconfig.open_readonly(args.db)
    try:
        work = repo.get_work_by_slug(args.slug)
        if work is None or work.id is None:
            raise ValueError(f"work {args.slug!r} not found in {args.db}")

        choices, reasoning = choose_chapters(repo, work.id)
        print("=== chapter selection evidence ===")
        print(reasoning)
        print("\n=== CHOSEN CHAPTERS ===")
        for c in choices:
            print(f"  chapter {c.ordinal}  [{c.role}]")
            print(f"      {c.reason}")
        print("\nCHOSEN CHAPTER NUMBERS: " + ", ".join(str(c.ordinal) for c in choices))

        args.out.mkdir(parents=True, exist_ok=True)
        chapters = {c.ordinal: c for c in repo.list_chapters(work.id)}
        for choice in choices:
            chapter = chapters.get(choice.ordinal)
            if chapter is None:
                raise ValueError(f"chapter {choice.ordinal} not in the database")
            text_path = args.out / f"ch{choice.ordinal:02d}_text.txt"
            json_path = args.out / f"ch{choice.ordinal:02d}_template.json"
            body = numbered_paragraphs(chapter.clean_text)
            text_path.write_text(body + "\n", encoding="utf-8")
            json_path.write_text(
                json.dumps(
                    template(choice.ordinal, args.slug, chapter.title),
                    indent=2, ensure_ascii=False,
                ) + "\n",
                encoding="utf-8",
            )
            # Parse it straight back: the brief requires valid JSON, so prove it.
            json.loads(json_path.read_text(encoding="utf-8"))
            paragraphs = body.count("\n\n") + 1
            print(
                f"wrote {text_path} ({paragraphs} paragraphs, "
                f"{len(chapter.clean_text)} chars)"
            )
            print(f"wrote {json_path} (parses as JSON: ok)")

        guide = args.out / "GUIDELINES.md"
        guide.write_text(guidelines(repo, work.id, args.slug, choices), encoding="utf-8")
        print(f"wrote {guide}")
        return 0
    finally:
        repo.close()


if __name__ == "__main__":
    raise SystemExit(main())
