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
