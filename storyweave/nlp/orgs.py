"""Retrofit R4b: recover common-noun-headed Organizations the GLiNER floor drops.

**The measured problem** (`evidence/retrofit/R4b_RESULT.md` §1, and
`tools/r4b_org_diagnosis.py` which produced it): an organization named by a proper
modifier plus a plain English group noun -- "the Salt Quarter watch", "Cassian's guard"
-- never reaches the graph, because GLiNER prefers the PLACE nested inside it. Asked
about "the Salt Quarter watch" it returns ``'Salt Quarter' -> Place`` and stops. The
longer span is never a candidate, so no clustering, significance or write-check rule
ever sees it: the loss is upstream of all of them.

**Why this is a rule and not a better prompt.** `tools/r4b_prompt_probe.py` measured four
candidate prompt additions -- "group of people", "military unit", "institution", and all
three together -- against the shipped R3 label set on every sentence in the corpus that
contains such a phrase. **None of them recovered the class**, and the nested-Place
reading survived every one. A zero-shot model that has already committed to the inner
span does not give up that span because a new label was added to the list. So the fix is
the structure the model cannot see, applied as a rule, with the model's own output as
its anchor.

**The rule, stated so it can be argued with.** A span is proposed as an Organization
when it is a sequence of one to three capitalised modifier tokens (a possessive like
"Cassian's" counts) immediately followed by one of :data:`GROUP_NOUNS`. The capitalised
modifier is what distinguishes a named body from a generic one: "the Salt Quarter watch"
is an organization, "the watch" is a common noun, and only the first is proposed. The
rule never invents a name that is not literally in the text, and it never fires on a
bare group noun.

**Where :data:`GROUP_NOUNS` came from, since it decides what the rule can see.** It is a
list of English COLLECTIVE / ORGANISATIONAL nouns -- words that denote a body of people
rather than a place or a thing -- assembled from general English vocabulary and from the
organisational senses already present in this project's own ontology documentation
(SPEC §5.1's description of Organization as "factions, houses, orders, governments").
It was written by scanning general English, NOT by reading the corpus and NOT by reading
the annotation: no entry was added because it appeared in this book, and the list
contains many words this book never uses (see the report's coverage table). That is
deliberate -- a list fitted to the corpus would be tuning on the answer key by another
route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: English collective / organisational nouns. See the module docstring for provenance.
#: Per-work overrides live in ``storyweave.toml`` (``[extraction] group_nouns``).
GROUP_NOUNS: tuple[str, ...] = (
    # bodies of armed or official people
    "watch", "guard", "guards", "garrison", "militia", "regiment", "legion", "corps",
    "patrol", "company", "battalion", "host", "army", "navy", "fleet", "constabulary",
    # governing and deliberative bodies
    "council", "senate", "tribunal", "assembly", "court", "ministry", "bureau",
    "office", "chancery", "synod", "parliament", "cabinet", "committee", "board",
    # religious, scholarly and fraternal bodies
    "order", "choir", "temple", "academy", "school", "college", "brotherhood",
    "sisterhood", "conclave", "coven", "circle", "chapter", "congregation", "seminary",
    # kin, trade and informal bodies
    "household", "house", "clan", "tribe", "family", "guild", "union", "league",
    "alliance", "concord", "consortium", "syndicate", "cartel", "ring", "crew",
    "band", "troupe", "staff", "retinue", "entourage", "cabal", "faction", "party",
)

#: English CLOSED-CLASS function words: articles, determiners, pronouns, conjunctions,
#: subordinators, prepositions and auxiliaries. At the start of a sentence every one of
#: them is capitalised, where it looks exactly like a proper modifier and is not.
#:
#: This list was widened twice, by measurement, and both steps are recorded because they
#: are the reason to trust it. The first version excluded nothing and promoted "A ring"
#: (from "A ring of smugglers") and "The chancery". Excluding determiners fixed those
#: and left "And House" and "If House" -- sentence-initial conjunctions. The general
#: fact behind both is the same: a proper modifier is an OPEN-class word, so the guard
#: is the closed class, not a list of the specific words that went wrong.
_FUNCTION_WORDS: frozenset[str] = frozenset(
    {
        # articles and determiners
        "a", "an", "the", "this", "that", "these", "those", "no", "some", "any",
        "each", "every", "another", "both", "either", "neither", "such", "what",
        # possessives and pronouns
        "his", "her", "its", "their", "our", "your", "my", "he", "she", "it", "they",
        "we", "you", "i", "who", "whom", "whose", "which",
        # conjunctions and subordinators
        "and", "or", "but", "nor", "yet", "so", "if", "then", "than", "because",
        "although", "though", "while", "when", "where", "whether", "as", "since",
        "unless", "until", "after", "before", "once",
        # prepositions and particles
        "at", "by", "for", "from", "in", "into", "of", "off", "on", "onto", "out",
        "over", "to", "under", "up", "with", "within", "without", "upon", "beneath",
        "beside", "behind", "between", "among", "through", "against", "toward",
        "towards", "about", "above", "below", "across", "near", "past",
        # auxiliaries and common copulas
        "is", "was", "were", "are", "be", "been", "being", "had", "has", "have",
        "do", "does", "did", "will", "would", "shall", "should", "can", "could",
        "may", "might", "must", "there", "here", "not", "now", "still", "even",
    }
)

#: The function words as they appear capitalised, i.e. at the start of a sentence, which
#: is the only position where they can be mistaken for a proper modifier.
_DET_ALT = "|".join(
    sorted((d.capitalize() for d in _FUNCTION_WORDS), key=len, reverse=True)
)

#: A capitalised token that is NOT a function word, or a capitalised possessive
#: ("Cassian's"). The possessive form matters: "Cassian's guard" is as much a named
#: body as "the Salt Quarter watch".
_MODIFIER = rf"(?!(?:{_DET_ALT})\b)[A-Z][\w-]*(?:'s|s')?"


@dataclass(frozen=True)
class OrgSpan:
    """One rule-proposed Organization span, in chapter-text offsets."""

    surface: str
    char_start: int
    char_end: int


def _pattern(group_nouns: tuple[str, ...]) -> re.Pattern[str]:
    alt = "|".join(sorted((re.escape(g) for g in group_nouns), key=len, reverse=True))
    # One to three capitalised modifiers, then the group noun. The HEAD is matched
    # case-insensitively -- "the Iron Order" and "the Salt Quarter watch" are the same
    # construction and a book may capitalise either -- while the MODIFIERS stay strictly
    # capitalised, because that is the part that distinguishes a named body from a
    # generic one. The article is not captured: it is not part of the name.
    return re.compile(rf"\b((?:{_MODIFIER}\s+){{1,3}}(?i:{alt}))\b")


def find_organization_spans(
    text: str,
    existing: frozenset[tuple[int, int]] = frozenset(),
    group_nouns: tuple[str, ...] = GROUP_NOUNS,
) -> list[OrgSpan]:
    """Propose Organization spans in ``text`` that the model did not already produce.

    ``existing`` is the set of ``(start, end)`` offsets the model already emitted, at any
    type. A span the model already found is left alone -- this rule only ADDS candidates
    the model missed, so it can never overwrite or retype the model's own output. Spans
    that merely OVERLAP an existing mention (the nested Place, which is the whole
    problem) are still proposed: that overlap is the point.
    """
    out: list[OrgSpan] = []
    for match in _pattern(group_nouns).finditer(text):
        start, end = match.start(1), match.end(1)
        if (start, end) in existing:
            continue
        out.append(OrgSpan(match.group(1), start, end))
    return out
