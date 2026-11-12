"""Stage-0 cleaner audit (retrofit R2): what the cleaner removes from a real corpus.

Runs `ingest/cleaner.clean_text` over every chapter file of a work and reports, per
corpus: watermark tags stripped, watermark tokens removed, homoglyphs folded, residual
Greek/Cyrillic code points left in the clean text, and whether the clean text changed at
all versus the pre-R2 cleaner. Read-only — it writes nothing but its own report.

    python tools/cleaner_audit.py                                  # every sample corpus
    python tools/cleaner_audit.py --corpus data/samples/shadow-slave

A corpus with no chapter files is reported as NOT MEASURED with the reason, never as a
zero: zero removals and "no text to measure" are different facts.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.ingest.cleaner import clean_text  # noqa: E402
from storyweave.ingest.homoglyphs import residual_confusable_script  # noqa: E402
from storyweave.ingest.work_config import CleaningConfig, load_work_config  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES = REPO_ROOT / "data" / "samples"


@dataclass
class CorpusAudit:
    name: str
    path: Path
    chapters: int = 0
    chars: int = 0
    measured: bool = True
    reason: str = ""
    tags: Counter[str] = field(default_factory=Counter)
    tokens: Counter[str] = field(default_factory=Counter)
    homoglyphs: Counter[str] = field(default_factory=Counter)
    residual: Counter[str] = field(default_factory=Counter)
    cruft_lines: int = 0
    #: chapters whose clean text differs from the pre-R2 cleaner's output
    changed_chapters: list[str] = field(default_factory=list)

    @property
    def watermark_hits(self) -> int:
        return sum(self.tags.values()) + sum(self.tokens.values())


def _pre_r2_config(cfg: CleaningConfig) -> CleaningConfig:
    """The same config with every R2 step disabled, to prove what R2 changed."""
    return cfg.model_copy(
        update={
            "fold_homoglyphs": False,
            "watermark_tags": [],
            "watermark_token_patterns": [],
            "straighten_quotes": False,
        }
    )


def audit_corpus(path: Path) -> CorpusAudit:
    audit = CorpusAudit(name=path.name, path=path)
    files = sorted(path.glob("ch*.txt"))
    if not files:
        audit.measured = False
        audit.reason = (
            f"no chapter files in {path} - this corpus' text is gitignored "
            "(data/raw/) and is not present on this machine"
        )
        return audit

    cfg = load_work_config(path / "storyweave.toml").cleaning
    pre = _pre_r2_config(cfg)
    for f in files:
        raw = f.read_text(encoding="utf-8")
        result = clean_text(raw, cfg)
        audit.chapters += 1
        audit.chars += len(result.text)
        audit.tags.update(result.watermark_tags_removed)
        audit.tokens.update(result.watermark_tokens_removed)
        audit.homoglyphs.update(result.homoglyphs_folded)
        audit.residual.update(residual_confusable_script(result.text))
        audit.cruft_lines += len(result.removed_lines)
        if clean_text(raw, pre).text != result.text:
            audit.changed_chapters.append(f.name)
    return audit


# Watermark forms as the scraper sites actually emit them, used by --inject-check.
# The Greek letters are literal on purpose; see tests/test_cleaner.py for why.
INJECTED_FORMS: tuple[str, ...] = (
    "ndαsnοvεl.cοm ",
    "novelsnext.com ",
    "<novelsnext>",
    "</novelsnext>",
)


def inject_check(path: Path) -> tuple[int, int, list[str]]:
    """Inject real watermark forms into a clean corpus and prove they round-trip out.

    Answers the question the absent Shadow Slave text leaves open: does the cleaner
    actually remove these at corpus scale, not just in a unit test? For each chapter,
    the watermark forms are spliced into the raw text at paragraph starts, the chapter
    is cleaned, and the result must equal the clean text of the un-injected chapter.

    Returns (chapters checked, watermark hits removed, chapters that did not round-trip).
    """
    files = sorted(path.glob("ch*.txt"))
    cfg = load_work_config(path / "storyweave.toml").cleaning
    checked = 0
    hits = 0
    failures: list[str] = []
    for f in files:
        raw = f.read_text(encoding="utf-8")
        expected = clean_text(raw, cfg).text
        lines = raw.split("\n")
        dirty = "\n".join(
            INJECTED_FORMS[i % len(INJECTED_FORMS)] + line if line.strip() else line
            for i, line in enumerate(lines)
        )
        result = clean_text(dirty, cfg)
        checked += 1
        hits += result.watermark_hits
        if result.text != expected:
            failures.append(f.name)
    return checked, hits, failures


def _describe(counter: Counter[str]) -> str:
    if not counter:
        return "none"
    return ", ".join(
        f"U+{ord(ch):04X} {unicodedata.name(ch, '?')} x{n}" for ch, n in counter.most_common()
    )


def report(audits: Sequence[CorpusAudit]) -> str:
    out: list[str] = []
    for a in audits:
        out.append(f"=== {a.name} ({a.path}) ===")
        if not a.measured:
            out.append(f"  NOT MEASURED: {a.reason}")
            out.append("")
            continue
        out.append(f"  chapters measured        : {a.chapters}")
        out.append(f"  clean-text characters    : {a.chars:,}")
        out.append(f"  watermark hits (total)   : {a.watermark_hits}")
        out.append(f"    tag markup stripped    : {dict(a.tags) or 'none'}")
        out.append(f"    domain tokens removed  : {dict(a.tokens) or 'none'}")
        out.append(f"  homoglyphs folded        : {_describe(a.homoglyphs)}")
        out.append(f"  residual Greek/Cyrillic  : {_describe(a.residual)}")
        out.append(f"  cruft lines stripped     : {a.cruft_lines}")
        changed = a.changed_chapters
        out.append(
            f"  clean text changed by R2 : {len(changed)} of {a.chapters} chapters"
            + (f" ({', '.join(changed[:6])}{'...' if len(changed) > 6 else ''})" if changed else "")
        )
        out.append("")
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--inject-check",
        action="store_true",
        help="also splice real watermark forms into each clean chapter and prove they "
        "round-trip back out (scale check for corpora whose own text is absent)",
    )
    ap.add_argument(
        "--corpus",
        action="append",
        type=Path,
        help="a corpus directory (repeatable); default: every directory under data/samples",
    )
    args = ap.parse_args(argv)
    paths = args.corpus or sorted(p for p in SAMPLES.iterdir() if p.is_dir())
    audits = [audit_corpus(p) for p in paths]
    print(report(audits))

    residual_total = sum(sum(a.residual.values()) for a in audits if a.measured)
    print(f"residual Greek/Cyrillic code points across all measured corpora: {residual_total}")

    failed = 0
    if args.inject_check:
        print("\n=== injection round-trip check ===")
        for a in audits:
            if not a.measured:
                print(f"  {a.name}: skipped (no text)")
                continue
            checked, hits, failures = inject_check(a.path)
            status = "OK" if not failures else f"FAIL on {failures}"
            print(f"  {a.name}: {checked} chapters, {hits} watermark hits removed -> {status}")
            failed += len(failures)

    return 1 if (residual_total or failed) else 0


if __name__ == "__main__":
    sys.exit(main())
