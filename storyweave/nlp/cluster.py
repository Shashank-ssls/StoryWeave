"""Alias clustering: raw mentions -> canonical entities (Phase 2).

This is the conservative, *string-based* floor of coreference — it merges surface
variants of the same name, NOT semantic identities. It does two things:

1. Group mentions by a normalized surface (case-folded, article-stripped, depunct).
   The canonical type is the majority vote across the group's mentions.
2. Abbreviation-merge (retrofit R3): fold a shortening into its full form when ALL
   FIVE rules hold, and refuse when anything is ambiguous. R4's relation validator has
   to find both participants' names inside a quote, so a missed alias costs recall
   twice over — but an over-merge silently fuses two people, which is unrecoverable and
   corrupts every edge on both. v1 measured 0 over-merges and 3 under-merges; the rules
   below are deliberately built to keep the 0 rather than to chase the 3.

   R1 replaced the old unordered set-subset test with an ORDERED, CONTIGUOUS one:
   set-subset made "Lady Sorrel Vane" and "Vane Sorrel" interchangeable and let
   "Orin Quell" fold into "Orin Drask Quell", which is a different person's name.

True identity links (Wren == Prince Caelum, Gray Sparrow == Lady Veris) are
deliberately NOT made here — those are Tier-3 identity edges that the reveal fence
must gate and the LLM infers in Phase 7. Pure Python: no ML, runs in the light venv.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from storyweave.db.models import Mention, NodeType
from storyweave.ingest.work_config import ClusteringConfig

_PUNCT = "\"'“”‘’()[]{}.,;:!?—-"
_ARTICLES = ("the ", "a ", "an ")
# Tokens too generic to justify a subset merge on their own.
_GENERIC = {
    "the", "a", "an", "lord", "lady", "ser", "sir", "king", "queen",
    "house", "guild", "city", "the boy", "man", "woman",
    # Bare person-nouns (retrofit R3). A common noun on its own is never a reliable
    # shortening of a name: the measured run folded "girl" into "chancery girl", which
    # would fuse every unnamed girl in the book into one character. Honorifics and
    # role words above are here for the same reason. A MODIFIED form is untouched -
    # "chancery girl" is still its own entity, only the bare word is refused.
    "girl", "boy", "child", "lad", "lass", "stranger", "guard", "soldier",
    "servant", "maid", "priest", "scribe", "captain", "master", "maester",
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
    #: ORDERED tokens. A tuple, not a set: word order carries identity.
    tokens: tuple[str, ...]
    type: NodeType
    members: list[Mention]

    @property
    def first_chapter(self) -> int:
        return min(m.chapter_ordinal for m in self.members)


@dataclass
class MergeDecision:
    """One abbreviation-merge decision, kept so under-merges can be reported."""

    short: str
    host: str | None
    merged: bool
    reason: str


@dataclass
class ClusterOutcome:
    clusters: list[EntityCluster]
    decisions: list[MergeDecision] = field(default_factory=list)

    @property
    def merges(self) -> list[MergeDecision]:
        return [d for d in self.decisions if d.merged]

    @property
    def under_merges(self) -> list[MergeDecision]:
        """Candidate shortenings that were NOT folded in, each with its reason."""
        return [d for d in self.decisions if not d.merged]


def is_contiguous_subsequence(short: tuple[str, ...], full: tuple[str, ...]) -> bool:
    """True when ``short`` appears in ``full`` as consecutive words, in order.

    Rule 1. "drask" and "orin drask" are contiguous runs of "warden-captain orin drask";
    "orin quell" is not, even though both its words appear — which is the point, because
    that is how two different people get fused.
    """
    n = len(short)
    if not n or n >= len(full):
        return False
    return any(full[i : i + n] == short for i in range(len(full) - n + 1))


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


def cluster_mentions(
    mentions: list[Mention], config: ClusteringConfig | None = None
) -> list[EntityCluster]:
    """Cluster raw mentions into canonical entities with a first_seen_chapter."""
    return cluster_mentions_detailed(mentions, config).clusters


def cluster_mentions_detailed(
    mentions: list[Mention], config: ClusteringConfig | None = None
) -> ClusterOutcome:
    """Cluster, and return every merge decision so under-merges can be reported.

    The abbreviation merge applies five rules and ALL of them must hold. When anything
    is ambiguous the merge is refused: a missed alias costs recall, a wrong one fuses
    two characters and corrupts every edge on both.
    """
    cfg = config or ClusteringConfig()

    by_norm: dict[str, list[Mention]] = {}
    for m in mentions:
        norm = normalize_surface(m.surface)
        if norm and not _is_stopword(norm):
            by_norm.setdefault(norm, []).append(m)

    reps: list[_Rep] = []
    for norm, members in by_norm.items():
        majority_type = Counter(m.type for m in members).most_common(1)[0][0]
        reps.append(_Rep(norm, tuple(norm.split()), majority_type, list(members)))

    # Longest names first, so a shortening meets its full form already placed.
    reps.sort(key=lambda r: (len(r.tokens), len(r.members)), reverse=True)
    hosts: list[_Rep] = []
    decisions: list[MergeDecision] = []

    for r in reps:
        if not cfg.merge_abbreviations:
            hosts.append(r)
            continue

        # Rule 4: a shortening made only of generic/stop words carries no identity.
        # ("lord", "the boy", "house" - these match half the cast.)
        if not r.tokens or set(r.tokens) <= _GENERIC:
            hosts.append(r)
            if len(r.tokens) < 2:
                decisions.append(
                    MergeDecision(r.norm, None, False, "rule 4: stop-word-only shortening")
                )
            continue

        # Rule 1: same type AND an ordered, contiguous run of the host's words.
        candidates = [
            h
            for h in hosts
            if h.type == r.type and is_contiguous_subsequence(r.tokens, h.tokens)
        ]

        if not candidates:
            hosts.append(r)
            continue

        # Rule 5 - "the short form does not match another entity's full name" - is
        # enforced structurally rather than by a separate test, and it is worth being
        # explicit about why, because a check here could never fire. Reps are keyed by
        # NORMALIZED SURFACE, so a short form that is spelled exactly like another
        # entity's full name IS that rep: there is one "drask", not two, and its mentions
        # are already pooled. The failure mode the rule is really about - a short form
        # that could belong to more than one full name - is therefore the same condition
        # as the ambiguity guard below, and that is where it is handled.
        #
        # The cross-type variant ("Vane" the place vs "Sorrel Vane" the character) is
        # excluded earlier, by the same-type requirement in rule 1.

        # Rule 2: the full form must appear first, or in the same chapter. A shortening
        # the reader meets BEFORE the full name is not yet attributable to it.
        in_order = [h for h in candidates if h.first_chapter <= r.first_chapter]
        if not in_order:
            hosts.append(r)
            decisions.append(
                MergeDecision(
                    r.norm, candidates[0].norm, False,
                    f"rule 2: short form appears first (ch{r.first_chapter} before "
                    f"ch{candidates[0].first_chapter})",
                )
            )
            continue

        # Rule 3: within the configured chapter window.
        in_window = [
            h
            for h in in_order
            if r.first_chapter - h.first_chapter <= cfg.abbreviation_chapter_window
        ]
        if not in_window:
            hosts.append(r)
            decisions.append(
                MergeDecision(
                    r.norm, in_order[0].norm, False,
                    f"rule 3: outside the {cfg.abbreviation_chapter_window}-chapter "
                    f"window (ch{in_order[0].first_chapter} -> ch{r.first_chapter})",
                )
            )
            continue

        # Ambiguity (and rule 5): more than one full name could host this shortening, so
        # which person it refers to is genuinely unknown. Refuse. This single guard is
        # what keeps the over-merge count at 0, and it is the reason the rules are
        # written as "all must hold" rather than "best match wins".
        if len(in_window) > 1:
            hosts.append(r)
            decisions.append(
                MergeDecision(
                    r.norm, None, False,
                    "ambiguous: "
                    + str(len(in_window))
                    + " candidate full names ("
                    + ", ".join(sorted(h.norm for h in in_window))
                    + ")",
                )
            )
            continue

        host = in_window[0]
        host.members.extend(r.members)
        decisions.append(MergeDecision(r.norm, host.norm, True, "all five rules hold"))

    clusters = [_build_cluster(r) for r in hosts]
    clusters.sort(key=lambda c: (c.first_seen_chapter, -c.mention_count, c.name))
    return ClusterOutcome(clusters=clusters, decisions=decisions)


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
