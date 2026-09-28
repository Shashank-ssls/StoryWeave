"""Title linking: attach a title to the person the text connects them to (retrofit R3).

A title is not a separate being from its holder. v1 made "the Warden" its own `Title`
node, which then collected its own edges and competed with the person in the graph; R3
turns it into an :class:`~storyweave.db.models.EntityLabel` on that person instead
(``LEGACY_TYPE_MAP[NodeType.TITLE] is BECOMES_LABEL``).

**The link is a reveal, so it is fenced.** Learning that "the Warden" is Orin Drask is
exactly the kind of fact the fence exists to gate: the label's ``revealed_chapter`` is the
chapter whose text makes the connection, and before that chapter the title must not appear
on that person in any payload. A title the text never connects to anyone is simply never
served.

**Exact apposition only — no LLM, no inference.** Two patterns, both requiring the name
and the title to sit next to each other separated by a comma:

    X, the Warden          ("Orin Drask, the Warden of the Salt Quarter, said nothing")
    the Warden, X,         ("the Warden, Orin Drask, said nothing")

The second pattern requires BOTH commas, and a title preceded by a preposition is rejected
outright. Both guards exist because the first real run over the corpus produced exactly two
links and both were wrong: "At the Chancery, Ser Robart Kell noticed ..." is a fronted
prepositional phrase, and "Aurelia Marrow, the Ninth House's last acknowledged daughter"
is a possessive, not a title called "the Ninth House's". Measured, then fixed.

That is a deliberately narrow net. Anaphora ("He was the Warden"), predication two
sentences later, and every other construction are left alone, because resolving them
needs a model and a wrong link invents an identity the book never stated. A quote is
mandatory: the matched span is stored on the label, which is also what R4's validator
reads.

Ambiguity is refused, not guessed: if the same title apposes two different people
anywhere in the work, neither link is made.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

#: A title phrase: "the" plus one or two Capitalized words. Kept tight on purpose —
#: "the Warden", "the Salt Cipher", but not a whole clause. No apostrophe in the word
#: class: it must not swallow a possessive, or "the Ninth House's last acknowledged
#: daughter" is mistaken for a title called "the Ninth House's".
_TITLE = r"the\s+[A-Z][\w-]*(?:\s+[A-Z][\w-]*)?"

#: Prepositions that make a following "the X, Name" a FRONTED PHRASE, not an apposition:
#: "At the Chancery, Ser Robart Kell noticed ..." names no title at all.
_PREPOSITIONS = frozenset(
    """at in on to from by near inside outside within through toward towards into onto
    past beyond under over above below beside behind before after across against along
    around among between during for of with without upon off out""".split()
)


@dataclass(frozen=True)
class TitleLink:
    """One title-to-person link the text states outright."""

    entity_id: int
    title: str
    chapter: int
    quote: str


@dataclass(frozen=True)
class RejectedTitleLink:
    """A candidate link that was refused, and why. Reported, never silently dropped."""

    title: str
    entity_ids: tuple[int, ...]
    reason: str


def _quote(text: str, start: int, end: int, pad: int = 40) -> str:
    a, b = max(0, start - pad), min(len(text), end + pad)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def find_title_links(
    names_by_entity: dict[int, set[str]],
    chapter_texts: dict[int, str],
) -> tuple[list[TitleLink], list[RejectedTitleLink]]:
    """Find `X, the Title` / `the Title, X` appositions across a work's chapters.

    ``names_by_entity`` maps entity id -> the surface strings that name it (canonical
    name plus its merged aliases). ``chapter_texts`` maps chapter ordinal -> clean text.

    Returns the accepted links (earliest chapter per entity+title, with its quote) and
    the refused candidates with reasons.
    """
    # (title_lower) -> entity_id -> (chapter, quote), earliest chapter kept.
    found: dict[str, dict[int, tuple[int, str]]] = defaultdict(dict)
    #: canonical casing for each title, taken from its first occurrence.
    display: dict[str, str] = {}

    for chapter in sorted(chapter_texts):
        text = chapter_texts[chapter]
        for entity_id, names in names_by_entity.items():
            for name in names:
                # A one-word lowercase "name" would match half the prose; the apposition
                # patterns need a real name to anchor on.
                if len(name) < 3 or not any(c.isupper() for c in name):
                    continue
                escaped = re.escape(name)
                for pattern, group in (
                    # "X, the Warden," / "X, the Warden of the Salt Quarter," - the
                    # title must END at an apposition boundary: a comma/full stop, or
                    # " of " introducing its domain. Without this the pattern truncates
                    # a longer noun phrase into a fake title: "Aurelia Marrow, the Ninth
                    # House's last acknowledged daughter" yields "the Ninth".
                    (rf"{escaped},\s+({_TITLE})(?![\w'])(?=\s*[,.;:]|\s+of\b)", 1),
                    # "the Warden, X," - BOTH commas are required. A pre-posed
                    # apposition is bracketed by them; without the trailing comma this
                    # matches any fronted phrase followed by a subject, which is how
                    # "At the Chancery, Ser Robart Kell noticed ..." became a "title".
                    (rf"\b({_TITLE}),\s+{escaped}\s*,", 1),
                ):
                    for match in re.finditer(pattern, text):
                        title = match.group(group).strip()
                        # Belt and braces on the same failure: a title immediately
                        # preceded by a preposition is part of that phrase, not an
                        # apposition to anyone.
                        prefix = text[max(0, match.start() - 24) : match.start()]
                        words = re.findall(r"[A-Za-z]+", prefix)
                        if (
                            match.group(0).lstrip().startswith("the")
                            and words
                            and words[-1].lower() in _PREPOSITIONS
                        ):
                            continue
                        key = title.lower()
                        display.setdefault(key, title)
                        prior = found[key].get(entity_id)
                        if prior is None or chapter < prior[0]:
                            found[key][entity_id] = (
                                chapter,
                                _quote(text, match.start(), match.end()),
                            )

    links: list[TitleLink] = []
    rejected: list[RejectedTitleLink] = []
    for key, by_entity in found.items():
        if len(by_entity) > 1:
            # The same title apposes two people. One of them is wrong and nothing here
            # can tell which, so neither is linked.
            rejected.append(
                RejectedTitleLink(
                    title=display[key],
                    entity_ids=tuple(sorted(by_entity)),
                    reason=(
                        f"ambiguous: apposed to {len(by_entity)} different entities; "
                        "linking either would invent an identity the text does not state"
                    ),
                )
            )
            continue
        entity_id, (chapter, quote) = next(iter(by_entity.items()))
        links.append(
            TitleLink(entity_id=entity_id, title=display[key], chapter=chapter, quote=quote)
        )

    links.sort(key=lambda link: (link.chapter, link.entity_id, link.title))
    rejected.sort(key=lambda r: r.title)
    return links, rejected
