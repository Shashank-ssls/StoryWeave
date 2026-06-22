"""GLiNER label prompts mapped to the canonical 8-type ontology.

GLiNER is zero-shot: it takes free-text label strings. We prompt it with the eight
canonical type names plus a few descriptive aliases that improve recall for the
common-noun ``Concept`` class (power systems, languages, phenomena) — the type
plain proper-noun NER misses. Every prompt maps back to a canonical
:class:`~storyweave.db.models.NodeType`, so what we persist is always one of the 8.
"""

from __future__ import annotations

from storyweave.db.models import NodeType

# prompt string -> canonical NodeType. Multiple prompts may map to one type.
LABEL_TO_TYPE: dict[str, NodeType] = {
    "Character": NodeType.CHARACTER,
    "person": NodeType.CHARACTER,
    "Place": NodeType.PLACE,
    "location": NodeType.PLACE,
    "Organization": NodeType.ORGANIZATION,
    "faction": NodeType.ORGANIZATION,
    "Item": NodeType.ITEM,
    "Ability": NodeType.ABILITY,
    "Concept": NodeType.CONCEPT,
    "power system": NodeType.CONCEPT,
    "phenomenon": NodeType.CONCEPT,
    "language": NodeType.CONCEPT,
    "Event": NodeType.EVENT,
    "Title": NodeType.TITLE,
}

DEFAULT_LABELS: list[str] = list(LABEL_TO_TYPE.keys())
