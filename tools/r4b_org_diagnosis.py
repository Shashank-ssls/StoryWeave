"""R4b diagnosis: why does the floor miss common-noun-headed Organizations?

    .\\dev.ps1
    python tools/r4b_org_diagnosis.py

Reads the R3 database and the corpus text ONLY. The gold annotation is never opened:
the whole point of R4b is to fix the CLASS of miss, and a diagnosis that starts from the
answer key cannot tell the difference between a class and an instance.

It answers three questions in order, which between them localise the fault to exactly
one stage:

1. Does the corpus contain group-noun-headed phrases at all, and how many?
2. Did GLiNER produce a MENTION for them? (If not, the fault is the label prompt or the
   threshold.)
3. If a mention exists, did it become a NODE of the right type? (If not, the fault is
   clustering, significance, or the four-type write check.)
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.repository import Repository  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r3.db"
SLUG = "the-ninth-house"

#: Group / collective nouns, from general English (see GROUP_NOUNS in
#: storyweave/nlp/orgs.py for the shipped list and its provenance). This diagnostic uses
#: a deliberately WIDE net -- it is looking for the class, not proposing the fix.
GROUP_NOUNS = (
    "watch", "guard", "order", "council", "guild", "company", "choir", "court",
    "band", "crew", "host", "legion", "assembly", "circle", "chapter", "brotherhood",
    "sisterhood", "conclave", "senate", "tribunal", "academy", "school", "temple",
    "household", "ring", "concord", "regiment", "garrison", "militia", "union",
    "league", "alliance", "cabal", "coven", "clan", "tribe", "corps", "staff",
    "ministry", "bureau", "office", "chancery", "synod", "chapterhouse",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--slug", default=SLUG)
    args = ap.parse_args(argv)

    repo = Repository(args.db)
    work = repo.get_work_by_slug(args.slug)
    assert work is not None and work.id is not None
    chapters = {c.ordinal: c.clean_text for c in repo.list_chapters(work.id)}
    mentions = repo.list_mentions(work.id)
    nodes = {n.id: n for n in repo.list_nodes(work.id) if n.id is not None}

    group_alt = "|".join(GROUP_NOUNS)
    # "the Salt Quarter watch", "the Iron Order", "the watch" -- a group noun with an
    # optional capitalised modifier in front of it.
    phrase = re.compile(
        rf"\b(?:the\s+)?((?:[A-Z][\w'-]+\s+){{0,3}}(?:{group_alt}))\b"
    )

    print("=" * 78)
    print("R4b DIAGNOSIS - common-noun-headed Organizations")
    print("=" * 78)

    # --- 1. the corpus ----------------------------------------------------- #
    corpus_hits: Counter[str] = Counter()
    modified_hits: Counter[str] = Counter()
    for text in chapters.values():
        for m in phrase.finditer(text):
            surface = m.group(1).strip()
            corpus_hits[surface] += 1
            if re.match(r"^[A-Z]", surface) and " " in surface:
                modified_hits[surface] += 1

    print(f"\n1. CORPUS: {sum(corpus_hits.values())} group-noun phrases, "
          f"{len(corpus_hits)} distinct")
    print(f"   of those, MODIFIED by a capitalised word "
          f"(the shape a proper organization takes): "
          f"{sum(modified_hits.values())} occurrences, {len(modified_hits)} distinct\n")
    for surface, n in modified_hits.most_common():
        print(f"     {n:3}  {surface!r}")

    # --- 2. did GLiNER see them? ------------------------------------------- #
    mention_surfaces = {m.surface.lower(): m for m in mentions}
    print("\n2. MENTIONS: did the GLiNER floor emit a mention for each?\n")
    no_mention: list[str] = []
    has_mention: list[tuple[str, str, bool]] = []
    for surface in sorted(modified_hits):
        hit = mention_surfaces.get(surface.lower())
        if hit is None:
            no_mention.append(surface)
        else:
            has_mention.append((surface, hit.type.value, hit.node_id is not None))
    print(f"   no mention at all : {len(no_mention)}")
    for s in no_mention:
        print(f"     MISSED  {s!r}")
    print(f"   mention exists    : {len(has_mention)}")
    for s, t, clustered in has_mention:
        print(f"     FOUND   {s!r} as {t}, clustered={clustered}")

    # --- 3. what the graph ended up with ----------------------------------- #
    orgs = sorted(n.name for n in nodes.values() if n.type.value == "Organization")
    print(f"\n3. NODES: {len(orgs)} Organization nodes in the R3 graph\n")
    for name in orgs:
        print(f"     {name!r}")

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    if no_mention and not has_mention:
        print(
            "The fault is UPSTREAM of clustering: GLiNER emitted no mention at all for\n"
            "these phrases, so no significance rule, merge rule or four-type write check\n"
            "ever saw them. That points at the LABEL PROMPT (or the threshold), not at\n"
            "the graph-building rules."
        )
    elif has_mention:
        print(
            "At least one phrase DID produce a mention, so the fault is downstream:\n"
            "clustering, significance, or the four-type write check. See the flags above."
        )
    repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
