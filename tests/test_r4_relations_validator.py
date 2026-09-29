"""Retrofit R4: the closed relation list, the validator, weight, and D1/D2.

The validator tests use REAL corpus strings (or strings of exactly the corpus's shape),
because a validator tested only on invented sentences proves nothing about the book it
has to run on. The two the R4 brief names by hand -- the vocative "little sister" and
the possessive "his niece" -- are pinned first.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from storyweave.db.models import (
    DOMAIN_RANGE,
    LEGACY_RELATION_MAP,
    RELATIONS,
    Edge,
    ExtractionMethod,
    LegacyRelationFate,
    Node,
    NodeType,
    Relation,
    RelationGrade,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.extract.relations import expand_to_sentence
from storyweave.extract.validator import (
    RejectReason,
    RelationProposal,
    ValidationContext,
    validate,
)
from storyweave.graph import serialize
from storyweave.query import fence

FROZEN_DB = Path("evidence/v1_ninth_house.db")

CH = 9
TEXT = (
    "Warden-Captain Orin Drask ran the Salt Quarter watch. "
    "\"Am I not blessed to suddenly get such a wonderful little sister?\" "
    "The Saint looked at his niece and said nothing. "
    "Juno Stray was like a sister to Ettie Marsh, but no kin of hers. "
    "Orin Drask's father had kept the same ledger."
)


def _context(**overrides: object) -> ValidationContext:
    base: dict[str, object] = {
        "clean_text": {CH: TEXT},
        "node_types": {
            1: NodeType.CHARACTER,
            2: NodeType.CHARACTER,
            3: NodeType.ORGANIZATION,
            4: NodeType.PLACE,
            5: NodeType.ITEM,
        },
        "labels": {
            1: ["Orin Drask", "Drask"],
            2: ["The Saint"],
            3: ["Salt Quarter watch"],
            4: ["Salt Quarter"],
            5: ["ledger"],
        },
    }
    base.update(overrides)
    return ValidationContext(**base)  # type: ignore[arg-type]


def _proposal(**overrides: object) -> RelationProposal:
    base: dict[str, object] = {
        "relation": "KIN_OF",
        "source_id": 1,
        "target_id": 2,
        "quote": "The Saint looked at his niece",
        "quote_chapter": CH,
    }
    base.update(overrides)
    return RelationProposal(**base)  # type: ignore[arg-type]


# --- the two cases the R4 brief names --------------------------------------- #


def test_vocative_little_sister_is_rejected() -> None:
    """A vocative in dialogue is not a kin claim (R4 acceptance, verbatim case)."""
    quote = '"Am I not blessed to suddenly get such a wonderful little sister?"'
    result = validate(_proposal(quote=quote), _context())
    assert not result.ok
    assert result.reason is RejectReason.KIN_GUARD


def test_possessive_his_niece_is_accepted() -> None:
    """A possessive pronoun attaches the kin word to a participant (R4 acceptance)."""
    result = validate(_proposal(), _context())
    assert result.ok
    assert result.relation is Relation.KIN_OF
    assert result.kin_role == "niece"


# --- one test per validator branch, in check order --------------------------- #


def test_a_quote_must_be_verbatim_in_the_claimed_chapter() -> None:
    result = validate(_proposal(quote="The Saint looked at his cousin"), _context())
    assert result.reason is RejectReason.QUOTE_NOT_VERBATIM


def test_a_quote_in_a_different_chapter_is_rejected() -> None:
    """The chapter is part of the citation: the right words in the wrong chapter fail."""
    result = validate(_proposal(quote_chapter=CH + 1), _context())
    assert result.reason is RejectReason.QUOTE_NOT_VERBATIM


def test_b_relation_must_be_one_of_the_twelve() -> None:
    result = validate(_proposal(relation="Respects"), _context())
    assert result.reason is RejectReason.RELATION_NOT_CLOSED


def test_c_domain_range_rejects_a_person_owning_a_person() -> None:
    result = validate(
        _proposal(
            relation="OWNS",
            source_id=1,
            target_id=2,
            quote="Orin Drask's father had kept the same ledger.",
        ),
        _context(),
    )
    assert result.reason is RejectReason.DOMAIN_RANGE


def test_c_symmetric_relation_arriving_backwards_is_swapped_not_rejected() -> None:
    """ALLY_OF is C,O <-> C,O, so an Organization-first proposal is valid, not junk."""
    result = validate(
        _proposal(
            relation="ALLY_OF",
            source_id=3,
            target_id=1,
            quote="Warden-Captain Orin Drask ran the Salt Quarter watch.",
        ),
        _context(),
    )
    assert result.ok


def test_d_an_ungrounded_endpoint_is_rejected() -> None:
    result = validate(_proposal(target_id=None), _context())
    assert result.reason is RejectReason.ENDPOINT_NOT_STORED


def test_d_an_endpoint_that_is_not_a_stored_node_is_rejected() -> None:
    result = validate(_proposal(target_id=999), _context())
    assert result.reason is RejectReason.ENDPOINT_NOT_STORED


def test_d_a_self_loop_is_rejected() -> None:
    result = validate(_proposal(target_id=1), _context())
    assert result.reason is RejectReason.SELF_LOOP


def test_e_a_simile_is_not_a_kin_claim() -> None:
    quote = "Juno Stray was like a sister to Ettie Marsh, but no kin of hers."
    result = validate(_proposal(quote=quote), _context())
    assert result.reason is RejectReason.KIN_GUARD
    assert "simile" in result.detail


def test_e_a_genitive_on_a_participant_name_is_accepted() -> None:
    result = validate(
        _proposal(quote="Orin Drask's father had kept the same ledger."), _context()
    )
    assert result.ok
    assert result.kin_role == "father"


def test_e_an_unattached_kin_claim_repeated_in_two_chapters_is_accepted() -> None:
    """The guard's second limb: recurrence across chapters substitutes for a possessive."""
    quote = '"Am I not blessed to suddenly get such a wonderful little sister?"'
    context = _context(kin_claim_chapters={(1, 2, "sister of"): {9, 17}})
    result = validate(_proposal(quote=quote, kin_role="sister of"), context)
    assert result.ok


def test_f_grade_is_stated_only_when_both_names_and_a_cue_are_present() -> None:
    both = "Warden-Captain Orin Drask ran the Salt Quarter watch."
    stated = validate(
        _proposal(relation="LEADS", source_id=1, target_id=3, quote=both), _context()
    )
    assert stated.ok and stated.grade is RelationGrade.STATED
    # Both "captain" (inside "Warden-Captain") and "ran" are LEADS cues; the longest
    # match wins, and which one it is does not matter -- what matters is that a cue was
    # found and recorded, so the grade can be audited back to a word in the sentence.
    assert stated.surface_term in {"captain", "ran"}

    # The same relation, evidenced by a sentence that names only one participant.
    one_name = "The Saint looked at his niece"
    inferred = validate(
        _proposal(relation="LEADS", source_id=2, target_id=3, quote=one_name), _context()
    )
    assert inferred.ok and inferred.grade is RelationGrade.INFERRED


def test_f_a_cue_never_matches_inside_a_longer_word() -> None:
    """"in" must not match "inside": cues are whole words (R4 grade rule)."""
    from storyweave.extract.validator import find_cue

    assert find_cue("the brigandine", Relation.LOCATED_IN, {Relation.LOCATED_IN: ["in"]}) is None
    assert find_cue("in the Quarter", Relation.LOCATED_IN, {Relation.LOCATED_IN: ["in"]}) == "in"


# --- the ontology ------------------------------------------------------------ #


def test_there_are_exactly_twelve_relations_and_each_has_a_domain_range() -> None:
    assert len(RELATIONS) == 12
    assert set(DOMAIN_RANGE) == set(RELATIONS)


def test_every_legacy_relation_has_a_recorded_fate() -> None:
    """No v1 relation may be silently forgotten (retrofit rule 3 + the R3 precedent)."""
    for old, (fate, new, _reverse) in LEGACY_RELATION_MAP.items():
        assert isinstance(old, str)
        if fate is LegacyRelationFate.MAPS:
            assert new in RELATIONS
        else:
            assert new is None


def test_student_maps_to_mentor_reversed() -> None:
    fate, new, reverse = LEGACY_RELATION_MAP["Student"]
    assert (fate, new, reverse) == (LegacyRelationFate.MAPS, Relation.MENTOR_OF, True)


def test_the_identity_family_collapses_to_same_as() -> None:
    for old in ("SAME_AS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"):
        assert LEGACY_RELATION_MAP[old][1] is Relation.SAME_AS
    # ALIAS is a label, not an edge.
    assert LEGACY_RELATION_MAP["ALIAS"][0] is LegacyRelationFate.BECOMES_LABEL


def test_expand_to_sentence_returns_a_literal_substring() -> None:
    quote = expand_to_sentence(TEXT, TEXT.index("The Saint"), TEXT.index("and said"))
    assert quote in TEXT
    assert "The Saint looked at his niece" in quote


# --- weight, not duplicates (R4 task 5) -------------------------------------- #


def _tiny_work(tmp_path: Path) -> tuple[Repository, int, int, int]:
    repo = Repository(tmp_path / "r4.sqlite")
    repo.initialize_schema()
    work_id = repo.create_work(Work(slug="w", title="W"))
    ids = []
    for name in ("A", "B"):
        ids.append(
            repo.add_node(
                Node(
                    work_id=work_id, name=name, type=NodeType.CHARACTER,
                    first_seen_chapter=1, revealed_chapter=1,
                    extraction_method=ExtractionMethod.GLINER,
                )
            )
        )
    return repo, work_id, ids[0], ids[1]


def _edge(work_id: int, src: int, tgt: int, relation: str, chapter: int = 5) -> Edge:
    return Edge(
        work_id=work_id, source_id=src, target_id=tgt, relation=relation,
        tier=RelationTier.SOCIAL, first_seen_chapter=chapter,
        revealed_chapter=chapter, extraction_method=ExtractionMethod.GLINER,
        grade=RelationGrade.INFERRED, quote="q", quote_chapter=chapter,
    )


def test_repeat_evidence_increments_weight_and_keeps_the_earliest_quote(
    tmp_path: Path,
) -> None:
    repo, work_id, a, b = _tiny_work(tmp_path)
    repo.add_edge(_edge(work_id, a, b, "ALLY_OF", chapter=5))
    existing = repo.get_edge_by_relation_pair(work_id, "ALLY_OF", a, b)
    assert existing is not None
    repo.reinforce_edge(
        existing, first_seen_chapter=3, revealed_chapter=3,
        grade=RelationGrade.INFERRED, quote="earlier", quote_chapter=3,
    )
    after = repo.get_edge_by_relation_pair(work_id, "ALLY_OF", a, b)
    assert after is not None
    assert after.weight == 2
    assert after.revealed_chapter == 3  # reveal only ever moves earlier
    assert after.quote == "earlier"
    repo.close()


def test_a_stated_quote_displaces_an_inferred_one_even_if_later(tmp_path: Path) -> None:
    repo, work_id, a, b = _tiny_work(tmp_path)
    repo.add_edge(_edge(work_id, a, b, "ALLY_OF", chapter=3))
    existing = repo.get_edge_by_relation_pair(work_id, "ALLY_OF", a, b)
    assert existing is not None
    repo.reinforce_edge(
        existing, first_seen_chapter=9, revealed_chapter=9,
        grade=RelationGrade.STATED, quote="a stated one", quote_chapter=9,
    )
    after = repo.get_edge_by_relation_pair(work_id, "ALLY_OF", a, b)
    assert after is not None
    assert after.grade is RelationGrade.STATED
    assert after.quote == "a stated one"
    assert after.revealed_chapter == 3  # the stamp still never moves later
    repo.close()


def test_the_unique_key_includes_the_relation_so_two_relations_coexist(
    tmp_path: Path,
) -> None:
    """D2 in the storage layer: one pair may carry two DIFFERENT relations."""
    repo, work_id, a, b = _tiny_work(tmp_path)
    repo.add_edge(_edge(work_id, a, b, "ALLY_OF"))
    repo.add_edge(_edge(work_id, a, b, "SAME_AS"))
    assert len(repo.list_edges(work_id)) == 2
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_edge(_edge(work_id, a, b, "ALLY_OF"))  # the same one twice
    repo.close()


# --- D1 / D2: the payload is built from rows --------------------------------- #


@pytest.mark.skipif(not FROZEN_DB.exists(), reason="frozen baseline not present")
def test_d2_the_secret_identity_edge_reaches_the_payload(tmp_path: Path) -> None:
    """Edge 1325 SECRET_IDENTITY (14 -> 150) used to be overwritten by 1327.

    The frozen baseline is opened READ-ONLY and is never migrated; this is also the
    regression test for a pre-R4 database still serving.
    """
    import shutil

    copy = tmp_path / "frozen.sqlite"
    shutil.copy(FROZEN_DB, copy)
    copy.chmod(0o644)
    with Repository(copy) as repo:
        work = repo.get_work_by_slug("the-ninth-house")
        assert work is not None and work.id is not None
        payload = serialize.graph_json(repo, work.id, 40)
        ids = {e["data"]["id"] for e in payload["elements"]["edges"]}
        assert "e1325" in ids
        assert "e1327" in ids
        relations = {
            e["data"]["id"]: e["data"]["relation"] for e in payload["elements"]["edges"]
        }
        assert relations["e1325"] == "SECRET_IDENTITY"
        assert relations["e1327"] == "REINCARNATION"


@pytest.mark.skipif(not FROZEN_DB.exists(), reason="frozen baseline not present")
@pytest.mark.parametrize("chapter", [1, 5, 9, 17, 25, 37, 40])
def test_d1_payload_edge_count_equals_fenced_drawable_row_count(
    tmp_path: Path, chapter: int
) -> None:
    """No edge may be lost between the fence and the payload, at any chapter."""
    import shutil

    copy = tmp_path / "frozen.sqlite"
    shutil.copy(FROZEN_DB, copy)
    copy.chmod(0o644)
    with Repository(copy) as repo:
        work = repo.get_work_by_slug("the-ninth-house")
        assert work is not None and work.id is not None
        drawn = {n.id for n in fence.visible_graph_nodes(repo, work.id, chapter)}
        rows = [
            e
            for e in fence.visible_edges(repo, work.id, chapter)
            if e.source_id in drawn and e.target_id in drawn
        ]
        payload = serialize.graph_json(repo, work.id, chapter)
        assert len(payload["elements"]["edges"]) == len(rows)
        # ... and every row is present exactly once, not merely counted.
        assert {f"e{e.id}" for e in rows} == {
            e["data"]["id"] for e in payload["elements"]["edges"]
        }


def test_a_pre_r4_database_serves_without_the_r4_columns(tmp_path: Path) -> None:
    """A read-only legacy database cannot be migrated, so the reads must degrade."""
    legacy = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(legacy)
    conn.executescript(
        """
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT, work_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
            relation TEXT NOT NULL, tier INTEGER NOT NULL,
            first_seen_chapter INTEGER NOT NULL, revealed_chapter INTEGER NOT NULL,
            extraction_method TEXT NOT NULL, evidence_span TEXT);
        INSERT INTO edges VALUES (1, 1, 1, 2, 'Ally', 2, 1, 1, 'rule', 'q');
        """
    )
    conn.commit()
    conn.close()
    with Repository(legacy) as repo:
        assert repo.has_edge_r4_columns() is False
        edge = repo.list_edges(1)[0]
        assert edge.grade is None and edge.weight == 1
