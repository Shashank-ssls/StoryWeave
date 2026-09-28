"""GLiNER label prompts, mapped to the four types the graph draws (retrofit R3).

GLiNER is zero-shot: it takes free-text label strings. Prompting it with eight types was
the largest single entity error category in the v1 measurement — 16 of 44 errors were
type disagreement, and every one of the four types removed here scored F1 = 0.000
(``evidence/EVAL_V1.md`` §9). A zero-shot model has no way to tell an "Ability" from a
"Concept" from an "Event" in prose; asking it to costs precision on the four types that
do work.

So the prompt set is now Character / Organization / Place / Item only, keeping exactly the
descriptive aliases v1 already used for those four ("person", "location", "faction") and
adding none. Nothing is added in the same phase that removes four types, so the measured
difference is attributable to the type reduction and nothing else. This is enforcement
point (a) of R3:
nothing outside :data:`~storyweave.db.models.GRAPH_NODE_TYPES` is ever *created*.
Prompt phrasing stays per-work data (``[extraction] extra_labels`` in
``storyweave.toml``), never hardcoded per book.

Species is kept as an optional Character *attribute* (a subtype/property), not a type of
its own — see ``SUBTYPES[NodeType.CHARACTER]`` and SPEC §5.2.
"""

from __future__ import annotations

from storyweave.db.models import GRAPH_NODE_TYPES, NodeType

# prompt string -> canonical NodeType. Multiple prompts may map to one type; every
# value is one of the four drawable types.
LABEL_TO_TYPE: dict[str, NodeType] = {
    "Character": NodeType.CHARACTER,
    "person": NodeType.CHARACTER,
    "Place": NodeType.PLACE,
    "location": NodeType.PLACE,
    "Organization": NodeType.ORGANIZATION,
    "faction": NodeType.ORGANIZATION,
    "Item": NodeType.ITEM,
}

DEFAULT_LABELS: list[str] = list(LABEL_TO_TYPE.keys())

# Guard the invariant at import time: a prompt that maps to a non-drawable type would
# create nodes the graph can never serve, which is a bug, not a configuration choice.
assert set(LABEL_TO_TYPE.values()) <= set(GRAPH_NODE_TYPES), (
    "every GLiNER prompt must map to a drawable type: "
    f"{sorted({t.value for t in LABEL_TO_TYPE.values()} - {t.value for t in GRAPH_NODE_TYPES})}"
)
