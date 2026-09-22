"""The citation gate, checked against real source files (integration phase, Part B.4).

Every one of "The Ninth House"'s curated Tier-3 identity edges
(``demo.seed_ninth_house._IDENTITY_EDGES``) carries an ``evidence_span`` that is
supposed to be a verbatim confirming sentence from its own ``revealed_chapter``'s
prose (docs/demo/the-ninth-house-bible.md §6). This test does not trust that claim —
it re-derives it, reading the actual committed chapter file and checking the quote
against it with the project's OWN citation-gate function
(``nlp.identity.citation_in_range``), the same fabrication guard a live LLM
identity-inference run would be held to. A quote that doesn't occur verbatim
(whitespace/punctuation/case-normalized) in its reveal chapter fails this test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storyweave.demo.seed_ninth_house import _IDENTITY_EDGES
from storyweave.nlp.identity import citation_in_range

_SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "samples" / "the-ninth-house"


def _chapter_text(ordinal: int) -> str:
    path = _SAMPLE_DIR / f"ch{ordinal:02d}.txt"
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "src_names,tgt_names,relation,revealed,evidence",
    _IDENTITY_EDGES,
    ids=[f"{r}@{n}" for _, _, r, n, _ in _IDENTITY_EDGES],
)
def test_identity_evidence_occurs_verbatim_in_its_reveal_chapter(
    src_names: tuple[str, ...],
    tgt_names: tuple[str, ...],
    relation: str,
    revealed: int,
    evidence: str,
) -> None:
    text = _chapter_text(revealed)
    assert citation_in_range(evidence, text), (
        f"{relation} edge {src_names[0]}->{tgt_names[0]} at ch{revealed}: "
        f"evidence_span not found verbatim in ch{revealed:02d}.txt"
    )


def test_all_seven_reveals_present_and_staggered() -> None:
    """A cheap sanity check on the schedule itself, independent of the citation
    gate above: 7 edges, 6 distinct pairs (one deepens), spanning early/mid/late."""
    assert len(_IDENTITY_EDGES) == 7
    pairs = {(src[0], tgt[0]) for src, tgt, *_ in _IDENTITY_EDGES}
    assert len(pairs) == 6  # Sorrel/Aurelia Marrow appears twice (the deepening)
    chapters = sorted(revealed for _, _, _, revealed, _ in _IDENTITY_EDGES)
    assert chapters[0] <= 8 and chapters[-1] >= 35  # spans Arc I through Arc V
    relations = {r for _, _, r, _, _ in _IDENTITY_EDGES}
    assert relations == {"ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"}


def test_evidence_does_not_occur_in_an_earlier_chapter() -> None:
    """The reveal must be a genuine reveal: the confirming sentence should NOT
    already be sitting in an earlier chapter (which would mean it wasn't a secret
    at all before `revealed`)."""
    for src_names, tgt_names, relation, revealed, evidence in _IDENTITY_EDGES:
        for earlier in range(1, revealed):
            text = _chapter_text(earlier)
            assert not citation_in_range(evidence, text), (
                f"{relation} edge {src_names[0]}->{tgt_names[0]}: evidence already "
                f"present in ch{earlier:02d}.txt, before its claimed reveal at "
                f"ch{revealed:02d}"
            )
