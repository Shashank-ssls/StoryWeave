"""Stage 0 text cleaning: NFKC, homoglyphs, watermarks, quotes, paragraphs.

The retrofit R2 cases below use the REAL strings the watermarks were found as, with the
Greek look-alike letters literally present in the source. Because an editor, shell or
git filter that normalised them to ASCII would make these tests silently vacuous,
``test_the_watermark_fixture_really_contains_greek`` asserts the code points directly
rather than trusting a comment.
"""

from __future__ import annotations

from pathlib import Path

from storyweave.ingest.cleaner import (
    clean_text,
    straighten_quotes,
    strip_watermark_tags,
    strip_watermark_tokens,
)
from storyweave.ingest.homoglyphs import (
    fold_homoglyphs,
    residual_confusable_script,
)
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


# --------------------------------------------------------------------------- #
# Retrofit R2: homoglyph folding, watermark removal, quote kind preservation.
# --------------------------------------------------------------------------- #

# "ndasnovel.com" with GREEK SMALL ALPHA / OMICRON / EPSILON swapped in for a, o, e.
WATERMARKED = "ndαsnοvεl.cοm Morgan looked away from Nephis"
ALPHA, OMICRON, EPSILON = "α", "ο", "ε"


def test_the_watermark_fixture_really_contains_greek() -> None:
    """Guards every test below: if the fixture were ASCII-folded they would pass vacuously."""
    assert ALPHA in WATERMARKED
    assert WATERMARKED.count(OMICRON) == 2
    assert EPSILON in WATERMARKED
    assert not WATERMARKED.isascii()


def test_folding_rewrites_the_real_watermark_to_latin() -> None:
    assert fold_homoglyphs("ndαsnοvεl.cοm") == "ndasnovel.com"


def test_watermark_domain_token_is_removed_from_real_string() -> None:
    result = clean_text(WATERMARKED)
    assert result.text == "Morgan looked away from Nephis"
    assert result.watermark_hits == 1
    assert result.watermark_tokens_removed == {"ndasnovel.com": 1}
    # The three folded code points are reported, not silently swallowed.
    assert dict(result.homoglyphs_folded) == {"α": 1, "ο": 2, "ε": 1}


def test_watermark_survives_without_folding_which_is_why_order_matters() -> None:
    """Proof that step 2 must precede step 3: unfolded, the same regex cannot match."""
    result = clean_text(WATERMARKED, CleaningConfig(fold_homoglyphs=False))
    assert result.watermark_hits == 0
    assert "Morgan looked away from Nephis" in result.text


def test_watermark_tag_markup_goes_and_inner_story_text_stays() -> None:
    raw = "even tone:<novelsnext> I think you should take a look at </novelsnext>"
    result = clean_text(raw)
    assert "novelsnext" not in result.text
    assert "<" not in result.text and ">" not in result.text
    # The inner text is story prose - deleting the block would delete the chapter.
    assert "I think you should take a look at" in result.text
    assert result.text.startswith("even tone:")
    assert result.watermark_tags_removed == {"novelsnext": 2}


def test_watermark_tags_are_configurable_per_work() -> None:
    raw = "he said<somesite>hello</somesite>"
    assert "somesite" in clean_text(raw).text  # not in the default list
    cfg = CleaningConfig(watermark_tags=["somesite"])
    assert clean_text(raw, cfg).text == "he saidhello"


def test_single_quotes_are_preserved_as_single_quotes() -> None:
    raw = "‘I hate this,’ he thought."
    result = clean_text(raw)
    assert result.text == "'I hate this,' he thought."
    assert '"' not in result.text


def test_double_quotes_become_straight_doubles() -> None:
    result = clean_text("“Who goes there?” she called.")
    assert result.text == '"Who goes there?" she called.'


def test_apostrophe_is_not_promoted_to_a_double_quote() -> None:
    assert straighten_quotes("don’t") == "don't"


def test_brackets_are_never_stripped() -> None:
    result = clean_text("[Can you hear me?]")
    assert result.text == "[Can you hear me?]"


def test_a_normal_sentence_containing_novel_is_unchanged() -> None:
    """False-removal guard: the pattern needs a real TLD, not the word 'novel'."""
    raw = "She read the novel twice, then wrote a novelistic reply about novels."
    result = clean_text(raw)
    assert result.text == raw
    assert result.watermark_hits == 0


def test_novel_domain_without_leading_word_still_matches() -> None:
    text, hits = strip_watermark_tokens(
        "novels.net Morgan", CleaningConfig().watermark_token_patterns
    )
    assert text.strip() == "Morgan"
    assert hits == {"novels.net": 1}


def test_tag_stripper_handles_self_closing_and_spaced_forms() -> None:
    text, hits = strip_watermark_tags("a<novelsnext/>b</ novelsnext >c", ["novelsnext"])
    assert text == "abc"
    assert hits == {"novelsnext": 2}


def test_non_confusable_greek_is_left_alone_and_reported() -> None:
    """A real Greek quotation is a content decision, not a watermark: do not mangle it."""
    raw = "the word πολις was carved there"
    result = clean_text(raw)
    # Omicron and iota DO have Latin twins, so they were folded to o and i...
    assert "ο" not in result.text and "ι" not in result.text
    assert result.text == "the word πoλiς was carved there"
    # ...but pi, lambda and final sigma have none: they survive untouched, and the audit
    # surfaces them as a decision to make rather than as silent corruption.
    assert set(residual_confusable_script(result.text)) == {"π", "λ", "ς"}


def test_cleaning_is_idempotent() -> None:
    """Cleaning already-clean text must be a no-op, or offsets could drift on re-ingest."""
    once = clean_text(WATERMARKED).text
    assert clean_text(once).text == once


def test_injection_round_trip_on_the_real_corpus() -> None:
    """End-to-end cover for tools/cleaner_audit.py's scale check.

    Without this, a broken audit tool would happily report OK. Splicing the real
    watermark forms into the committed Hollow Crown chapters must remove every one of
    them and land back on byte-identical clean text.
    """
    from tools.cleaner_audit import inject_check

    corpus = Path(__file__).resolve().parents[1] / "data" / "samples" / "the-hollow-crown"
    checked, hits, failures = inject_check(corpus)
    assert checked == 4
    assert hits > 0
    assert failures == []
