"""Phase 1: end-to-end ingest of the bundled CC0 sample.

Proves the full pipeline (config -> clean -> split -> chunk -> repo), the offset
invariant on persisted chunks, and idempotent double-ingest (no duplicates).
"""

from __future__ import annotations

from pathlib import Path

from storyweave.db.repository import Repository
from storyweave.ingest.pipeline import ingest
from storyweave.ingest.work_config import find_work_config, load_work_config

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "samples" / "the-hollow-crown"


def _load_config() -> object:
    return load_work_config(find_work_config(SAMPLE_DIR))


def test_sample_exists() -> None:
    assert SAMPLE_DIR.is_dir()
    assert list(SAMPLE_DIR.glob("*.txt"))


def test_ingest_sample_end_to_end() -> None:
    cfg = _load_config()
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        report = ingest(SAMPLE_DIR, repo, cfg)  # type: ignore[arg-type]

        assert report.work_slug == "the-hollow-crown"
        assert report.chapters_added == 4
        assert report.chunks_added > 0
        # Two cruft lines in the sample (a [T/N:...] note and a nav line).
        assert report.cruft_lines_removed == 2

        assert repo.count_chapters(report.work_id) == 4
        assert repo.count_chunks(report.work_id) == report.chunks_added


def test_persisted_chunks_satisfy_offset_invariant() -> None:
    cfg = _load_config()
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        report = ingest(SAMPLE_DIR, repo, cfg)  # type: ignore[arg-type]

        for chapter in repo.list_chapters(report.work_id):
            assert chapter.id is not None
            for chunk in repo.list_chunks(chapter.id):
                assert chapter.clean_text[chunk.char_start : chunk.char_end] == chunk.text


def test_double_ingest_no_duplicates() -> None:
    cfg = _load_config()
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        first = ingest(SAMPLE_DIR, repo, cfg)  # type: ignore[arg-type]
        chapters_after_first = repo.count_chapters(first.work_id)
        chunks_after_first = repo.count_chunks(first.work_id)

        second = ingest(SAMPLE_DIR, repo, cfg)  # type: ignore[arg-type]

        assert second.chapters_added == 0
        assert second.chapters_updated == 0
        assert second.chapters_skipped == 4
        assert second.chunks_added == 0
        # Counts are stable: no duplicate rows.
        assert repo.count_chapters(second.work_id) == chapters_after_first
        assert repo.count_chunks(second.work_id) == chunks_after_first
