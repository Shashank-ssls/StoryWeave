# R2 — Stage-0 cleaner audit

**What R2 does.** Hardens the Stage-0 cleaner so watermark junk and look-alike letters
cannot become "names", and so quote marks keep their meaning. Ordered pipeline, each step
a small pure function with its own tests: NFKC → homoglyph folding → watermark removal
(tags, then domain tokens) → quote straightening (kind preserved) → whitespace/paragraph
normalisation.

| field | value |
| --- | --- |
| date | 2026-09-28 |
| branch | `retrofit/v2-core`, phase R2 (run after R1; no R3 work had started) |
| audit tool | `tools/cleaner_audit.py` (read-only) |
| log, verbatim | `evidence/retrofit/logs/R2_cleaner_audit.log` |

Every figure below is **[MEASURED]** unless marked **[NOT MEASURED]** with its reason.

---

## 1. The headline: R2 changes nothing on the measured corpus — [MEASURED]

```
=== the-ninth-house ===
  chapters measured        : 40
  clean-text characters    : 65,255
  watermark hits (total)   : 0
    tag markup stripped    : none
    domain tokens removed  : none
  homoglyphs folded        : none
  residual Greek/Cyrillic  : none
  cruft lines stripped     : 0
  clean text changed by R2 : 0 of 40 chapters

=== the-hollow-crown ===
  chapters measured        : 4
  clean-text characters    : 4,647
  watermark hits (total)   : 0
    tag markup stripped    : none
    domain tokens removed  : none
  homoglyphs folded        : none
  residual Greek/Cyrillic  : none
  cruft lines stripped     : 2
  clean text changed by R2 : 0 of 4 chapters

residual Greek/Cyrillic code points across all measured corpora: 0
```

**0 watermark hits and 0 homoglyphs across all 44 committed chapters, and the clean text
of every single chapter is byte-identical to what the pre-R2 cleaner produced.** The audit
proves this directly: it cleans each chapter twice, once with all four R2 steps enabled and
once with them disabled, and compares.

The only non-ASCII character in the Ninth House source text is U+2014 EM DASH, 117
occurrences — no curly quotes, no Greek, no Cyrillic, no watermarks.

Three consequences worth stating:

1. **R2 is a no-op on The Ninth House, now measured rather than assumed.** The earlier
   judgement that R2 could be deferred because "the measured corpus is clean text" was
   correct, and this is the evidence for it.
2. **R3's re-extraction is unaffected.** Because clean text is unchanged, character offsets
   are unchanged, so entity/mention offsets from a post-R2 ingest are directly comparable
   to the frozen v1 baseline. R2 cannot be blamed for, or credited with, any R3 delta.
3. **Hollow Crown is untouched** (rule I2): its 4 chapters clean identically, and its 2
   cruft lines are stripped by its own pre-existing `cruft_patterns`, not by anything new.

## 2. Shadow Slave — [NOT MEASURED]

```
=== shadow-slave ===
  NOT MEASURED: no chapter files in data/samples/shadow-slave - this corpus' text is
  gitignored (data/raw/) and is not present on this machine
```

`data/raw/` contains only `.gitkeep`. Shadow Slave's text — the corpus the watermarks were
actually *found* in — is not on this machine, so its watermark hit count **cannot be
measured and is not estimated here**. `data/samples/shadow-slave/` holds only its
`storyweave.toml`.

To get the number, restore the text to `data/samples/shadow-slave/ch*.txt` (or
`data/raw/`) and run `python tools/cleaner_audit.py --corpus data/samples/shadow-slave`.
**R2 must be re-audited before Shadow Slave is ever re-extracted** — that is the ordering
constraint this phase exists to satisfy.

## 3. Instead: an injection round-trip check at corpus scale — [MEASURED]

A no-op audit cannot demonstrate that the cleaner *works*, and the corpus that would
demonstrate it is absent. So `--inject-check` splices the real watermark forms into every
paragraph of every committed chapter, cleans it, and requires the result to be
byte-identical to the clean text of the un-injected chapter:

```
=== injection round-trip check ===
  shadow-slave: skipped (no text)
  the-hollow-crown: 4 chapters, 69 watermark hits removed -> OK
  the-ninth-house: 40 chapters, 994 watermark hits removed -> OK
```

**1,063 watermark hits removed across 44 chapters, with byte-identical round-trip and zero
failures.** The injected forms are the four the sites actually emit: `ndαsnοvεl.cοm `
(Greek α/ο/ε), `novelsnext.com `, `<novelsnext>`, `</novelsnext>`.

This is a scale check on real prose, not a unit test, and it is the strongest available
substitute for the absent corpus. It is pinned by
`test_injection_round_trip_on_the_real_corpus`, so a future change that quietly breaks the
cleaner fails the suite rather than the audit reporting a cheerful `OK`.

## 4. Unicode audit — [MEASURED]

**Zero Greek or Cyrillic code points remain in the clean text of any measured corpus.**

Folding is deliberately limited to characters the Unicode confusables data treats as
look-alikes of an ASCII letter (54 entries; the table is in
`storyweave/ingest/homoglyphs.py`, every row annotated with its code point and Unicode
name). Greek and Cyrillic letters with **no** Latin twin — `π`, `λ`, `ς`, `ж`, `ю` — are
**not** folded, because a book that genuinely quotes Greek or Russian must not be mangled.
Those are *reported* by `residual_confusable_script`, so a real Greek quotation shows up as
a decision to make rather than as silent corruption. On this corpus the residual count is
0, and `test_non_confusable_greek_is_left_alone_and_reported` pins the behaviour:
`πολις` cleans to `πoλiς` — omicron and iota folded, pi/lambda/final-sigma preserved and
reported.

## 5. Why the step order is load-bearing — [MEASURED]

Homoglyph folding (step 2) must run **before** watermark removal (step 3). Unfolded,
`ndαsnοvεl.cοm` is not the string `ndasnovel.com` and no plain regex matches it. This is
not asserted, it is tested both ways:

- `test_watermark_domain_token_is_removed_from_real_string` — with folding on, the real
  string cleans to exactly `Morgan looked away from Nephis`, 1 watermark hit, and the three
  folded code points (α×1, ο×2, ε×1) are reported.
- `test_watermark_survives_without_folding_which_is_why_order_matters` — with
  `fold_homoglyphs=False`, the same input yields **0** watermark hits. The failure mode is
  demonstrated, not described.

## 6. Decisions taken, and why

**Watermark tags strip the markup and KEEP the inner text.** `<novelsnext>` wrappers
enclose real story prose — that is precisely what defeats a cleaner that deletes the whole
block, and deleting it would delete part of the chapter. So `even tone:<novelsnext> I think
you should take a look at </novelsnext>` cleans to `even tone: I think you should take a
look at`: no tag text remains, the sentence survives. Tag names are per-work data
(`cleaner.watermark_tags`, default `novelsnext`/`novelnext`/`novelbin`/`novelfire`).

**Quote straightening preserves kind, and brackets are never touched.** `“ ”` → `"`,
`‘ ’` → `'`, and a single quote is *never* promoted to a double one — `’` is also the
apostrophe in `don’t`, and in this corpus single quotes mark thought while doubles mark
speech, so merging them would destroy a distinction the reader relies on. `[ ]` is absent
from the table on purpose: `[Can you hear me?]` is a system message and its brackets are
content. Both pinned by tests.

**The domain pattern requires a real TLD.** `\b\w*(?:novel|novels)\w*\.(?:com|net|org)\b`,
so `She read the novel twice, then wrote a novelistic reply about novels.` is returned
unchanged with 0 hits (`test_a_normal_sentence_containing_novel_is_unchanged`), while
`novels.net Morgan` loses only the domain. The leading `\w*` is intentionally star, not
plus, so a bare `novels.net` matches as well as `ndasnovel.com`.

**Cleaning is idempotent** (`test_cleaning_is_idempotent`): cleaning already-clean text is
a no-op, so a re-ingest cannot drift offsets.

## 7. Offsets and raw text — verified, not rebuilt — [MEASURED]

R2 says to verify the existing design rather than rebuild it. Verified against the frozen
v1 database, read-only:

```
chunk offset invariant  : 163/163 chunks satisfy clean_text[start:end] == text;    violations=0
mention offset invariant: 887/887 mentions satisfy clean_text[start:end] == surface; violations=0
```

All offsets index into clean text, as designed. The raw source files are read and never
written (`git status data/samples/` is clean after the full audit), and `chapters` stores
the cleaned copy while the source file on disk remains the untouched original, so every
folded code point is recoverable.

## 8. Gates

| gate | result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `mypy` | `Success: no issues found in 81 source files` |
| `pytest` | `185 passed, 6 skipped` (169 before R2; 16 new cleaner tests) |
| `tools/check_local_env.py` | `PASS: all 10 checks are on the project drive.` (both venvs) |

## 9. Stop conditions — none tripped

| stop condition | status |
| --- | --- |
| `tools/check_local_env.py` fails | passes in both venvs |
| any fence violation | no fence, schema or query code touched in R2 |
| any alias over-merge / SAME_AS false positive | no clustering or identity code touched |
| ch40 default graph node count | unchanged — R2 does not alter the graph |
| R5 precision | not applicable |
