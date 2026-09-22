"""Alias clustering: raw mentions -> canonical entities (Phase 2).

This is the conservative, *string-based* floor of coreference — it merges surface
variants of the same name, NOT semantic identities. It does two things:

1. Group mentions by a normalized surface (case-folded, article-stripped, depunct).
   The canonical type is the majority vote across the group's mentions.
2. Subset-merge: fold a shorter name into a longer same-type name when its tokens
   are a strict subset (e.g. "Veris" -> "Lady Veris", "Coil" -> "the Coil"),
   guarding against merges on purely generic tokens.

True identity links (Wren == Prince Caelum, Gray Sparrow == Lady Veris) are
deliberately NOT made here — those are Tier-3 identity edges that the reveal fence
must gate and the LLM infers in Phase 7. Pure Python: no ML, runs in the light venv.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from storyweave.db.models import Mention, NodeType

_PUNCT = "\"'“”‘’()[]{}.,;:!?—-"
_ARTICLES = ("the ", "a ", "an ")
# Tokens too generic to justify a subset merge on their own.
_GENERIC = {
    "the", "a", "an", "lord", "lady", "ser", "sir", "king", "queen",
    "house", "guild", "city", "the boy", "man", "woman",
}

# Mentions dropped OUTRIGHT before clustering, never becoming a node at all (measured
# necessity: docs/INTEGRATION.md Part B.3 found this exact noise pattern on a real
# GLiNER pass — closed-class pronouns/determiners a zero-shot NER model has no
# antecedent-linking capability to resolve, plus the handful of bare generic-object
# common nouns that dominated false positives). Standard NER post-processing, generic
# to any work, not tuned to this book's specific text (nothing here is a proper noun
# or a capitalized mid-sentence mention — those are left completely alone).
_PRONOUNS = {
    "i", "me", "my", "mine", "myself",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "we", "us", "our", "ours", "ourselves",
    "they", "them", "their", "theirs", "themselves",
    "who", "whom", "whose", "this", "that", "these", "those",
    "someone", "somebody", "something",
    "everyone", "everybody", "everything",
    "anyone", "anybody", "anything",
    "no one", "nobody", "nothing",
    "both of them", "both", "one", "ones",
}
# Bare generic-object nouns: excluded only on an EXACT normalized match (a single
# common word with no modifier/proper-noun context at all) — "the desk" is dropped,
# "Sorrel's writing desk" or "the Ashcombe Blade" is not touched.
_GENERIC_OBJECTS = {
    "desk", "door", "doorway", "table", "hall", "room", "study", "home",
    "street", "streets", "wall", "floor", "ceiling", "window", "chair",
    "bed", "lamp", "lamps", "box", "thing", "things", "stall", "stalls",
    "threshold", "location",
}


def _is_stopword(norm: str) -> bool:
    return norm in _PRONOUNS or norm in _GENERIC_OBJECTS


def normalize_surface(surface: str) -> str:
    """Case-fold, strip surrounding punctuation, drop a leading article, squeeze spaces."""
    s = re.sub(r"\s+", " ", surface.strip().strip(_PUNCT).strip())
    low = s.lower()
    for art in _ARTICLES:
        if low.startswith(art):
            low = low[len(art):]
            break
    return low.strip()


@dataclass
class _Rep:
    norm: str
    tokens: set[str]
    type: NodeType
    members: list[Mention]


@dataclass
class EntityCluster:
    name: str
    type: NodeType
    subtype: str | None
    first_seen_chapter: int
    mention_count: int
    members: list[Mention] = field(default_factory=list)

    @property
    def representative(self) -> Mention:
        """Earliest mention (chapter, then position) — used to quote evidence."""
        return min(self.members, key=lambda m: (m.chapter_ordinal, m.char_start))


def cluster_mentions(mentions: list[Mention]) -> list[EntityCluster]:
    """Cluster raw mentions into canonical entities with a first_seen_chapter."""
    by_norm: dict[str, list[Mention]] = {}
    for m in mentions:
        norm = normalize_surface(m.surface)
        if norm and not _is_stopword(norm):
            by_norm.setdefault(norm, []).append(m)

    reps: list[_Rep] = []
    for norm, members in by_norm.items():
        majority_type = Counter(m.type for m in members).most_common(1)[0][0]
        reps.append(_Rep(norm, set(norm.split()), majority_type, list(members)))

    # Merge specific-first so single-token aliases fold into multi-token names.
    reps.sort(key=lambda r: (len(r.tokens), len(r.members)), reverse=True)
    merged: list[_Rep] = []
    for r in reps:
        host = next(
            (
                h
                for h in merged
                if h.type == r.type
                and r.tokens
                and r.tokens < h.tokens
                and not r.tokens <= _GENERIC
            ),
            None,
        )
        if host is not None:
            host.members.extend(r.members)
        else:
            merged.append(r)

    clusters = [_build_cluster(r) for r in merged]
    clusters.sort(key=lambda c: (c.first_seen_chapter, -c.mention_count, c.name))
    return clusters


def _build_cluster(rep: _Rep) -> EntityCluster:
    surfaces = [m.surface.strip() for m in rep.members]
    counts = Counter(surfaces)
    # Canonical name: most frequent surface; tie broken by the longest (most specific).
    best = max(counts.items(), key=lambda kv: (kv[1], len(kv[0])))
    name = best[0]
    first_seen = min(m.chapter_ordinal for m in rep.members)
    subtype = next((m.subtype for m in rep.members if m.subtype), None)
    return EntityCluster(
        name=name,
        type=rep.type,
        subtype=subtype,
        first_seen_chapter=first_seen,
        mention_count=len(rep.members),
        members=rep.members,
    )
