"""Phase 1: text cleaning — NFKC, de-hyphenation, cruft logging, paragraphs."""

from __future__ import annotations

from storyweave.ingest.cleaner import clean_text
from storyweave.ingest.work_config import CleaningConfig


def test_nfkc_normalizes_fullwidth() -> None:
    result = clean_text("Ｈｅｌｌｏ")  # full-width latin
    assert result.text == "Hello"


def test_dehyphenate_joins_soft_wrap() -> None:
    on = clean_text("long-\nword here.", CleaningConfig(dehyphenate=True))
    assert "longword here." in on.text
    off = clean_text("long-\nword here.", CleaningConfig(dehyphenate=False))
    assert "longword" not in off.text


def test_cruft_is_stripped_and_logged() -> None:
    cfg = CleaningConfig(cruft_patterns=[r"^\[T/N:"])
    result = clean_text("Real line.\n[T/N: a note]\nMore.", cfg)
    assert "[T/N:" not in result.text
    assert result.removed_lines == ["[T/N: a note]"]
    assert "Real line." in result.text


def test_blank_line_paragraph_mode_collapses_soft_newlines() -> None:
    result = clean_text("Line one.\nstill one.\n\nPara two.")
    assert "Line one. still one." in result.text
    assert "\n\n" in result.text


def test_single_newline_paragraph_mode() -> None:
    cfg = CleaningConfig(single_newline_is_paragraph=True)
    result = clean_text("Line one.\nstill one.", cfg)
    assert result.text == "Line one.\n\nstill one."
