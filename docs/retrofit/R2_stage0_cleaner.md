# R2 — Stage 0 text cleaner hardening

**Goal:** stop watermark junk and look-alike letters from becoming "names", and
keep quote marks meaningful. Needed before any re-extraction.

## Paste into Claude Code
```
Read CLAUDE.md and docs/retrofit/R2_stage0_cleaner.md. Phase R2. R1 is complete.
```

## Tasks (in `storyweave/ingest/cleaner.py`)
Apply in this order, each a small pure function with its own tests:
1. Unicode NFKC.
2. Homoglyph folding: Greek/Cyrillic look-alikes → Latin (e.g. U+03B1 α→a,
   U+03BF ο→o, U+03B5 ε→e, Cyrillic а/е/о/с/р/х). Table in code, documented.
3. Watermark strip: configured tag patterns (`<novelsnext>…</novelsnext>`
   removes tags, keeps inner text if it is story text — make it configurable in
   `storyweave.toml` as `cleaner.watermark_tags`), then a domain-like token regex
   applied AFTER folding (e.g. `\b\w+(novel|novels)\w*\.(com|net|org)\b`).
4. Curly → straight quotes **but preserve kind**: `“ ”` → `"`, `‘ ’` → `'`.
   Never turn `'` into `"`. Never strip `[ ]`.
5. Whitespace/paragraph normalisation; paragraph IDs assigned after cleaning.
Store raw text untouched; all offsets index into clean text (already v1 design —
verify, don't rebuild).

## Tests (use real strings)
- `ndαsnοvεl.cοm Morgan looked away from Nephis` → `Morgan looked away from Nephis`
- `even tone:<novelsnext> I think you should take a look at </novelsnext>` →
  no tag text remains
- `'I hate this,' he thought.` keeps single quotes
- `[Can you hear me?]` keeps brackets
- False-removal guard: a normal sentence containing "novel" is unchanged

## Acceptance
- [ ] All tests pass; count of watermark hits removed on the 40 Ninth House
      chapters and on `data/samples/shadow-slave` logged to
      `evidence/retrofit/R2_cleaner_audit.md` [MEASURED]
- [ ] Unicode audit: zero Greek/Cyrillic code points left in clean text
- [ ] Green gates, commit `feat(retrofit): R2 stage-0 cleaner`, push
