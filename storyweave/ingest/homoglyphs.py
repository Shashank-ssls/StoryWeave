"""Homoglyph folding: Greek/Cyrillic look-alike letters -> their Latin twins.

Scraped web-novel text is routinely watermarked by swapping a few Latin letters for
visually identical Greek or Cyrillic ones, so that a copied paragraph carries a
traceable fingerprint and a naive cleaner cannot regex the watermark out. A real
example from the Shadow Slave sample, byte for byte:

    ndαsnοvεl.cοm       (U+03B1 alpha, U+03BF omicron, U+03B5 epsilon)

To a reader that is ``ndasnovel.com``. To the tokenizer it is a brand-new word, so
GLiNER dutifully proposes it as a proper noun and it becomes an "entity". Folding
these back to Latin BEFORE the watermark patterns run is what lets one plain regex
catch every spelling of the same watermark.

Scope and safety
----------------
The table is deliberately limited to characters the Unicode confusables data treats
as look-alikes of an ASCII letter. Greek and Cyrillic letters with no Latin twin
(``π``, ``ж``, ``ю``, ``ы`` …) are **not** in the table and are left untouched: a
book that genuinely quotes Greek or Russian must not be mangled. Instead they are
reported — ``residual_confusable_script`` finds anything left over, which is what the
R2 audit asserts against, so a real Greek quotation shows up as a finding to decide
about rather than as silent corruption.

This is lossy by design and only ever applied to ``clean_text``. The raw text is
stored untouched, so the original code points are always recoverable.
"""

from __future__ import annotations

import unicodedata
from collections import Counter

# Greek -> Latin. Each entry is a character whose rendered shape is the Latin letter.
_GREEK: dict[str, str] = {
    "Α": "A",  # Α GREEK CAPITAL LETTER ALPHA
    "Β": "B",  # Β BETA
    "Ε": "E",  # Ε EPSILON
    "Ζ": "Z",  # Ζ ZETA
    "Η": "H",  # Η ETA
    "Ι": "I",  # Ι IOTA
    "Κ": "K",  # Κ KAPPA
    "Μ": "M",  # Μ MU
    "Ν": "N",  # Ν NU
    "Ο": "O",  # Ο OMICRON
    "Ρ": "P",  # Ρ RHO
    "Τ": "T",  # Τ TAU
    "Υ": "Y",  # Υ UPSILON
    "Χ": "X",  # Χ CHI
    "α": "a",  # α ALPHA          — seen in ndαsnοvεl.cοm
    "γ": "y",  # γ GAMMA
    "ε": "e",  # ε EPSILON        — seen in ndαsnοvεl.cοm
    "η": "n",  # η ETA
    "ι": "i",  # ι IOTA
    "κ": "k",  # κ KAPPA
    "ν": "v",  # ν NU
    "ο": "o",  # ο OMICRON        — seen in ndαsnοvεl.cοm
    "ρ": "p",  # ρ RHO
    "τ": "t",  # τ TAU
    "υ": "u",  # υ UPSILON
    "χ": "x",  # χ CHI
}

# Cyrillic -> Latin. The classic phishing set; every one of these is pixel-identical
# to its Latin twin in almost every font.
_CYRILLIC: dict[str, str] = {
    "А": "A",  # А CYRILLIC CAPITAL LETTER A
    "В": "B",  # В VE
    "Е": "E",  # Е IE
    "З": "3",  # З ZE  (renders as the digit three)
    "К": "K",  # К KA
    "М": "M",  # М EM
    "Н": "H",  # Н EN
    "О": "O",  # О O
    "Р": "P",  # Р ER
    "С": "C",  # С ES
    "Т": "T",  # Т TE
    "У": "Y",  # У U
    "Х": "X",  # Х HA
    "а": "a",  # а A
    "е": "e",  # е IE
    "о": "o",  # о O
    "р": "p",  # р ER
    "с": "c",  # с ES
    "у": "y",  # у U
    "х": "x",  # х HA
    "і": "i",  # і BYELORUSSIAN-UKRAINIAN I
    "ї": "i",  # ї YI
    "ј": "j",  # ј JE
    "ѕ": "s",  # ѕ DZE
    "һ": "h",  # һ SHHA
    "ԁ": "d",  # ԁ KOMI DE
    "Ԛ": "Q",  # Ԛ QA
    "Ԝ": "W",  # Ԝ WE
}

HOMOGLYPHS: dict[str, str] = {**_GREEK, **_CYRILLIC}

#: ``str.translate`` table, built once.
_TRANSLATION = str.maketrans(HOMOGLYPHS)

#: Unicode script name prefixes we fold from, used by the residual audit.
_CONFUSABLE_SCRIPTS = ("GREEK", "CYRILLIC")


def fold_homoglyphs(text: str) -> str:
    """Replace every look-alike Greek/Cyrillic letter with its Latin twin."""
    return text.translate(_TRANSLATION)


def count_folded(text: str) -> Counter[str]:
    """How many of each homoglyph `text` contains, for the audit. Does not modify it."""
    return Counter(ch for ch in text if ch in HOMOGLYPHS)


def residual_confusable_script(text: str) -> Counter[str]:
    """Greek/Cyrillic code points still present after folding.

    Non-empty means the text contains a Greek or Cyrillic letter that has no Latin
    look-alike, so folding deliberately left it alone. The R2 audit reports these
    rather than mangling them: a genuine Greek quotation is a content decision, not a
    watermark.
    """
    out: Counter[str] = Counter()
    for ch in text:
        if ch in HOMOGLYPHS or ch.isascii():
            continue
        name = unicodedata.name(ch, "")
        if name.startswith(_CONFUSABLE_SCRIPTS):
            out[ch] += 1
    return out
