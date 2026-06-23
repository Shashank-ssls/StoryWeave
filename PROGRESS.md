# PROGRESS — StoryWeave

> Live status. Resume cold from this file. Read with CLAUDE.md + SPEC.md each session.

## Current phase
**Phase 7c — Tier-3 IDENTITY inference (the showcase).** Status: **green & pushed.** Citation-gated, reveal-respecting identity edges (SAME_AS/ALIAS/SECRET_IDENTITY/REINCARNATION/TRANSMIGRATED_INTO) wired behind `llm_enabled` (OFF by default). Deterministic flip-at-gold + no-citation-no-edge regressions green in the light venv; the live model is reported, non-gating. **Identity primary refined to CPU `qwen2.5:7b`** (the full multi-step task re-separates the models — see below). NO Tier-2 cleanup (7d parked). **Private LotM ch1 validation run DONE** (report-only, nothing mutated — see Measurement-run section). **Next (decided): `TRANSMIGRATED_INTO` citation-production fix → re-measure entailment gap on a multi-chapter drop → (maybe) NLI → 7d → Phase 8** (Phase 8 waits until reveal timing is trustworthy). See In-progress / next + Known issues.

## Measurement run — private LotM ch1 validation (Phase 7c, REPORT-ONLY, nothing mutated)
First contact of the 7c identity machinery with prose not in our hand-labeled sample. **Report only** — drove the real `LlmIdentityModel.infer` directly over the chapter (no DB written, no edge, no schema/product change; throwaway scratch probe deleted). **LotM stayed strictly local** (gitignored `data/raw/`, never committed/quoted). Weights on F:, C: clean (keypair only), Ollama stopped at end.
- **Scope caveat (important): only ONE chapter was available (LotM ch1).** That bounds the run: Q1 (gate holds) and Q3 (over-merge) are answerable; Q2 (reveal-TIMING / EARLY spoiler-shift) is **not** — with a single chapter the only gold is k=1, so `first_yes_k` can only be 1 or MISS, and an EARLY flip has no earlier chapter to occur in. Multi-chapter drop needed to measure Q2 and to make Q3 a rate.
- **Cases (hand-labeled from ch1).** Positive = the SPEC flagship: Zhou Mingrui transmigrated INTO Klein Moretti's body, reader learns it in ch1 → `TRANSMIGRATED_INTO`, gold k=1. Controls = distinct co-occurring named entities that must not merge. Models: CPU `qwen2.5:7b` (primary, run ×2 — **identical**) + GPU `llama3.2:3b` (fallback, ×1).

  | case | model | expected | same? | relation | citation in-range? | verdict | citation class |
  |---|---|---|---|---|---|---|---|
  | ZhouMingrui↔Klein | qwen2.5:7b | TRANSMIGRATED_INTO@1 | YES | REINCARNATION | **NO** | **MISS (fail-closed)** | fabricated (echoed the instruction) |
  | ZhouMingrui↔Klein | llama3.2:3b | TRANSMIGRATED_INTO@1 | YES | SECRET_IDENTITY | **NO** | **MISS (fail-closed)** | absent (empty clue) |
  | Klein↔EvernightGoddess | both | NOT same | NO | — | — | **PASS (control)** | n/a |
  | ZhouMingrui↔EvernightGoddess | both | NOT same | NO | — | — | **PASS (control)** | n/a |
  | Klein↔Hermes-language (junk) | qwen2.5:7b | NOT same | YES | SAME_AS | **NO** | rejected → no edge | fabricated (echoed the instruction) |
  | Klein↔Hermes-language (junk) | llama3.2:3b | NOT same | NO | — | — | **PASS** | n/a |

- **Q1 — citation gate / fail-closed rate:** the gate's SAFETY held perfectly — every `same=YES` (1 true + 1 junk on 7B; 1 true on 3B) was rejected for a non-passage citation, so **zero edges written, zero over-merges survived**. But the COST landed: the TRUE reveal was dropped too — **fail-closed on 1/1 true merges on both models**. On this prose the gate is currently *safe-but-silent*: it writes nothing, true or false.
- **Q2 — reveal timing:** `first_yes_k = None` (MISS) for the transmigration on both models (the YES was citation-rejected). No reveal landed, so no spoiler-shift could be observed; EARLY is structurally unobservable with one chapter. **Q2 effectively unmeasured.**
- **Q3 — entailment-gap bite (the headline):** **real-but-irrelevant over-merge rate = 0.** Of every asserted YES, NONE carried a real-but-irrelevant in-passage citation — ALL carried fabricated/empty citations, all caught by the existence gate. **The entailment-relevance gap did NOT bite on ch1 — it is MASKED by a more fundamental upstream failure.**
- **Negative control:** PASS — no over-merge edge survived (both models reject the Evernight-Goddess pairs; 3B also rejects the Hermes-language junk; 7B's junk-YES was citation-rejected).
- **THE DOMINANT MEASURED FAILURE (not the one anticipated):** on real LotM prose both models **fail to quote the passage** for the transmigration reveal — 7B echoes the instruction sentence as its "clue", 3B returns an empty clue — so the existence gate fail-closes on the TRUE reveal. **Root cause:** the system prompt demands a single clause that names BOTH entities, but LotM conveys the transmigration via inherited memories + the mirror, never co-stating "Zhou Mingrui" and "Klein Moretti" in one clause. With nothing to bind to, the both-names citation rule has no satisfying quote → degenerate output. **This is design-input (c) confirmed on real prose:** even with both names present, `TRANSMIGRATED_INTO` is a single-body / two-names-never-co-stated relation, so a two-named-clause demand cannot fire.
- **SIZING THE NEXT FIX (the deliverable):** the heavy **NLI/entailment-relevance verifier is NOT yet justified** — the gap it targets did not bite (0 real-but-irrelevant over-merges) and is masked. The justified, **lighter** fix first: relax the both-names citation demand for transmigration/memory-flood reveals — accept a citation that evidences the transmigration MECHANISM (waking in another body / inherited memories), or adopt the single-entity-property representation of design-input (c) for `TRANSMIGRATED_INTO`. **Hard caveat — ONE chapter, small N:** the entailment gap is **unmeasured here, not disproven**; it can only bite on reveals that DO co-name both entities in one clause (later secret-identity/alias cases, e.g. Klein⇄persona names). **Re-measure Q3 on a multi-chapter drop with such co-naming reveals before sizing any NLI fix.**
- **ONE-LINE VERDICT:** on LotM ch1 the entailment gap did NOT bite (0 over-merges); a more basic **citation-production failure** dominates (both models won't quote the passage for the transmigration reveal → existence gate fail-closes on the TRUE reveal). Next session's first fix is the **transmigration citation rule / single-entity representation (light, design-input-c)**, NOT the heavy NLI check — and a **multi-chapter co-naming reveal set is required** before the entailment gap can actually be measured.

## Done (Phase 7c — Tier-3 identity inference)
The showcase, and still pure enhancement (rules #4/#5): with `llm_enabled=False` (default) `infer_identities` produces nothing, writes nothing, constructs no client, opens no socket — the Tier-1/Tier-2 floor + the reveal fence stand intact. New module `nlp/identity.py`; CLI `storyweave identity <slug> [--model --config --db]`; knobs in `WorkConfig.identity` (`candidate_types`, `max_candidate_pairs`) — data, not code. **No schema change** (`tier=3`, `method='llm'` already in the Phase-0 CHECK constraints); flows through the existing `edges` table → `query/fence.py` unchanged (Phase 5 already fences identity edges).
- **The load-bearing rule, as production code:** an identity edge's `revealed_chapter` = the smallest k at which the model confirms the identity from chapters 1..k ONLY, **backed by a quoted clause that actually occurs in chapters 1..k.** The Phase-7b addendum's citation margin is the PRODUCTION mechanism: the model must emit a supporting quote; `citation_in_range` verifies it; a `same=true` with no valid in-range citation is **rejected and counted** (`citations_rejected`) so a fail-closed is observably distinct from "no identity found".
- **Reveal computation = the addendum sweep, now production:** for a candidate pair of canonical nodes, sweep k=1..last feeding only ch1..k; for EACH Tier-3 relation confirmed with a verified citation, write one edge at its smallest-k. A pair may carry **layered reveals** (Wren==Caelum is SECRET_IDENTITY at ch2 AND TRANSMIGRATED_INTO at ch4 — the LotM-style showcase). Anchor-don't-invent (7a rule): head/tail re-ground to floor nodes; **identity is an EDGE, never a node collapse** (the slider still shows two nodes with a blooming edge); an unanchored span yields no edge and no new node.
- **Gold reveal chapters (fixed by the 7b addendum, confirmed against the text), the regression targets:** SECRET_IDENTITY Wren==Caelum **k=2** ("Wren was Caelum"), ALIAS Gray Sparrow==Lady Veris **k=3** ("…were the same person"), TRANSMIGRATED_INTO **k=4** ("an older soul had been poured into the drowned prince"). The (Wren,Caelum) pair carries the secret-identity (k2) and transmigration (k4) reveals; (Sparrow,Veris) carries the alias (k3).
- **Citation match rule (decided + documented):** **normalized containment** — NFKC + casefold + strip punctuation + collapse whitespace (mirrors the ingest cleaner's NFKC space), `clue` must occur in the fed ch1..k text, ≥8 normalized chars. Chosen over a stricter "the quote must name BOTH entities" rule because that **fails closed on the actual sample**: the live model cites *real but vaguely-phrased* clauses near the reveal (e.g. it confirmed Wren==Caelum quoting "He had not drowned; he had washed up…" not the clean "Wren was Caelum"), so a both-names gate would reject even the correct SECRET_IDENTITY. Existence-containment is the reveal-respecting confidence margin; **relevance/entailment is a model problem, not a match-rule problem** (recorded as the next design input).
- **All five in the VOCABULARY; THREE proven, TWO unproven (stated honestly):** the prompt lets the model emit any of the five. SECRET_IDENTITY / ALIAS / TRANSMIGRATED_INTO have gold cases + regression tests on the sample. **SAME_AS and REINCARNATION are schema-and-prompt-ready but UNPROVEN** — no sample exercises them, so there is no gold case and no faked test for them.
- **Deterministic regressions (fake model, light venv, GREEN-GATING) — `tests/test_identity.py` (+10):** **A FLIP-AT-GOLD** — scripted correct per-k verdicts → the three edges land at `revealed_chapter` == 2/3/4 exactly, never earlier (the anti-early-bloom guarantee, permanent); the layered-reveal pair; the fence pass-through (SECRET_IDENTITY hidden at n=1, shown at n=2). **B NO-CITATION-NO-EDGE** — a confident YES whose quote is fabricated → no edge written, `citations_rejected≥1` (distinct from a clean NO). Plus idempotency + tier isolation (Tier-1/Tier-2 survive a Tier-3 rebuild), graceful degradation (model raises → `degraded`, floor intact), disabled-by-default (no edge, no socket — monkeypatched `urlopen` never called), and citation-gate/relation-vocab units. **A live LLM is non-deterministic, so none of these touch a real model.**
- **LIVE reveal-accuracy check (`eval/identity_eval.py`, NON-BLOCKING report — the production analog of the addendum sweep):** drives the REAL model + the same citation gate over the sample; reports `first_yes_k` vs gold (EXACT/EARLY/LATE/MISS) per proven identity + the negative control (Veris≠Dunmore). Measured (skeptical prompt):

  | model | SECRET_IDENTITY (gold 2) | ALIAS (gold 3) | TRANSMIGRATED_INTO (gold 4) | neg ctrl (Veris≠Dunmore) | id-timing (any label) |
  |---|---|---|---|---|---|
  | **qwen2.5:7b (CPU, primary)** | **EXACT (2)** | **EXACT (3)** | MISS | **PASS** | Wren/Caelum EXACT(2), Sparrow/Veris EXACT(3) |
  | llama3.2:3b (GPU, fallback) | **EXACT (2)** | LATE (4) | MISS | PASS* | Wren/Caelum EXACT(2), Sparrow/Veris EXACT(3) |

  **Findings (the live check earned its keep):** (1) **No EARLY flips and EXACT reveal TIMING for both name-pair identities on both models** — the citation margin holds; the whole-phase anti-spoiler-shift property is met in production. (2) **The full identity task re-separates the models:** 7B labels the alias correctly (ALIAS EXACT at gold 3) and robustly holds the negative control; **3B mislabels the alias subtype** (says SECRET_IDENTITY at k3, ALIAS at k4 → strict LATE) and **intermittently over-merges the negative control** (`*` PASS flickered to FAIL across runs — the `/v1` path is unseeded → non-deterministic; 3B confabulated a real-but-irrelevant citation). (3) **TRANSMIGRATED_INTO is MISSED live by both** — in this sample the prior-world soul is unnamed, so transmigration is really a single-entity property, not a two-named edge; the relation stays schema/prompt-ready and deterministically tested, but is not live-confirmable here (recorded, not faked).
- **Model verdict refined on 7c evidence:** the addendum's simple per-pair probe found 3B==7B → it picked 3B for speed; the **full multi-step identity task (relation-typing + skeptical merging + citation) favors the bigger model** — **7c identity primary = CPU `qwen2.5:7b`** (correct subtype, robust control; the config default already is `qwen2.5:7b`), **GPU `llama3.2:3b` = the speed fallback** (`--model llama3.2:3b`). This is the original 7b size-intuition, now backed by real 7c task evidence rather than reasoning.

## Done (Phase 7b ADDENDUM — reveal-chapter-graded identity probe; model choice now evidence-backed)
The 7b gate's single Wren==Caelum clue was too easy (all 4 configs solved it → model pick rested on size reasoning). More importantly, a plain yes/no scorer is blind to the failure that matters for 7c: an **eager-but-correct** model flips to YES one chapter EARLY on a partial clue, producing a right edge with a **spoiler-shifted `revealed_chapter`** (it blooms a chapter too soon). So this addendum (`eval/llm_probe.py`, stdlib-only) **sweeps** k = 1..(gold+1), feeding ONLY chapters 1..k (reveal-respecting), and records `first_yes_k` vs a **gold reveal chapter** = the chapter the *last necessary clue* lands. Identity is probed **per candidate pair** (the form 7c uses), strict-JSON `same_entity`. **No 7c pipeline, no identity edge written; Ollama stopped at the end.**
- **Gold reveal chapters (set by reading the sample, one-line reason each):**
  - **C1 Wren==Caelum → ch2.** ch1 names no link (Caelum is never spoken; only a heron ring + glass-tower visions); ch2 states it outright ("Wren was Caelum… Prince Caelum Veyle"). Early-flip structurally impossible (Caelum absent before ch2).
  - **C2 Sparrow==Veris → ch3.** Neither name appears before ch3; ch3 states "The Gray Sparrow and Lady Veris were the same person" — stated flatly in ONE place, *not* scattered in this sample, so early-flip is also structurally impossible here (reported honestly).
  - **C3 transmigration → ch4.** ch1's Glasswound ("a phenomenon that revealed another world") + ch2's "borrowed memory" are *partial* hints (could be clairvoyance/curse); only ch4's "an older soul had been poured into the drowned prince" confirms an outside soul in this body. **This is the real temporal discriminator** — the only case where a partial clue precedes the confirmation, so EARLY is observable.
  - **C4 NEGATIVE CONTROL: Lady Veris ≠ Ser Dunmore** (two distinct allies who co-occur/interact at the ch4 alliance). Gold = never same; any YES at any k = FAIL (over-merge).
- **THE TABLE — cell = `first_yes_k`:VERDICT** (EXACT=flip at gold, EARLY=before gold/spoiler-shift, LATE=after, MISS=never; ctrl PASS=never merged):

  | model | dev | C1 (gold ch2) | C2 (gold ch3) | C3 (gold ch4) | C4 neg | tok/s | summary |
  |---|---|---|---|---|---|---|---|
  | llama3.2:3b | GPU | 2:**EXACT** | 3:**EXACT** | **2:EARLY** | **PASS** | **59.6** | base: 2 EXACT, C3 2-early, ctrl PASS |
  | qwen2.5:7b | CPU | 2:**EXACT** | 3:**EXACT** | **3:EARLY** | **PASS** | 8.9 | base: 2 EXACT, C3 1-early, ctrl PASS |

  **Base-prompt finding:** per-pair probing makes both alias cases land **EXACT** for both models (the holistic-enumeration under-merge from the first draft is gone), and the negative control **PASSES** for both (no over-merge). The discriminator is **C3 (transmigration): BOTH flip EARLY**, but GPU-3B is *more* eager (flips at ch2, 2 early) than CPU-7B (ch3, 1 early). Both correctly resisted the bare ch1 "another world" visions (k1=n for both) — they bloom on ch2's "borrowed memory", not the ch4 confirmation.
- **THE ONE PROMPT IMPROVEMENT — `--cite` (require a quoted confirming clause before YES) — moved both to ideal:**

  | model | dev | C1 | C2 | C3 | C4 | tok/s | summary |
  |---|---|---|---|---|---|---|---|
  | llama3.2:3b | GPU | 2:EXACT | 3:EXACT | **4:EXACT** | PASS | 59.7 | **3 EXACT, 0 early, ctrl PASS** |
  | qwen2.5:7b | CPU | 2:EXACT | 3:EXACT | **4:EXACT** | PASS | 8.7 | **3 EXACT, 0 early, ctrl PASS** |

  Requiring a quoted clause anchors the transmigration flip to the ch4 "older soul…drowned prince" line (the only place an outside-soul clause exists), moving `first_yes_k` from 2→4 (GPU-3B) and 3→4 (CPU-7B) — both EARLY→**EXACT** — while keeping C1/C2 EXACT and the control PASS. **The actionable lever is the PROMPT (a citation = a confidence margin), not the model size.**
- **VERDICT (reveal-accuracy = WHEN it flips, justified by the table): 7c primary = GPU `llama3.2:3b`; fallback = CPU `qwen2.5:7b`.** Resolving the decision tree: with the citation-anchored prompt GPU-3B lands C1/C2/C3 all **EXACT** and holds the negative control **PASS** → the "switch to GPU-3B (≈6.7× faster, reveal-accuracy-proven)" branch fires. The only place size mattered was the *base* prompt's subtle case (3B 2-early vs 7B 1-early — 7B marginally more conservative), but the correct fix is the prompt, after which 3B equals 7B at all-EXACT and runs **59.7 vs 8.7 tok/s (~6.8×)**. CPU-7B stays the fallback for VRAM-contended/RAM-only runs.
- **7c DESIGN INPUT (recorded, NOT implemented here):** the smallest-k flip rule needs a **confidence margin** before it sets `revealed_chapter`, or it spoiler-shifts on partial clues (both sizes did, by 1–2 chapters, on transmigration under the plain prompt). The margin that worked: **require the model to cite the confirming clause from chapters 1..k before asserting the identity** (equivalently: require YES to hold / clear a probability threshold). 7c should adopt the cite-anchored per-pair prompt and re-validate `revealed_chapter` against a hand-set gold on a real novel before locking.

## Done (Phase 7b — LLM go/no-go gate, NOT a feature)
- **Runner = Ollama** (no-installer zip under gitignored `tools/`, server bound to 127.0.0.1; models cached to F: via `OLLAMA_MODELS=.llm-cache/ollama-models`). Chosen over a custom CUDA llama-cpp-python build because the zip needs no admin/service, bundles CUDA runners that auto partial-offload on the 4 GB card, and exposes an OpenAI-compatible `/v1` endpoint + eval timing (measured tok/s, not guessed). **C: stayed clean** (only a 6 KB Ollama keypair; zero model weights on C:); 6.3 GB of GGUF weights live on F:.
- **GO/NO-GO MATRIX** (`eval/llm_gate.py`, stdlib-only; probe = the Wren==Caelum identity clue across sample ch1+ch2, strict JSON `{"same_entity":[["Wren","Caelum"]]}`, graded on co-reference):

  | model | dev | loads | JSON | correct | tok/s | notes |
  |---|---|---|---|---|---|---|
  | llama3.2:3b | GPU | yes | yes | **YES** | **57.4** | fully offloaded to the 4 GB card |
  | qwen2.5:7b | CPU | yes | yes | **YES** | 8.5 | 0% VRAM (system RAM) |
  | llama3.2:3b | CPU | yes | yes | **YES** | 16.7 | — |
  | qwen2.5:7b | GPU | yes | yes | **YES** | **1.3** | does NOT fit 4 GB → partial-offload thrash |

  **Result = GO.** Honest caveat: the miniature probe is too easy to separate on *accuracy* — even the 3B nails it. The real discriminators are **speed and fit**: GPU-3B fast (57 tok/s); 7B does not fit the 4 GB GPU (1.3 tok/s); CPU-7B slow-but-roomy (8.5 tok/s) and leaves VRAM free for GLiNER. (The 7B-on-GPU vram% reading is unreliable when over-budget; the 1.3 tok/s is the real "doesn't fit" signal.)
- **Wired path behind the flag (OFF by default):** `storyweave/nlp/llm.py` — `llm_available(settings)` is the single gate (False unless `llm_enabled` AND base_url AND model); `LlmClient` **refuses to construct while disabled** (raises) and speaks the OpenAI-compatible Chat Completions API (runner-agnostic), stdlib `urllib` only (no new dep, light-venv clean). NO Tier-2/Tier-3 logic — that's 7c. `config.py` documents the run-order fallback and defaults to local Ollama / `qwen2.5:7b` with `llm_enabled=False`.
- **Tests (`test_llm.py`, +4):** disabled by default; client refuses to construct when disabled; **hard proof that the disabled path opens no socket** (monkeypatch `urllib.request.urlopen` to explode → never called); available only when enabled AND configured.

> **Phase 7 is split into THREE independently-gated sub-phases** (not one monolithic LLM stage): **7a** GLiNER-RelEx Tier-2 social relations (CPU, no VRAM risk — DONE); **7b** the LLM GPU→CPU→Colab go/no-go + Tier-2 disambiguation/junk rejection; **7c** Tier-3 identity inference (the Wren==Caelum / Zhou Mingrui⇄Klein showcase, reveal-shifting). Each ends green + pushed before the next.

## Done (Phase 7a)
- **Environment gate PASSED (CPU, no new framework).** Relation extraction ships inside the already-pinned `gliner==0.2.27`: `GLiNER.inference(..., relations=[...], return_relations=True)`. Checkpoint `knowledgator/gliner-relex-base-v1.0` (870M, v1.0 GCN/adjacency arch) loads + runs on CPU (84s cold load); weights cache to F: (one C: README leak detected + deleted). Smoke: `Lady Veris --betrayed--> Coil` (1.00), `Prince Caelum --mentor of--> Wren` (0.93). Pinned in `requirements-ml.txt`. (Note: `gliner-token-relex-v1.0` / `-relex-large-v0.5` from the brief don't exist / use the OLD two-pass API; the real repos are `gliner-relex-{base,large,multi}-v1.0`.)
- `nlp/relex.py`: `RelexExtractor` (lazy gliner import, `.venv-ml`) maps relex outputs onto the Tier-2 vocab via a prompt→relation table (`RELATION_PROMPTS`, e.g. "betrayed"→Betrayed, "mother of"→Parent); `RelexProtocol` lets tests inject a fake. `extract_social_relations` **anchors** each relation's head/tail surfaces to the canonical nodes the GLiNER floor already grounded (normalized-surface→node_id vote from the `mentions` table) — **relex never invents nodes**, it only adds edges between existing entities. Symmetric relations (Ally/Family/…) are stored order-independent.
- **Persistence + fence (no new path):** Tier-2 edges go through `repository.add_edge` with `tier=2`, `method='gliner'` (it IS a GLiNER model → no schema migration), evidence span, and Tier-1 reveal stamps (`revealed==first_seen==chunk's chapter`). They flow through the existing `edges` table → `list_edges_revealed` → `query/fence.py` unchanged; the Phase-5 P0 fence suite still passes untouched. Idempotent: `clear_edges_by_tier(work, SOCIAL)` rebuilds only Tier-2, leaving Tier-1 intact.
- **Graceful degradation IS tested (rule #4):** if the relex model can't load or fails mid-run, `extract_social_relations` returns a `degraded` report and leaves the Tier-1 floor + its fenced graph fully intact (`test_graceful_degradation_keeps_the_floor`).
- `cli`: `storyweave social <slug> [--model --config --db]` (lazy ML import; degrades cleanly).
- `config`/`work_config`: `relex_model`/`relex_device`/`relex_ner_threshold`/`relex_rel_threshold` (global) + per-work `RelationConfig` overrides (knobs are data).
- **BENCHMARK (interview gold) — `eval/relex_eval.py` + `data/labels/the-hollow-crown_relations.json`** (7 hand-labeled Tier-2 social relations across ch1–4, with an alias map so scoring is name-robust; symmetric + inverse relations normalized). Measured on the CC0 sample:
  - **Learned GLiNER-RelEx (Tier-2):** ALL **P=0.67 R=0.29 F1=0.40** (tp=2, fp=1, fn=5). Perfect on `Parent` (Maela→Caelum, 1.00) and recovers `Serves` (Wren→Coil); 13 Tier-2 edges produced graph-wide. Misses `Ally`/`Betrayed`/`Family` (base model, hard literary MTL-style prose, strict triple match).
  - **Hand-written co-occurrence rules (Tier-1) on the SAME social gold:** ALL **F1=0.00** — *by construction*: proximity rules can only emit structural labels (`RelatedTo`/`MemberOf`/`LeaderOf`), never social ones. **But Tier-1 pair coverage = 4/6**: rules connect 4 of 6 gold social pairs by *some* edge. **Deliverable insight:** rules find *that* two entities relate; the learned layer is what names *how* (Serves vs Betrayed vs Parent) — the two are complementary, neither alone is complete.
- Tests (`test_relex.py`, +8): prompt-map ⊆ Tier-2 vocab; anchor+persist+stamp; **no phantom node** for unanchored spans; symmetric dedup; **Tier-1 untouched + Tier-2 idempotent**; **Tier-2 edge passes the both-endpoints fence** (hidden until late endpoint revealed); **graceful degradation**; + 1 ML-gated real-relex smoke (`.venv-ml`).

## Done (Phase 7a — tuning pass: measure-driven recall/precision)
Goal: lift Tier-2 recall (Ally/Betrayed/Family were 0) without collapsing precision; every change proven on `eval/relex_eval.py` (added `--sweep`/`--dump` diagnostic: one low-threshold inference pass, post-filtered in memory — a full sweep costs one model load, not N).

- **BEFORE → AFTER (the-hollow-crown social gold, base `relex-base-v1.0`):**

  | | P | R | F1 | per-relation recall |
  |---|---|---|---|---|
  | **before** (thr 0.50) | 0.67 | 0.29 | **0.40** | Parent 1.0, Serves 0.5; Ally/Betrayed/Family 0 |
  | **after** (thr 0.60) | **1.00** | 0.29 | **0.44** | Parent 1.0, Serves 0.5; Ally/Betrayed/Family 0 |

  Headline win: **precision 0.67→1.00, F1 0.40→0.44** — at the shipped operating point relex makes **zero false-positive social claims** (8 Tier-2 edges graph-wide, down from 13). For a spoiler graph a wrong edge is worse than a missing one, so precision is the right axis to tune.
- **Lever 1 — threshold sweep (shipped).** `relation_threshold` 0.30→0.90: F1 peaks at a P=1.00 plateau from **0.60** (knee = max recall at P=1.0). Chosen 0.60. Lives in the sample `storyweave.toml` `[relations] relex_rel_threshold` (per-work knob) + the global default bumped 0.5→0.6 (precision-favoring). **Sweep table (base):** thr 0.50 → P0.67/F1 0.40; **0.60 → P1.00/F1 0.44**; 0.70–0.80 → P1.00/F1 0.44; 0.90 → F1 0.25.
- **Lever 2 — richer prompts (tested, REVERTED).** Expanded `RELATION_PROMPTS` with synonyms for the missed relations (betrayed→{turned against, usurped, conspired against}; Family→{kin of, related to}; Ally→{fights alongside, …}). Re-swept: **headline F1 unchanged (0.44), Ally/Betrayed/Family still 0 at every threshold.** Reverted (no number moved → doesn't ship). The `--dump` diagnostic shows why: the misses are **coreference** ("Maela was *my* friend" → Veris; "Help *me*" → Veris/Wren) and **implication** ("slipped the crown onto his own head" = betrayal, never the word) — not phrasing. That is squarely the LLM layer's job (7b/7c with coref + inference).
- **Lever 3 — larger checkpoint (tested, NOT shipped).** `gliner-relex-large-v1.0` (downloaded to F:, C: verified clean): **recovers Family (0→1.0) and full Serves recall, R 0.29→0.57** — but only at thr 0.30 where **precision collapses to 0.36**. At thr 0.60: P0.43/R0.43/F1 0.43. It violates the "without collapsing precision" constraint and never recovers Ally/Betrayed, so **base stays pinned**; large is kept on disk for 7b experiments. Decision recorded.
- **Net:** the threshold knob is the only lever that moved the shipped number (F1 0.40→0.44, P→1.00). The Ally/Betrayed ceiling is a coref/inference limit, explicitly deferred to the LLM layer — not a 7a tuning gap.
- Constraints held: **P0 fence suite unchanged & green**; graceful-degradation test green; light `.venv` green (importorskip); both venvs ruff + mypy clean; all knobs are config/TOML data (no `if`-branches); LotM stayed local (benchmark on the CC0 sample only).

## Done (Phase 6)
- `api/app.py`: fenced routes, thin (validate → fence → serialize → typed response). `n` is a mandatory `Query(..., ge=0)` so missing/negative → **422** automatically.
  - `GET /api/v1/health` — liveness + DB status + works count + vector-store status.
  - `GET /api/v1/works` — list works (+ chapter counts).
  - `GET /api/v1/works/{slug}/entities?n=N` — fenced entity list.
  - `GET /api/v1/works/{slug}/graph?n=N` — fenced Cytoscape JSON.
  - `GET /api/v1/works/{slug}/entity/{id}?n=N` — single entity (404 if unrevealed) + its revealed edges + revealed properties.
  - `GET /api/v1/works/{slug}/search?n=N&q=...` — fenced semantic search + cited answer.
- `api/schemas.py`: a pydantic response model for every route (no raw dicts); Cytoscape graph fully typed (`GraphNodeData`/`GraphEdgeData`).
- `api/deps.py`: overridable providers (`get_repository`/`get_embedder`/`get_vector_store`). The API imports NO ML — Embedder/Chroma load lazily; tests inject a fake embedder + in-memory store, so the whole API runs under light `.venv`.
- All reads go through `query/fence.py`; all SQL in `repository`. `Repository` now opens SQLite with `check_same_thread=False` (FastAPI threadpool; per-request repos aren't shared concurrently).
- Tests (`test_api.py`, +16): **P0 422-on-missing-n for every data route** (parametrized) + 422 on negative n + 422 on missing q; fenced entities/graph/entity-detail/search (incl. ch5 hidden at N=2, identity edge appears at N=2, secret property only at N=5); 404 for unknown work + unrevealed entity. `test_health.py` updated for DB status.

## Done (Phase 5)
- `query/fence.py` is now the consolidated single chokepoint for ALL four fenced surfaces: `visible_nodes`, `visible_edges` (both-endpoints; covers Tier-3 identity edges with no special-casing), `visible_node_properties` (NEW — property + node both-rule), `visible_chunk_hits` (search). Module docstring documents the keystone contract.
- `db/repository.py`: `list_node_properties_revealed(work_id, N)` — SQL JOIN enforcing the property-level both-rule (property AND node revealed); plus `list_node_properties(node_id)`.
- `graph/serialize.py`: the projection now attaches **fenced** revealed properties to each node's Cytoscape `data.properties` (a secret stat on a hidden/early-property node never leaks).
- **Permanent P0 regression `tests/test_fence.py` (7 tests)**: late node hidden at low N / visible at high N; both-endpoints edge rule; edge-level reveal independent of endpoints; serialized graph fenced; **property revealed later than its node**; **property of a hidden node stays hidden**; **Tier-3 identity reveal** (Wren==Prince Caelum SECRET_IDENTITY edge, hidden at N=1, visible at N=2); and a projection invariant proving no element with `revealed_chapter > N` ever appears.
- Architecture audit: graph projection + search both route through `query/fence.py`; SQL filtering lives in `repository.list_*_revealed`, vector filtering in the store's `query`; no unfenced read path is exposed to callers.

## Done (Phase 4)
- `search/embedder.py`: sentence-transformers wrapper (`Embedder`, lazy import, `.venv-ml`), L2-normalized embeddings (cosine == dot), HF cache forced to F:. `EmbedderProtocol` lets retrieval be tested with a fake embedder. Pinned `sentence-transformers==5.6.0`; model `all-MiniLM-L6-v2` (384-dim).
- `search/store.py`: `BaseVectorStore` interface + two backends — `InMemoryVectorStore` (pure-Python cosine, light venv, exact) and `ChromaVectorStore` (on-disk, lazy `chromadb==1.5.9`, cosine). Every vector carries `work_id` + `chapter_ordinal` (reveal key). **Fence applied inside `query`** (eligible = work_id match AND `chapter_ordinal <= max_chapter`) before ranking — no unfenced path out of the store. Rebuildable from SQLite.
- `query/fence.py`: added `visible_chunk_hits` — the sanctioned search entry; guarantees the chapter constraint reaches the index. (TYPE_CHECKING import of the store avoids a runtime cycle.)
- `search/retriever.py`: `index_work` (embed all chunks → store, idempotent per work), `search` (embed query → fenced top-k), and **offline extractive RAG** `compose_answer` (best query-relevant sentence per top hit + `[chN]` citations, provenance = chunk_id/chapter/char offsets). No LLM needed (rule #4); LLM compose is a Phase-7 opt-in.
- `cli`: `storyweave index <slug>` and `storyweave search <slug> "<query>" -n N [--top-k --db]` (negative N → error).
- `config`: `embedding_model`, `embedding_device`, `vector_dir` (`<repo>/.chroma`, gitignored).
- Tests (+13): store fence/work-isolation, `index_work` idempotency, **MANDATORY fence regression** (`test_search.py`: a ch5 chunk is absent at N=3 even when the query is its own text; reachable at N=5), extractive-answer citations; ML-gated real-embedder dimension/similarity + Chroma round-trip-fenced.
- Demo on sample: `index` → 12 chunks; search "who is the Gray Sparrow really" at **N=2 returns only ch1/ch2** (reveal is ch3, fenced out), at **N=4 returns the ch3/ch4 reveal passages**. Cited, spoiler-aware, end to end.

## Done (Phase 3)
- `query/fence.py`: the spoiler-fence chokepoint (`visible_nodes`/`visible_edges`). Sole sanctioned caller of the revealed-chapter SQL; never post-filters in Python.
- `db/repository.py`: `list_nodes_revealed` / `list_edges_revealed` apply the fence at the SQL level — the **both-endpoints rule** is a JOIN condition (`s.revealed_chapter<=N AND t.revealed_chapter<=N`). Plus edge CRUD: `list/count/clear_edges`.
- `graph/builder.py`: Tier-1 relationship extraction by co-occurrence within a configurable char window (same chapter). Explainable type-pair rule table → MemberOf/LocatedIn/HasAbility/OwnsItem/HasTitle/ParticipatedIn/AffiliatedWith, a lexical cue promoting MemberOf→LeaderOf, and `RelatedTo` as the never-drop fallback. Every edge: tier=1, method=rule, evidence quote, `first_seen==revealed==earliest co-occurrence chapter`. Idempotent (clear+rebuild).
- `graph/serialize.py`: SQLite → NetworkX `DiGraph` (fenced via `query/fence.py`) → Cytoscape `elements` JSON carrying type/subtype/reveal stamps.
- `ingest/work_config.py`: `RelationConfig` (window_chars=250, min_cooccurrences=1) — knobs as data.
- `cli`: `storyweave relate <slug>` and `storyweave graph <slug> -n N [--out]` (negative N → error).
- `networkx>=3.3` added to light deps (pure-Python, fine on 3.14).
- Tests (+13): `test_relate.py` (rule table, RelatedTo fallback, window exclusion, idempotency), `test_serialize.py` (Cytoscape shape + fenced), and **`test_fence.py` — the P0 both-endpoints regression** (edge to a ch5 node invisible at N=3; edge-level reveal independent of endpoints; serialized graph fenced).
- Demo on sample: extract→relate = **189 Tier-1 edges**; fenced graph grows **n=1: 15 nodes/64 edges → n=4: 38 nodes/189 edges**; Cytoscape JSON validated; zero LLM.

## Done (Phase 2)
- **Environment gate PASSED.** `.venv-ml` (Python 3.12) created; installed `torch==2.12.1+cpu`, `gliner==0.2.27`, `transformers==5.6.2`, `huggingface_hub==1.20.1`; real smoke extraction works on CPU (Wren→Character 0.98, Aldercross→Place, Coil→Organization). Versions pinned in `requirements-ml.txt`.
- **Model cache forced onto F:** (off C:, env discipline). `config.hf_home` → `<repo>/.hf-cache` (gitignored), applied via `nlp.extractor.configure_hf_cache` before any HF import; `tests/conftest.py` pins it before `importorskip` triggers HF; `HF_HUB_DISABLE_SYMLINKS=1` avoids WinError 1314. Verified: weights land on F:, C: stays clean. (Two C: leaks during setup were detected and deleted.)
- `nlp/labels.py`: GLiNER prompt labels → canonical 8-type map (incl. Concept-boosting prompts: "power system", "phenomenon", "language").
- `nlp/extractor.py`: lazy GLiNER wrapper (`GlinerExtractor`), returns canonical-typed `MentionSpan`s; ML imports lazy so it imports in the light venv.
- `nlp/cluster.py`: pure-Python alias clustering — normalize (case/article/punct), majority-vote type, conservative token-subset merge ("Veris"→"Lady Veris", "Coil"→"the Coil"). Canonical entity carries `first_seen_chapter`. Deliberately NOT semantic identity (that's Tier-3/Phase 7).
- `nlp/metrics.py`: pure P/R/F1 (generic, per-type + micro ALL).
- `nlp/pipeline.py`: `extract_work` — clear→GLiNER per chunk (offsets mapped to chapter)→persist raw mentions→cluster→insert canonical nodes (method=gliner, evidence quote, importance=mention count)→backfill `mention.node_id`. Idempotent (derived data, clear+rebuild).
- `db`: `mentions` table (raw candidates, persisted BEFORE clustering, FK + node_id backfill) + `Mention` model + repo methods (`add/list/count/clear_mention`, `set_mention_node`, `list/count/clear_nodes`).
- `cli`: `storyweave extract <slug> [--config --model --threshold --device --db]` (lazy ML imports).
- `eval/ner_eval.py` + `data/labels/the-hollow-crown_ch01.json`: hand-labeled ch01 (incl. a Concept entity, "the Glasswound"). Ran: **Concept P/R/F1 = 1.00**, Place correct, ALL F1=0.53 (gold 8, pred 15). Sample ch01 gained a named phenomenon "the Glasswound" so the corpus genuinely exercises the Concept type.
- Tests: +15 (cluster, metrics, mentions repo round-trip — pure/light) and 2 ML-gated GLiNER tests (`importorskip`). Light venv: 33 passed, 2 skipped. `.venv-ml`: the 2 GLiNER tests pass.

## Done (Phase 1)
- `ingest/cleaner.py`: NFKC, line-ending normalize, de-hyphenate soft wraps, config-driven cruft stripping (logged, not silently dropped), paragraph-preserving re-flow (blank-line or single-newline mode). Returns `CleanResult(text, removed_lines)`.
- `ingest/splitter.py`: chapter detection (`auto`/`file`/`heading`/`delimiter`; dir = one file per chapter, leading heading line → title); sentence spans (ASCII + CJK terminators); `chunk_spans` (max_chars, sentence overlap, oversize sentence = own chunk); `chunk_chapter` builds chunks by **slicing** clean_text so the offset invariant holds structurally.
- `ingest/work_config.py`: `storyweave.toml` loader via `tomllib` → validated `WorkConfig` (cleaning/splitting/chunking). Absent file = all defaults. `find_work_config` auto-detects beside file / in dir.
- `ingest/pipeline.py`: orchestrates config→clean→split→chunk→repo; idempotent (chapter keyed by (work, ordinal) + content_hash; identical = skip, changed = replace+rechunk); returns `IngestReport`.
- `db/repository.py`: added `chapters` + `chunks` tables (FK cascade, UNIQUE constraints) and methods (`get_or_create_work`, chapter/chunk CRUD + counts). All SQL still in repository.
- `db/models.py`: `Chapter` + `Chunk` pydantic mirrors (source-data layer, no reveal stamps; content_hash for idempotency).
- `cli/main.py`: `storyweave ingest <path> [--title --slug --config --db]` (lazy ML-free imports).
- **CC0 sample novel** `data/samples/the-hollow-crown/` (4 chapters + `storyweave.toml` + `LICENSE.md`): alias-rich, with a secret royal heir (Wren = Prince Caelum), a spymistress alias (Gray Sparrow = Lady Veris), and a transmigration hint — stresses Phase 2/5/7. Real novels stay in gitignored `data/raw/`.
- Tests (15 new, all green): cleaner (NFKC/dehyphen/cruft/paragraph modes), splitter (sentence spans, chunk sizing, heading+delimiter detection, **offset round-trip invariant**), end-to-end ingest of sample incl. **double-ingest-no-duplicates** + persisted-chunk offset invariant.

## Done (Phase 0)
- Package scaffold: `storyweave/{config,db,ingest,nlp,graph,search,query,api,cli}` + `frontend/ eval/ tests/ data/{raw,samples,labels}/ docker/`.
- `pyproject.toml`: light deps (fastapi, uvicorn, pydantic, pydantic-settings, typer) + `[dev]` (pytest, httpx, ruff, mypy). ruff + mypy(strict) + pytest config. Console script `storyweave`.
- `requirements-ml.txt`: documents the intended `.venv-ml` (Python 3.12) setup — **not installed** (Phase 2 is the gate).
- `.gitignore` (excludes `.venv/ .venv-ml/ *.sqlite node_modules/ data/raw/`), `.env.example` (LLM off by default).
- `storyweave/config.py`: pydantic-settings, env prefix `STORYWEAVE_`, `llm_enabled=False` default.
- `storyweave/api/app.py`: FastAPI app, `GET /api/v1/health`.
- `storyweave/cli/main.py`: Typer CLI with `version` + `info` commands.
- **Full 8-type schema, day one** — `db/models.py` (pydantic mirrors + ontology vocab) and `db/repository.py` (ALL SQL; 8 node types w/ CHECK, nullable subtype, 3-tier edges w/ CHECK, node-property mechanism, universal `first_seen_chapter`+`revealed_chapter` + provenance on every row).
- Tests (9, green): smoke (version + LLM-off default), `/health`, schema round-trip incl. Tier-3 identity edge + property-level reveal + CHECK-constraint rejection.
- `.venv` (Python 3.14) created; `pip install -e ".[dev]"` succeeded. README outline.

## Gate result (Phase 1)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, no issues in 25 source files.
- `pytest` → 24 passed.
- CLI verified: `storyweave ingest data/samples/the-hollow-crown` → `+4 chapters, +12 chunks, 2 cruft lines removed`; re-run → `0 added, 4 unchanged, 0 chunks` (idempotent).

## Gate result (Phase 0)
- Package scaffold: `storyweave/{config,db,ingest,nlp,graph,search,query,api,cli}` + `frontend/ eval/ tests/ data/{raw,samples,labels}/ docker/`.
- `pyproject.toml`: light deps (fastapi, uvicorn, pydantic, pydantic-settings, typer) + `[dev]` (pytest, httpx, ruff, mypy). ruff + mypy(strict) + pytest config. Console script `storyweave`.
- `requirements-ml.txt`: documents the intended `.venv-ml` (Python 3.12) setup — **not installed** (Phase 2 is the gate).
- `.gitignore` (excludes `.venv/ .venv-ml/ *.sqlite node_modules/ data/raw/`), `.env.example` (LLM off by default).
- `storyweave/config.py`: pydantic-settings, env prefix `STORYWEAVE_`, `llm_enabled=False` default.
- `storyweave/api/app.py`: FastAPI app, `GET /api/v1/health`.
- `storyweave/cli/main.py`: Typer CLI with `version` + `info` commands.
- **Full 8-type schema, day one** — `db/models.py` (pydantic mirrors + ontology vocab) and `db/repository.py` (ALL SQL; 8 node types w/ CHECK, nullable subtype, 3-tier edges w/ CHECK, node-property mechanism, universal `first_seen_chapter`+`revealed_chapter` + provenance on every row).
- Tests (9, green): smoke (version + LLM-off default), `/health`, schema round-trip incl. Tier-3 identity edge + property-level reveal + CHECK-constraint rejection.
- `.venv` (Python 3.14) created; `pip install -e ".[dev]"` succeeded. README outline.

## Gate result (Phase 0)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, no issues in 18 source files.
- `pytest` → 9 passed.
- `storyweave version` → `0.1.0`; `storyweave info` → `llm_enabled: False`.

## Gate result (Phase 7c)
- `ruff check .` → All checks passed (storyweave + tests + eval).
- `mypy` (strict) → Success, 57 source files (incl. `nlp/identity.py`, `eval/identity_eval.py`).
- `pytest` (light `.venv`) → **85 passed, 6 skipped** (+10 deterministic identity tests; the live smoke skips without `STORYWEAVE_LLM_LIVE`). Full identity orchestration (sweep, citation gate, anchoring, persistence, idempotency, fence, degradation) runs with ZERO ML/network.
- `pytest` (`.venv-ml`, `test_identity.py` + `test_fence.py` + `test_llm.py`) → 21 passed, 1 skipped (**P0 fence suite unchanged & green**; identity has no ML so it runs in both venvs).
- Live check (`eval/identity_eval.py`) → reveal TIMING EXACT (k2/k3) on both models, negative control held by 7B; reported, non-gating. Ollama stopped; C: clean (6 KB keypair), weights on F:.
- Rule #4/#5 proof: `llm_enabled=False` (default) → `infer_identities` returns `disabled`, writes nothing, opens no socket (tested with a booby-trapped `urlopen`).
- 7a Tier-2 precision (P=1.00) and Tier-2 edges untouched (7d scope); no schema migration.

## Gate result (Phase 7b)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, 33 storyweave source files (eval `llm_gate.py` clean too).
- `pytest` (light `.venv`) → 75 passed, 5 skipped (+4 LLM gate tests). `.venv-ml` sanity (test_llm/smoke/schema) → 12 passed; no ML code changed this phase, P0 fence suite untouched.
- LLM gate (`eval/llm_gate.py`) → **GO**: 4/4 configs produced correct identity JSON; GPU-3B 57 tok/s, CPU-7B 8.5 tok/s, GPU-7B 1.3 tok/s (over budget). C: clean, weights on F:.
- Rule #4/#5 proof: `llm_enabled=False` (default) → no client constructible, no outbound socket (tested).

## Gate result (Phase 7a, incl. tuning pass)
- `ruff check .` → All checks passed (storyweave + tests + eval).
- `mypy` (strict) → Success, 32 storyweave source files (eval clean too).
- `pytest` (light `.venv`) → 71 passed, 5 skipped (ML-gated skip without ML). Full relex orchestration (anchor/persist/idempotency/fence/degradation) runs with zero ML.
- `pytest` (`.venv-ml`, `test_relex.py` + `test_fence.py`) → 15 passed (incl. real GLiNER-RelEx smoke + the **unchanged P0 fence suite**). C: stays clean; relex weights on F:.
- Benchmark (`eval/relex_eval.py`) → after tuning: learned Tier-2 **ALL P=1.00 R=0.29 F1=0.44** (Parent 1.00, Serves 0.67, zero FPs); rules F1=0.00 on social gold but 4/6 pair coverage — complementarity stands. `--sweep`/`--dump` diagnostics added.

## Gate result (Phase 6)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, 46 source files.
- `pytest` (light `.venv`) → 64 passed, 4 skipped. Entire API suite runs without ML installed (proves no ML import in the API layer).
- P0: every data route returns 422 when `n` is absent.

## Gate result (Phase 5)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, 43 source files.
- `pytest` (light `.venv`) → 50 passed, 4 skipped.
- P0 fence suite (`test_fence.py`) → 7 passed (nodes, edges, identity, properties, projection invariant).

## Gate result (Phase 4)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, 43 source files.
- `pytest` (light `.venv`) → 46 passed, 4 skipped.
- `pytest` (`.venv-ml`, `test_search.py`) → 7 passed (real embeddings + Chroma).
- Fenced search regression green; cache stays on F: (673M), C: clean.

## Gate result (Phase 3)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, 39 source files.
- `pytest` (light `.venv`) → 41 passed, 2 skipped.
- P0 fence regression (`test_fence.py`) green; Cytoscape JSON validated; graph fenced & grows with N.

## Gate result (Phase 2)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, 34 source files.
- `pytest` (light `.venv`) → 33 passed, 2 skipped (GLiNER tests skip without ML).
- `pytest` (`.venv-ml`) → GLiNER tests pass; cache stays on F:, C: clean.
- `eval/ner_eval.py` → real per-type P/R/F1 (Concept 1.00, ALL F1 0.53).
- CLI: `storyweave extract the-hollow-crown` → 89 mentions → 38 entities (7/8 types); re-run identical (idempotent).

## In-progress / next
- **Phase 7c DONE.** Tier-3 identity inference shipped (citation-gated, reveal-respecting, OFF by default). **Identity primary = CPU `qwen2.5:7b`** (config default), GPU `llama3.2:3b` = speed fallback.
- **DECIDED next-session order (updated by the LotM ch1 run):**
  1. **DONE — private LotM ch1 validation run** (report-only, nothing mutated; see Measurement-run section). Result reshaped the priority below.
  2. **NEXT — `TRANSMIGRATED_INTO` citation-production fix (light, the measured binding problem):** the both-names citation demand fail-closes on transmigration/memory-flood reveals that never co-name both entities → relax it / adopt the single-entity representation (design-input c). This is what actually blocked the true reveal on real prose, ahead of any entailment work.
  3. **THEN — re-measure the entailment gap on a MULTI-CHAPTER drop** with co-naming secret-identity/alias reveals (the gap was 0/masked on ch1; it can only bite where one clause co-names both entities). Only if it bites at a real rate does the **heavy NLI/entailment-relevance verifier** get built; otherwise lighter relation-subtype discipline. **Do not build NLI before this measurement.**
  4. **THEN — Phase 7d (Tier-2 LLM cleanup), still PARKED:** LLM-assisted Tier-2 disambiguation (Hermes-language vs deity) + junk rejection. Its own boundary; must NOT disturb the 7a precision (P=1.00) number or the Tier-3 edges. **Distinct from the Tier-3 entailment gap.**
  5. **Phase 8 (Frontend) does NOT start until reveal timing is trustworthy;** **Phase 9** — packaging/CI/README.
- **7c residual design inputs (recorded, NOT implemented; the entailment gap is now its own Known-issues item):** (b) **relation-subtype discipline** — small models use SAME_AS/SECRET_IDENTITY/ALIAS interchangeably; a post-hoc type-normalizer or few-shot examples would firm this up. (c) **TRANSMIGRATED_INTO for the unnamed-soul case** — needs a single-entity property representation (or a synthetic "prior-world soul" node) rather than a two-named edge; revisit when a sample names both sides (LotM's Zhou Mingrui⇄Klein does).
- **To run the LLM locally (7c):** `tools/ollama/ollama serve` with `OLLAMA_MODELS=.llm-cache/ollama-models`, then set `STORYWEAVE_LLM_ENABLED=true` (models `qwen2.5:7b` CPU or `llama3.2:3b` GPU already pulled). Re-run `eval/llm_gate.py` to re-confirm.
- Routes not yet built: `POST /ingest`, delete-work, and a Tier filter on `/graph` so the frontend can toggle structural vs social. Add when wiring the frontend (Phase 8).
- **Benchmark improvement ideas (7b/later):** the 7a tuning pass settled the GLiNER-RelEx ceiling — threshold tuned (0.60, P=1.00), richer prompts tested (no gain, reverted), `relex-large-v1.0` tested (recovers Family/recall but precision→0.36, not shipped). The residual misses (Ally/Betrayed via pronoun coref + implication) need the **LLM layer (7b/7c)**: coreference resolution + relation inference, not more relex tuning. `relex-large-v1.0` weights are already on F: if a recall-favoring mode is wanted later.

## Known issues / TODOs
- **Tier-3 entailment gap (OPEN, blocks public reveal-timing claims):** the citation gate proves the cited clause is real, not that it entails the pair. Real-but-irrelevant citations can over-merge (GPU-3B observed on the sample). A Tier-3 SOUNDNESS gap in the identity showcase itself — **distinct from 7d (Tier-2 cleanup).** Must be resolved before any public GIF asserts trustworthy reveal timing.
  - **MEASURED (LotM ch1 run, see Measurement-run section): the gap did NOT bite on real ch1 prose — 0 real-but-irrelevant over-merges.** It is currently **MASKED** by a more fundamental failure: both models fail to quote the passage for the transmigration reveal (7B echoes the instruction, 3B empty), so the existence gate fail-closes on the TRUE reveal (1/1 true merges dropped, both models). **So the heavy NLI fix is NOT yet justified by data.** Binding problem first = **citation production for transmigration-style reveals** (the both-names clause demand has nothing to bind to when the text never co-states both names) → light fix = relax that demand / single-entity representation (design-input c). The entailment gap stays OPEN but **unmeasured at scale** — needs a multi-chapter drop with co-naming secret-identity/alias reveals to measure as a rate.
- **`TRANSMIGRATED_INTO` citation rule (NEW, OPEN — surfaced by the LotM run):** the both-names citation requirement fail-closes on transmigration/memory-flood reveals where the prose never co-names both entities in one clause (confirmed live on LotM ch1, both models → MISS on the true reveal). Likely the **first** fix next session. Tied to design-input (c).
- Starlette TestClient emits a deprecation warning (httpx vs httpx2). Cosmetic; revisit if it becomes an error.
- `.venv-ml` intentionally not created yet (Phase 2 gate).
- Dir-mode chapter detection ingests every `*.txt`; non-chapter files in a sample dir must use another extension (the sample's notice is `LICENSE.md`). Acceptable for now.

## Decisions log
- **Two-venv split confirmed working:** `.venv` = Python 3.14 (light); `.venv-ml` = Python 3.12 (heavy, Phase 2). Light deps installed cleanly on 3.14.
- **`config` as a module** (`config.py`), not a subpackage — simpler; satisfies the SPEC layout intent.
- **Ontology vocabulary lives in `db/models.py`** and is reused to build SQL CHECK constraints in `repository.py`, so SQL and pydantic mirrors cannot drift.
- **`requires-python = ">=3.12"`**, ruff/mypy target `py312` — the floor shared by both venvs.
- Health route under `/api/v1` from the start (forward-compatible with Phase 6 routes).
- No Claude co-author trailer on commits (CLAUDE.md backup discipline).
- **Phase 1:** chunk offset invariant is guaranteed *structurally* by slicing `clean_text[start:end]` (not by reconstructing text), so it holds regardless of sentence-splitter quality.
- **Phase 1:** chapters/chunks carry NO reveal stamps — they are raw source data; the reveal mechanism is reserved for graph elements (nodes/edges/properties).
- **Phase 1:** idempotency keyed on (work, ordinal) + content_hash of clean_text; identical re-ingest skips, changed content replaces chapter (chunks cascade) and re-chunks.
- **Phase 1:** cleaning is paragraph-preserving and defines the canonical coordinate space that chunk offsets index into.
- **Phase 2 (HF cache on F:):** model weights cache at `<repo>/.hf-cache` (gitignored), pinned via `config.hf_home` + `configure_hf_cache` + `tests/conftest.py`, with `HF_HUB_DISABLE_SYMLINKS=1`. Both GLiNER now and the Phase-7 LLM cache on F:, never C:. Exact path: `F:\Dev\Claude_folder_project_and_stuff\storyweave\.hf-cache`. (HF binds the cache path at IMPORT time, so the env var must be set before the first `huggingface_hub` import — hence conftest.)
- **Phase 2 (model):** `urchade/gliner_small-v2.1` on CPU is the pinned floor; small model also fits the 4 GB GPU via `gliner_device="cuda"`.
- **Phase 2 (clustering):** string-based canonicalization only (surface variants), NOT semantic identity — Wren≠Caelum here on purpose; identity is Tier-3, fenced, Phase 7.
- **Phase 2 (extraction idempotency):** mentions+nodes are derived; a re-run clears and rebuilds (no dup nodes).
- **Phase 2 (sample):** ch01 gained a named phenomenon "the Glasswound" so the CC0 corpus exercises the signature Concept type (GLiNER tags it Concept ~0.45, above the 0.4 threshold).
- **Phase 3 (fence at SQL level):** the both-endpoints rule is a JOIN in `repository.list_edges_revealed`, never a Python post-filter; `query/fence.py` is the only sanctioned caller. Phase 5 will consolidate search fencing here too.
- **Phase 3 (rule edges reveal == first_seen):** a structural co-occurrence edge is known to the reader exactly when both entities have co-occurred, so no reveal shift; secret/identity reveal-shifting is Tier-3/LLM (Phase 7).
- **Phase 3 (edges are derived):** like mentions/nodes, edges are rebuilt idempotently (clear+rebuild) — SQLite chapters are the only non-derived source.
- **Phase 4 (chunk reveal key):** a chunk's reveal key is its `chapter_ordinal` (reader at N sees chunks from chapters ≤ N); stored as vector metadata so the fence is an index-level filter, not a post-filter.
- **Phase 4 (two backends, one interface):** InMemory (light, exact, testable without ML) + Chroma (on-disk dev). FAISS deferred — Chroma covers dev/demo; the adapter interface keeps FAISS a drop-in later.
- **Phase 4 (offline RAG floor):** extractive cited answer needs no LLM (rule #4). Vector index is fully rebuildable from SQLite chunks; nothing non-derived is stored in `.chroma/`.
- **Phase 4 (Windows/Chroma):** Chroma holds `chroma.sqlite3` open; tests use `TemporaryDirectory(ignore_cleanup_errors=True)`. Chroma collection names need ≥3 chars.
- **Phase 5 (identity = ordinary edge):** Tier-3 identity reveals (SAME_AS/ALIAS/SECRET_IDENTITY/REINCARNATION/TRANSMIGRATED_INTO) need NO special fence path — they are edges fenced by `revealed_chapter` + both-endpoints. The reader-knowledge timing (e.g. learns Wren==Caelum at ch2) is just the edge's `revealed_chapter`.
- **Phase 5 (property both-rule):** a property is visible only if the property AND its node are revealed — enforced as a SQL JOIN, surfaced in the graph projection as `data.properties`.
- **Phase 5 (no unfenced path):** the only client-facing reads are the `fence.visible_*` functions; raw `repository.list_nodes/list_edges` are for derived rebuilds, never client output. Phase 6 API must call only the fence.
- **Phase 6 (no ML in API):** Embedder/Chroma are injected via FastAPI dependencies and load ML lazily; tests override them with a fake embedder + in-memory store, so the API is fully testable (and runnable) under the light `.venv`.
- **Phase 6 (mandatory n):** every data route uses a required `Query(..., ge=0)`; FastAPI returns 422 for missing/negative n with no custom code. `q` is `Query(min_length=1)`.
- **Phase 6 (sqlite threads):** `Repository` uses `check_same_thread=False` for FastAPI's threadpool; safe because each request gets its own repo (no concurrent sharing).
- **Phase 7a (no new framework):** relation extraction is already in `gliner==0.2.27` (`GLiNER.inference(relations=..., return_relations=True)`) — no gliner upgrade, Phase-2 floor pin untouched. The only new artifact is the model `gliner-relex-base-v1.0` (cached to F:).
- **Phase 7a (provenance = gliner, no migration):** Tier-2 edges use `method='gliner'` (it is a GLiNER model) so the Phase-0 CHECK constraint `('gliner','rule','llm')` is unchanged; `tier=2` is what separates them from Tier-1 `method='rule'` edges. (LLM-inferred Tier-2/Tier-3 in 7b/7c will use `method='llm'`.)
- **Phase 7a (anchor, don't invent):** relex spans are re-grounded to the floor's canonical nodes via a normalized-surface→node_id vote over `mentions`; an unanchored span yields no edge. Keeps the 8-type node set authoritative and avoids phantom nodes.
- **Phase 7a (reveal == first_seen for stated relations):** a social relation written in the prose is reader-known when read, so no reveal shift here; reveal-shifting (secrets/identity) is Tier-3 (7c).
- **Phase 7a (idempotent, tier-scoped):** `clear_edges_by_tier(work, SOCIAL)` rebuilds only Tier-2, so re-running `social` never disturbs the Tier-1 floor and never duplicates.
- **Phase 7a (graceful degradation is enhancement, not dependency):** model load/inference failure → `degraded` report, Tier-1 floor + fence untouched (rule #4), covered by a permanent test.
- **Phase 7a (benchmark = the deliverable):** learned RE recovers social relations (Parent 1.00, Serves) that hand-written co-occurrence rules cannot label at all (rules F1=0 on social gold, yet 4/6 pair coverage). Complementary, not competing — quantified on the CC0 sample.
- **Phase 7a tuning (precision over recall for a spoiler graph):** chose `relex_rel_threshold=0.60` (the P=1.00 knee) over recall-maximizing settings — a false social edge is worse than a missing one when the graph is reader-facing. F1 0.40→0.44, precision 0.67→1.00, zero FP social edges. Knob lives in `storyweave.toml`; global default also 0.6.
- **Phase 7a tuning (negative results are results):** richer prompts and `relex-large-v1.0` were both measured and rejected — prompts moved nothing (Ally/Betrayed/Family are coref/implication, not phrasing); large recovered Family + recall but collapsed precision to 0.36. Recorded so the ceiling is understood, not re-litigated. The remaining recall is an LLM-layer (7b/7c) job.
- **Phase 7b (runner = Ollama, not llama-cpp-python):** the no-installer zip avoids a Windows CUDA build, bundles CUDA runners for the GTX 1650's auto partial-offload, caches weights to F:, and gives an OpenAI-compatible `/v1` + measured eval timing. The wired client targets `/v1` so it's runner-agnostic (swap to any compatible endpoint later).
- **Phase 7b (chosen path — SUPERSEDED by the addendum below):** initially CPU `qwen2.5:7b` primary on *size reasoning* (probe didn't separate accuracy; 7-8B assumed safer for multi-step inference). Kept here for the audit trail; the model pick is revised by the graded probe.
- **Phase 7b ADDENDUM (model pick = GPU `llama3.2:3b` primary, CPU `qwen2.5:7b` fallback — EVIDENCE-backed on REVEAL accuracy):** a reveal-chapter-graded sweep (`eval/llm_probe.py`) measures *when* each model first flips to YES vs a gold reveal chapter (the metric 7c's `revealed_chapter` depends on), per candidate pair, reveal-respecting. **Base prompt:** both land the alias cases EXACT and PASS the negative control, but both flip EARLY on the subtle transmigration case (GPU-3B 2 chapters early, CPU-7B 1 early — 7B marginally more conservative). **The one prompt improvement (`--cite`, require a quoted confirming clause) moved both transmigration flips to EXACT** (first_yes 2→4 and 3→4), all cases EXACT + control PASS for both. With reveal-accuracy then tied, **speed decides: 59.7 vs 8.7 tok/s (~6.8×) → GPU-3B primary.** CPU-7B is the fallback for VRAM-contended/RAM-only runs and the conservative real-novel re-validation in 7c. **7c design inputs banked: (a) infer identity per-candidate-pair, not one-shot enumeration; (b) gate the `revealed_chapter` flip behind a confidence margin — require the model to cite the confirming clause from ch1..k — or it spoiler-shifts on partial clues.**
- **Phase 7c (citation gate = EXISTENCE, not relevance):** `revealed_chapter` = smallest k with a confirmed identity AND a quote that normalized-occurs in chapters 1..k. Match rule = NFKC+casefold+depunct+whitespace containment (≥8 chars), reusing the cleaner's NFKC space. Rejected the stricter "quote must name both entities" rule because the live model cites real-but-vague clauses near the reveal → both-names fails closed (drops even the correct SECRET_IDENTITY). A `same=true` with no valid in-range citation is rejected + counted (`citations_rejected`) so fail-closed ≠ "no identity". Relevance/entailment is a model problem → next design input (needs NLI, not substring).
- **Phase 7c (identity is an EDGE, never a node collapse):** the two underlying entities stay two nodes; the inferred identity is one `tier=3, method='llm'` edge between them with the verified citation as `evidence_span` and the smallest-k as `revealed_chapter` (the reveal SHIFT — entities exist from `first_seen` but the reader connects them at k). No schema change (`tier=3`/`method='llm'` already in the Phase-0 CHECK); flows through the unchanged fence. A pair may carry MULTIPLE Tier-3 edges (layered reveals: Wren==Caelum SECRET_IDENTITY@2 + TRANSMIGRATED_INTO@4).
- **Phase 7c (deterministic tests vs live model):** a live LLM is non-deterministic, so the green-gating regressions (flip-at-gold, no-citation-no-edge, degradation, idempotency, disabled-path) are driven by an injected fake (`IdentityProtocol`) in the light venv; the real model is exercised only in the non-blocking `eval/identity_eval.py` report. Confirmed: the `/v1` path is unseeded → live answers flicker run-to-run (the negative control PASS→FAIL drift on GPU-3B), which is exactly why live output must never gate CI.
- **Phase 7c (identity primary = CPU `qwen2.5:7b`, refining the addendum):** the addendum's *simple* per-pair probe found 3B==7B → picked 3B for speed; the *full* identity task (relation-typing + skeptical merging + citation) re-separates them — 7B labels the alias EXACT@3 and robustly holds the negative control, 3B mislabels the subtype (LATE) and intermittently over-merges. So the identity primary is `qwen2.5:7b` (config default already), `llama3.2:3b` the speed fallback. Reveal TIMING is EXACT (k2/k3) on BOTH — the anti-early-bloom property holds regardless.
- **Phase 7c (all five vocab, three proven):** SECRET_IDENTITY/ALIAS/TRANSMIGRATED_INTO have gold cases + tests; SAME_AS/REINCARNATION are schema-and-prompt-ready but UNPROVEN (no sample exercises them — not faked). TRANSMIGRATED_INTO is deterministically tested but not live-confirmable on this sample (the prior-world soul is unnamed → a single-entity property, not a two-named edge).
- **Phase 7b (flag off = structurally inert):** `llm_available()` is the single gate and `LlmClient` refuses to construct when disabled, so rules #4/#5 hold by construction, not convention — proven by a test that fails if the disabled path opens any socket. No Tier-2/Tier-3 logic built yet (gate only).
