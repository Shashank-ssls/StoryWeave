"""The R4 validator: the code that disposes of what the model proposes.

Retrofit rule 8 says the LLM (or here, GLiNER-RelEx) proposes and the code disposes;
retrofit rule 4 says citation or nothing. This module is where both are enforced. Every
proposed edge runs the same six checks, in the order the R4 brief fixes, and the first
one it fails is the reason it is refused. A refusal is written to
``validator_rejections`` with its reason code -- refusals are evidence, and the phase
reports counts by reason rather than a single "n edges kept".

The checks, in order:

a. ``QUOTE_NOT_VERBATIM`` -- the quote must appear character-for-character in the clean
   text of the chapter it claims. This is the check that makes every other claim
   auditable: a quote that is not in the book cannot support anything.
b. ``RELATION_NOT_CLOSED`` -- the relation must be one of the twelve (retrofit rule 3).
c. ``DOMAIN_RANGE`` -- the endpoint TYPES must match the relation's domain and range.
d. ``ENDPOINT_NOT_STORED`` / ``SELF_LOOP`` -- both endpoints must be entities the floor
   already grounded. No phantom nodes, ever.
e. ``KIN_GUARD`` -- kinship needs more than a kin word in the neighbourhood (see
   :func:`_possessive_kin`).
f. grade -- STATED iff the quote names both participants AND carries a relation cue.
   This never rejects; it decides whether the edge is servable.

The module holds no SQL and opens no database: it takes a :class:`ValidationContext` of
plain dicts, so it is directly unit-testable on real corpus strings.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from storyweave.db.models import (
    DOMAIN_RANGE,
    RELATIONS,
    SYMMETRIC_R4_RELATIONS,
    NodeType,
    Relation,
    RelationGrade,
)
from storyweave.extract.cues import DEFAULT_CUES, KIN_NOUNS


class RejectReason(StrEnum):
    """Why a proposal was refused. One code per check, in check order."""

    QUOTE_NOT_VERBATIM = "QUOTE_NOT_VERBATIM"
    RELATION_NOT_CLOSED = "RELATION_NOT_CLOSED"
    DOMAIN_RANGE = "DOMAIN_RANGE"
    ENDPOINT_NOT_STORED = "ENDPOINT_NOT_STORED"
    SELF_LOOP = "SELF_LOOP"
    KIN_GUARD = "KIN_GUARD"


@dataclass(frozen=True)
class RelationProposal:
    """One candidate edge, before the validator sees it."""

    relation: str
    source_id: int | None
    target_id: int | None
    quote: str
    quote_chapter: int
    source_surface: str = ""
    target_surface: str = ""
    score: float = 0.0
    kin_role: str | None = None
    subtype: str | None = None


@dataclass(frozen=True)
class ValidationContext:
    """Everything the validator needs to judge a proposal, as plain data.

    ``kin_claim_chapters`` implements the second half of the kin guard: a kin claim with
    no possessive attachment is still accepted if the SAME claim (same pair, same kin
    role) is made in two or more distinct chapters. It has to be precomputed over the
    whole work, so the caller builds it in a first pass and validates in a second.
    """

    clean_text: Mapping[int, str]
    node_types: Mapping[int, NodeType]
    labels: Mapping[int, Sequence[str]]
    kin_claim_chapters: Mapping[tuple[int, int, str], set[int]] = field(
        default_factory=dict
    )
    cues: Mapping[Relation, Sequence[str]] = field(default_factory=lambda: DEFAULT_CUES)


@dataclass(frozen=True)
class ValidationResult:
    """The verdict. ``ok`` edges carry their normalised endpoints and their grade."""

    ok: bool
    reason: RejectReason | None = None
    detail: str = ""
    relation: Relation | None = None
    source_id: int | None = None
    target_id: int | None = None
    grade: RelationGrade | None = None
    surface_term: str | None = None
    kin_role: str | None = None


def _word_re(term: str) -> re.Pattern[str]:
    """A whole-word (or whole-phrase) matcher, so "in" never matches "brigandine"."""
    return re.compile(rf"(?<!\w){re.escape(term.lower())}(?!\w)")


def find_cue(
    quote: str, relation: Relation, cues: Mapping[Relation, Sequence[str]]
) -> str | None:
    """The first cue word for ``relation`` present in ``quote``, or None.

    Longest cue first, so "in love" is reported rather than the "in" inside it.
    """
    lowered = quote.lower()
    for term in sorted(cues.get(relation, ()), key=len, reverse=True):
        if _word_re(term).search(lowered):
            return term
    return None


def find_label(quote: str, labels: Sequence[str]) -> str | None:
    """The first of an entity's labels that appears verbatim in the quote."""
    lowered = quote.lower()
    for label in sorted(labels, key=len, reverse=True):
        if label and _word_re(label).search(lowered):
            return label
    return None


_KIN_ALT = "|".join(KIN_NOUNS)

#: "like a sister", "as a brother to him" -- a simile is not a kin claim.
_SIMILE = re.compile(
    rf"\b(?:like|as)\s+(?:a|an|the|his|her|their|my|your)\s+(?:{_KIN_ALT})\b",
    re.IGNORECASE,
)

#: An optional adjective the text may slip between the possessive and the kin noun.
_KIN_ADJ = r"(?:own\s+|young\s+|older\s+|elder\s+|little\s+|dear\s+|poor\s+)*"

_PRONOUN_KIN = re.compile(
    rf"\b(?:his|her|their|my|your|its)\s+{_KIN_ADJ}({_KIN_ALT})\b", re.IGNORECASE
)


def _possessive_kin(quote: str, labels: Sequence[str]) -> str | None:
    """The kin noun attached by a possessive to a participant, or None.

    Two forms count, and only these two:

    * a genitive on a participant's own name -- "Orin's father", "Drask's niece";
    * a possessive pronoun -- "his niece", "her mother", "their son".

    A bare kin noun does NOT count. That is the whole point of the guard: "such a
    wonderful little sister" is a vocative in dialogue, not a statement that these two
    people are siblings, and it is exactly the shape that makes naive kinship
    extraction wrong.
    """
    if _SIMILE.search(quote):
        return None
    pronoun = _PRONOUN_KIN.search(quote)
    if pronoun:
        return pronoun.group(1).lower()
    for label in labels:
        if not label:
            continue
        genitive = re.search(
            rf"{re.escape(label)}(?:'s|s')\s+{_KIN_ADJ}({_KIN_ALT})\b",
            quote,
            re.IGNORECASE,
        )
        if genitive:
            return genitive.group(1).lower()
    return None


def _kin_guard(
    proposal: RelationProposal,
    context: ValidationContext,
    source_id: int,
    target_id: int,
) -> tuple[bool, str, str | None]:
    """R4 task 3e. Returns (accepted, detail, kin_role)."""
    labels = [*context.labels.get(source_id, ()), *context.labels.get(target_id, ())]
    role = _possessive_kin(proposal.quote, labels)
    if role is not None:
        return True, "possessive genitive", role
    key = (min(source_id, target_id), max(source_id, target_id), proposal.kin_role or "")
    chapters = context.kin_claim_chapters.get(key, set())
    if len(chapters) >= 2:
        return True, f"repeated in chapters {sorted(chapters)}", proposal.kin_role
    if _SIMILE.search(proposal.quote):
        return False, "simile, not a kin claim", None
    return False, "no possessive attachment and claimed in only one chapter", None


def validate(proposal: RelationProposal, context: ValidationContext) -> ValidationResult:
    """Run the six checks in order. The first failure is the verdict."""
    # (a) the quote must really be in the book.
    chapter_text = context.clean_text.get(proposal.quote_chapter)
    if not proposal.quote or chapter_text is None or proposal.quote not in chapter_text:
        return ValidationResult(
            False,
            RejectReason.QUOTE_NOT_VERBATIM,
            f"quote not found verbatim in chapter {proposal.quote_chapter}",
        )

    # (b) the relation must be one of the twelve.
    try:
        relation = Relation(proposal.relation)
    except ValueError:
        return ValidationResult(
            False,
            RejectReason.RELATION_NOT_CLOSED,
            f"{proposal.relation!r} is not one of the {len(RELATIONS)} relations",
        )

    # (d, first half) both endpoints must be stored entities. Checked before the type
    # rule because the type rule needs their types.
    source_id, target_id = proposal.source_id, proposal.target_id
    if source_id is None or target_id is None:
        return ValidationResult(
            False, RejectReason.ENDPOINT_NOT_STORED, "an endpoint did not ground"
        )
    if source_id == target_id:
        return ValidationResult(False, RejectReason.SELF_LOOP, "source == target")
    if source_id not in context.node_types or target_id not in context.node_types:
        return ValidationResult(
            False, RejectReason.ENDPOINT_NOT_STORED, "an endpoint is not a stored node"
        )

    # (c) domain and range.
    spec = DOMAIN_RANGE[relation]
    source_type = context.node_types[source_id]
    target_type = context.node_types[target_id]
    if source_type not in spec.head or target_type not in spec.tail:
        # A symmetric relation may simply have arrived the other way round.
        swapped = spec.symmetric and target_type in spec.head and source_type in spec.tail
        if not swapped:
            return ValidationResult(
                False,
                RejectReason.DOMAIN_RANGE,
                f"{source_type.value} -{relation.value}-> {target_type.value} "
                f"violates domain/range",
            )
        source_id, target_id = target_id, source_id

    # (e) the kin guard.
    kin_role = proposal.kin_role
    if relation is Relation.KIN_OF:
        accepted, detail, kin_role = _kin_guard(proposal, context, source_id, target_id)
        if not accepted:
            return ValidationResult(False, RejectReason.KIN_GUARD, detail)

    # Symmetric relations are stored order-independently, so one pair is one row.
    if relation in SYMMETRIC_R4_RELATIONS and source_id > target_id:
        source_id, target_id = target_id, source_id

    # (f) the grade. Never rejects; decides what the graph may serve.
    head_label = find_label(proposal.quote, context.labels.get(source_id, ()))
    tail_label = find_label(proposal.quote, context.labels.get(target_id, ()))
    cue = find_cue(proposal.quote, relation, context.cues)
    stated = head_label is not None and tail_label is not None and cue is not None
    return ValidationResult(
        True,
        relation=relation,
        source_id=source_id,
        target_id=target_id,
        grade=RelationGrade.STATED if stated else RelationGrade.INFERRED,
        surface_term=cue,
        kin_role=kin_role,
        detail=(
            f"head={head_label!r} tail={tail_label!r} cue={cue!r}"
            if stated
            else f"not stated: head={head_label!r} tail={tail_label!r} cue={cue!r}"
        ),
    )
