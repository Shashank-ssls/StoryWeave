"""Phase 2: mentions persistence (light) + GLiNER extraction (ML-gated).

The GLiNER tests use ``importorskip`` so the light .venv gate skips them; they run
under .venv-ml where gliner + torch are installed.
"""

from __future__ import annotations

import pytest

from storyweave.db.models import (
    Chapter,
    Chunk,
    ExtractionMethod,
    Mention,
    Node,
    NodeType,
    Work,
)
from storyweave.db.repository import Repository


def test_mentions_repository_round_trip() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        cid = repo.add_chapter(
            Chapter(work_id=wid, ordinal=1, clean_text="Wren.", content_hash="h")
        )
        mid = repo.add_mention(
            Mention(
                work_id=wid,
                chapter_id=cid,
                chapter_ordinal=1,
                ordinal=0,
                surface="Wren",
                type=NodeType.CHARACTER,
                char_start=0,
                char_end=4,
                score=0.9,
            )
        )
        assert repo.count_mentions(wid) == 1

        nid = repo.add_node(
            Node(
                work_id=wid,
                type=NodeType.CHARACTER,
                name="Wren",
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
        repo.set_mention_node(mid, nid)
        assert repo.list_mentions(wid)[0].node_id == nid

        repo.clear_mentions(wid)
        assert repo.count_mentions(wid) == 0


def test_gliner_extracts_character() -> None:
    pytest.importorskip("gliner")
    from storyweave.nlp.extractor import GlinerExtractor

    spans = GlinerExtractor().extract("Wren stole the heron ring in Aldercross.")
    assert any(s.type is NodeType.CHARACTER and "Wren" in s.surface for s in spans)


def test_extract_work_end_to_end() -> None:
    pytest.importorskip("gliner")
    from storyweave.nlp.pipeline import extract_work

    text = "Wren stole the heron ring in Aldercross, a city of House Veyle."
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        cid = repo.add_chapter(
            Chapter(work_id=wid, ordinal=1, clean_text=text, content_hash="h")
        )
        repo.add_chunk(
            Chunk(
                chapter_id=cid,
                work_id=wid,
                ordinal=0,
                char_start=0,
                char_end=len(text),
                text=text,
                content_hash="c",
            )
        )

        report = extract_work(wid, repo)

        assert report.mentions_count > 0
        assert report.entities_count > 0
        nodes = repo.list_nodes(wid)
        assert any(n.type is NodeType.CHARACTER for n in nodes)
        # Every mention was clustered into a node.
        assert all(m.node_id is not None for m in repo.list_mentions(wid))
        # Re-running is idempotent (clear + rebuild, no duplicate nodes).
        again = extract_work(wid, repo)
        assert repo.count_nodes(wid) == again.entities_count
