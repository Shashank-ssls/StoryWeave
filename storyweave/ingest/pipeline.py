"""Ingest orchestration: config -> clean -> split -> chunk -> repository.

Idempotent: a chapter is keyed by (work, ordinal) and carries a content hash of
its clean text. Re-ingesting identical content inserts nothing; changed content
replaces the chapter and its chunks. Returns an :class:`IngestReport`.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from storyweave.db.models import Chapter, Chunk
from storyweave.db.repository import Repository
from storyweave.ingest.cleaner import clean_text
from storyweave.ingest.splitter import RawChapter, chunk_chapter, detect_chapters
from storyweave.ingest.work_config import WorkConfig

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    return _SLUG_STRIP.sub("-", value.lower()).strip("-") or "untitled"


def detect_outline(text: str, config: WorkConfig | None = None) -> list[RawChapter]:
    """Detect the chapter outline of raw pasted text WITHOUT writing to the DB.

    Runs the exact same ``detect_chapters`` splitter the ingest pipeline uses (on the
    raw text, before cleaning — which is the order ingest detects in), so a preview
    count is guaranteed to match what ``ingest`` would actually persist. No mutation.
    """
    cfg = config or WorkConfig()
    tmp = Path(tempfile.gettempdir()) / f"storyweave-preview-{_sha256(text)[:16]}.txt"
    tmp.write_text(text, encoding="utf-8")
    try:
        return detect_chapters(tmp, cfg.splitting)
    finally:
        tmp.unlink(missing_ok=True)


@dataclass
class IngestReport:
    work_slug: str
    work_id: int
    chapters_added: int = 0
    chapters_updated: int = 0
    chapters_skipped: int = 0
    chunks_added: int = 0
    cruft_lines_removed: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"work '{self.work_slug}' (id={self.work_id}): "
            f"+{self.chapters_added} chapters, ~{self.chapters_updated} updated, "
            f"={self.chapters_skipped} unchanged, +{self.chunks_added} chunks, "
            f"{self.cruft_lines_removed} cruft lines removed"
        )


def ingest(
    source: Path | str,
    repo: Repository,
    config: WorkConfig | None = None,
    *,
    slug: str | None = None,
    title: str | None = None,
) -> IngestReport:
    """Ingest a file or directory of ``.txt`` chapters into ``repo``."""
    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"ingest source not found: {src}")

    cfg = config or WorkConfig()

    work_slug = slug or cfg.slug or slugify(src.stem if src.is_file() else src.name)
    work_title = title or cfg.title or src.stem.replace("_", " ").replace("-", " ").title()

    work_id = repo.get_or_create_work(work_slug, work_title)
    report = IngestReport(work_slug=work_slug, work_id=work_id)

    raw_chapters = detect_chapters(src, cfg.splitting)
    if not raw_chapters:
        report.warnings.append("no chapters detected in source")
        return report

    seen_ordinals: set[int] = set()
    for raw in raw_chapters:
        if raw.ordinal in seen_ordinals:
            report.warnings.append(
                f"duplicate chapter ordinal {raw.ordinal} in source; later one skipped"
            )
            continue
        seen_ordinals.add(raw.ordinal)

        cleaned = clean_text(raw.raw_text, cfg.cleaning)
        report.cruft_lines_removed += len(cleaned.removed_lines)
        if not cleaned.text:
            report.warnings.append(f"chapter ordinal {raw.ordinal} empty after cleaning")
            continue

        content_hash = _sha256(cleaned.text)
        existing = repo.get_chapter_by_ordinal(work_id, raw.ordinal)

        if existing is not None and existing.content_hash == content_hash:
            report.chapters_skipped += 1
            continue

        if existing is not None and existing.id is not None:
            repo.delete_chapter(existing.id)  # content changed; chunks cascade away
            report.chapters_updated += 1
        else:
            report.chapters_added += 1

        chapter_id = repo.add_chapter(
            Chapter(
                work_id=work_id,
                ordinal=raw.ordinal,
                title=raw.title,
                clean_text=cleaned.text,
                content_hash=content_hash,
                source_path=raw.source_path,
            )
        )

        for cspan in chunk_chapter(cleaned.text, cfg.chunking):
            repo.add_chunk(
                Chunk(
                    chapter_id=chapter_id,
                    work_id=work_id,
                    ordinal=cspan.ordinal,
                    char_start=cspan.char_start,
                    char_end=cspan.char_end,
                    text=cspan.text,
                    content_hash=_sha256(cspan.text),
                )
            )
            report.chunks_added += 1

    return report
