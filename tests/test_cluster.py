"""Phase 2: alias clustering (pure Python, light venv)."""

from __future__ import annotations

from storyweave.db.models import Mention, NodeType
from storyweave.nlp.cluster import cluster_mentions, normalize_surface


def _m(surface: str, typ: NodeType, chapter: int, start: int = 0) -> Mention:
    return Mention(
        work_id=1,
        chapter_id=chapter,
        chapter_ordinal=chapter,
        ordinal=0,
        surface=surface,
        type=typ,
        char_start=start,
        char_end=start + len(surface),
        score=0.9,
    )


def test_normalize_strips_articles_and_punctuation() -> None:
    assert normalize_surface("the Coil") == "coil"
    assert normalize_surface('  "Wren," ') == "wren"
    assert normalize_surface("A Sky") == "sky"


def test_cluster_merges_surface_variants_and_subsets() -> None:
    mentions = [
        _m("Wren", NodeType.CHARACTER, 1),
        _m("Wren", NodeType.CHARACTER, 1),
        _m("Aldercross", NodeType.PLACE, 1),
        _m("the Coil", NodeType.ORGANIZATION, 1),
        _m("Coil", NodeType.ORGANIZATION, 2),
        _m("Lady Veris", NodeType.CHARACTER, 3),
        _m("Veris", NodeType.CHARACTER, 3),
    ]
    clusters = {c.name: c for c in cluster_mentions(mentions)}

    # "the Coil"/"Coil" share a normalized form; "Veris" folds into "Lady Veris".
    assert len(clusters) == 4
    assert clusters["Wren"].type is NodeType.CHARACTER
    assert clusters["Wren"].mention_count == 2
    assert clusters["Wren"].first_seen_chapter == 1

    coil = next(c for c in clusters.values() if c.type is NodeType.ORGANIZATION)
    assert coil.mention_count == 2
    assert coil.first_seen_chapter == 1

    assert "Lady Veris" in clusters
    assert clusters["Lady Veris"].mention_count == 2
    assert clusters["Lady Veris"].first_seen_chapter == 3


def test_majority_vote_resolves_type_disagreement() -> None:
    mentions = [
        _m("Aldercross", NodeType.PLACE, 1),
        _m("Aldercross", NodeType.PLACE, 1),
        _m("Aldercross", NodeType.ORGANIZATION, 2),
    ]
    clusters = cluster_mentions(mentions)
    assert len(clusters) == 1
    assert clusters[0].type is NodeType.PLACE  # 2 Place vs 1 Organization


def test_distinct_entities_are_not_merged() -> None:
    mentions = [
        _m("Wren", NodeType.CHARACTER, 1),
        _m("Aldercross", NodeType.PLACE, 1),
    ]
    assert len(cluster_mentions(mentions)) == 2


# --- stopword filter (integration phase, Part C: measured noise pattern from
# docs/INTEGRATION.md Part B.3 — closed-class pronouns + bare generic-object nouns
# never become nodes at all) ------------------------------------------------------ #


def test_pronoun_mentions_are_dropped_before_clustering() -> None:
    mentions = [
        _m("Wren", NodeType.CHARACTER, 1),
        _m("she", NodeType.CHARACTER, 1),
        _m("You", NodeType.CHARACTER, 1),  # case-insensitive
        _m("Herself", NodeType.CHARACTER, 1),
        _m("both of them", NodeType.CHARACTER, 1),
    ]
    clusters = {c.name: c for c in cluster_mentions(mentions)}
    assert set(clusters) == {"Wren"}


def test_bare_generic_object_nouns_are_dropped_but_modified_ones_are_not() -> None:
    mentions = [
        _m("the desk", NodeType.PLACE, 1),  # bare generic -> dropped
        _m("door", NodeType.PLACE, 1),  # bare generic -> dropped
        _m("the Ashcombe Blade", NodeType.ITEM, 1),  # a real, specific name -> kept
        _m("Sorrel's writing desk", NodeType.ITEM, 1),  # "desk" with real context -> kept
    ]
    clusters = {c.name for c in cluster_mentions(mentions)}
    assert clusters == {"the Ashcombe Blade", "Sorrel's writing desk"}


def test_a_real_entity_that_happens_to_be_named_a_pronoun_word_is_still_dropped() -> None:
    """Documented trade-off, not a bug: this filter is a blunt, closed-class-only
    instrument. A hypothetical character literally named "She" would be lost too -
    an acceptable cost for removing the much larger volume of real pronoun noise
    (measured: ~20+ pronoun nodes per 40-chapter work), consistent with GLiNER-floor
    extraction being a floor, not a claim of perfect recall."""
    mentions = [_m("She", NodeType.CHARACTER, 1, start=0)]
    assert cluster_mentions(mentions) == []
