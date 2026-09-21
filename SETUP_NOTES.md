# SETUP_NOTES — local environment setup (Windows, GTX 1650)

Session goal: get this ZIP-downloaded copy of StoryWeave running locally. No feature work.

## Phase 0 — Recon findings

- **Folder structure is already correct.** `F:\Dev\Claude_folder_project_and_stuff\StoryWeave`
  contains CLAUDE.md, SPEC.md, PROGRESS.md, README.md, pyproject.toml, requirements-ml.txt,
  storyweave/, frontend/, tests/, data/, docker/, .github/ directly at root. **Not nested.**
  Phase 1 (folder move) is **SKIPPED — not needed.**
- **This is not an early-stage project.** PROGRESS.md shows Phase 8 (frontend) complete,
  124 tests passing, ruff clean, mypy strict clean across 59 files. It was previously built,
  gated, and pushed to GitHub (`Shashank-ssls/StoryWeave`) in an earlier session; this ZIP is
  a fresh download of that pushed state onto a new machine. No `.git` folder present (confirms
  ZIP download, not clone).
- **Tooling present (nothing installed by this session):**
  - Python 3.14.4 at `F:\Apps\Python\python.exe` (candidate for light `.venv`, matches CLAUDE.md's
    "`.venv` = 3.14" split).
  - Python 3.12.13 at `C:\Users\space\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe`
    (via `py -0p`; installed by `uv`, already present — candidate for `.venv-ml`, matches
    "`.venv-ml` = 3.12" split exactly).
  - Node v24.15.0, npm 11.15.0 (README wants 18+, 20 recommended; CI pins 20 — 24 should be fine
    for a local dev server/build; noted as a possible but unconfirmed risk).
  - git 2.54.0.windows.1.
  - `nvidia-smi`: GTX 1650, driver 596.36, driver-reported CUDA 13.2. **No Ollama installed**
    (`ollama --version` → command not found). LLM layer stays off (already off by default).
- **Important pin discovery:** `requirements-ml.txt` already pins exact versions **verified at a
  prior gate**: `torch==2.12.1` (installed from the **CPU** index-url, deliberately, per its own
  comment — "Phase-2 environment gate, verified working on CPU"), `gliner==0.2.27`,
  `transformers==5.6.2`, `huggingface_hub==1.20.1`, `sentence-transformers==5.6.0`,
  `chromadb==1.5.9`. `storyweave/config.py` defaults `gliner_device="cpu"` /
  `relex_device="cpu"`; CUDA (`gliner_device="cuda"`) is documented as an optional override, not
  the tested default. **Decision: install the pinned CPU wheel as-is rather than switching to a
  CUDA build** — the pasted task's generic instruction was to prefer CUDA, but this project has
  already run a real go/no-go gate on CPU and pinned to it; swapping to an untested CUDA build
  right after a ZIP restore risks breaking a proven combination for no measured benefit (CPU is
  fine for this workload per PROGRESS.md's own numbers). Flagging this deviation explicitly per
  your rules rather than silently following either instruction.
- **`storyweave/config.py` already defaults `HF_HOME` to `<repo>/.hf-cache`** (gitignored), so
  model weights already stay off C: without any manual env override. I will still create
  `.local/pip_cache` and `.local/npm_cache` for pip/npm as instructed, and additionally set
  `HF_HOME`/`TORCH_HOME` in the activation scripts for defense-in-depth / any ad-hoc script that
  doesn't import `storyweave.config` first.
- **No hardcoded absolute paths** (`F:\`, `C:\Users`, `/Users/`, `/home/`) found anywhere in
  `storyweave/`, `tests/`, `frontend/src/`, or the top-level docs (grep clean).
- **No top-level `storyweave.toml`** — per-work config lives at
  `data/samples/the-hollow-crown/storyweave.toml` and `data/samples/shadow-slave/storyweave.toml`
  (the latter references a local, gitignored novel text not present in this checkout — expected).
- Demo tier: `storyweave/demo/seed.py` — `storyweave seed-demo --db storyweave-demo.sqlite`
  builds a deterministic CC0 demo graph with zero ML/downloads (README step 6).
- CI (`.github/workflows/ci.yml`) pins Python 3.12 (light gate) and Node 20 for its own runs —
  confirms 3.12+ is the true floor for the light venv despite the local dev machine using 3.14.

---

## Phase-by-phase results

| Phase | Result | Notes |
|---|---|---|
| 0 - Recon | PASS | Findings above. Project is Phase-8-complete, not early-stage. |
| 1 - Folder fix | SKIPPED | Already correctly rooted; no nested folder. |
| 2 - Re-link git | PASS | `git init` + `origin` + `fetch` + `reset --soft origin/main`; working tree matches `origin/main` byte-for-byte except the new `SETUP_NOTES.md`. Not committed/pushed (as instructed). |
| 3 - Python envs | PASS | `.venv` (3.14) + `.venv-ml` (3.12) created; `pip install -e ".[dev]"` and the pinned ML stack installed; `pip check` clean in both; lockfiles frozen. |
| 4 - Models | PASS | GLiNER (`urchade/gliner_small-v2.1`) + GLiNER-RelEx (`knowledgator/gliner-relex-base-v1.0`) downloaded and smoke-tested; confirmed nothing landed in `C:\Users\<me>\.cache\huggingface` (1.5 GB, all on F: in `.hf-cache/`). Ollama: not installed - left that way (LLM layer off by default, no models pulled). |
| 5 - Activation scripts | PASS | `dev.ps1` / `dev.bat` created and both variants (light + `-Ml`/`ml`) tested working. |
| 6 - Frontend | PASS | `npm ci` (81 packages) + `npm run build` green. 6 audit findings reported, not fixed (see below). |
| 7 - Run & verify | PASS | Backend health/works/graph endpoints hit and verified (see below); frontend dev server loads and proxies `/api` to the backend; demo tier confirmed with LLM disabled; full ML pipeline (`ingest`, `extract`, `relate`) run on the real GLiNER models against the CC0 sample (throwaway DB, deleted after). |
| Tests/lint/types | PASS | `pytest`: 124 passed, 6 skipped. `ruff check .`: clean. `mypy`: clean, 59 files. Frontend `tsc -b && vite build`: clean (one pre-existing Cytoscape chunk-size warning). All match PROGRESS.md's last-recorded numbers exactly - nothing regressed by this environment setup. |

## Verified backend responses (real requests, not assumed)

- `GET /api/v1/health` -> `{"status":"ok","version":"0.1.0","database":"ok","works":1,"vector_store":"empty"}`
- `GET /api/v1/works` -> `{"works":[{"id":1,"slug":"the-hollow-crown","title":"The Hollow Crown","chapter_count":4}]}`
- `GET /api/v1/works/the-hollow-crown/graph?n=1|2|4` -> nodes/edges grow monotonically (6/5 -> 10/9 -> 13/13), and the identity edges (`ALIAS` at `revealed_chapter:3`, `TRANSMIGRATED_INTO` at `revealed_chapter:4`) are absent from the `n=1`/`n=2` payloads and present at `n=4` - the spoiler fence verified live, not just read from code.
- Frontend dev server (`http://localhost:5173/`) -> 200, and its `/api` proxy -> the same backend health JSON, confirming the dev-server-to-API wiring works with no CORS/base-URL mismatch.

## Exact commands (fresh terminal)

```powershell
# Backend (light venv)
.\dev.ps1
storyweave seed-demo --db storyweave-demo.sqlite   # already done this session, DB exists
$env:STORYWEAVE_DB_PATH="storyweave-demo.sqlite"; uvicorn storyweave.api.app:app --port 8000

# Frontend (separate terminal, no venv needed)
cd frontend
npm run dev                                        # http://localhost:5173

# ML pipeline (separate terminal, heavy venv)
.\dev.ps1 -Ml
storyweave ingest data/raw/my-novel --slug my-novel --db my.sqlite
storyweave extract my-novel --db my.sqlite
storyweave relate  my-novel --db my.sqlite
```

## Every file changed or created, with reason

- `SETUP_NOTES.md` - created; this file (recon + report).
- `.gitignore` - added a `.local/` line; keeps the new cache dirs out of git.
- `.local/{pip_cache,npm_cache,hf_cache,torch_cache}/` - created; pip/npm caches actually route here (`hf_cache`/`torch_cache` are currently unused placeholders - see HF_HOME decision below).
- `dev.ps1`, `dev.bat` - created; per-session env + venv activation, two variants each (light / `-Ml`|`ml`).
- `frontend/.npmrc` - created (`cache=../.local/npm_cache`); keeps npm's package cache off C:.
- `requirements.lock.txt`, `requirements-ml.lock.txt` - created; `pip freeze` snapshots of both venvs, for reproducibility.
- `.venv/`, `.venv-ml/`, `frontend/node_modules/`, `frontend/dist/`, `.hf-cache/`, `.chroma/` (empty), `storyweave-demo.sqlite` - created by the normal setup/build/seed commands; all already gitignored, none committed.
- Deleted: a stray empty file named `activates` (0 bytes) that appeared at the repo root during venv-activation testing - almost certainly a shell-quoting artifact from one of my own PowerShell invocations, not pre-existing user data. Removed as clutter; flagged here per your rule.
- No application source code was modified.

## Version pins

- No new pins were added anywhere - `requirements-ml.txt`'s existing pins (torch==2.12.1, gliner==0.2.27, transformers==5.6.2, huggingface_hub==1.20.1, sentence-transformers==5.6.0, chromadb==1.5.9) were already correct and gate-verified; installed as-is.
- One correction during setup: `pip install torch --index-url .../cpu` (no version) initially grabbed 2.14.0; re-ran pinned to `torch==2.12.1` to match the project's tested version. Final state confirmed: `torch 2.12.1+cpu`, `cuda available: False`.

## Deliberate deviations from your pasted instructions (flagging explicitly, not silently)

1. **CPU torch instead of a CUDA build.** `requirements-ml.txt` documents `torch==2.12.1` as gate-verified on CPU, and `storyweave/config.py` defaults `gliner_device="cpu"`. I installed the CPU wheel as pinned rather than switching to a CUDA build for the GTX 1650 - swapping now would be an untested combination replacing a proven one, for a workload the project's own numbers say doesn't need it (CPU inference times were all sub-90s in my smoke tests). GPU accel remains available as an opt-in (`gliner_device="cuda"` + a CUDA torch wheel) if you want to try it later.
2. **HF_HOME left at the app's own default (`<repo>/.hf-cache`)**, not redirected to `.local/hf_cache`. `storyweave/config.py`/`extractor.py` already force HF weights onto F: via `HF_HOME` (using `os.environ.setdefault`, so it's fully overridable) before I touched anything, and the 1.5 GB of models are already downloaded there. Redirecting to `.local/hf_cache` now would just split the cache and force a second download. `.local/hf_cache` and `.local/torch_cache` still exist as instructed but are currently empty placeholders; say the word if you want me to actually move `.hf-cache/` into `.local/` and set `HF_HOME` explicitly in the activation scripts instead.

## npm audit (reported only, nothing fixed)

6 vulnerabilities (2 moderate, 4 high), all in frontend dev-tooling transitive deps (not runtime/production code): `browserslist`, `esbuild`/`vite` (dev-server-only issue), `nanoid`, `postcss`, `baseline-browser-mapping`. `npm audit fix` (non-breaking) would resolve most; `--force` would bump `vite` to 8.x (breaking) - did not run either, per your instruction.

## Blocked / needs your decision

- Ollama: not installed, nothing pulled. Config expects `qwen2.5:7b` (CPU primary) and `llama3.2:3b` (GPU fallback) if/when you want the optional LLM layer - install separately when ready.
- Not committed or pushed - working tree matches `origin/main` plus the new setup files above; waiting for your review before any `git add`/`commit`.
- Frontend Node version: installed/tested against Node v24.15 (only version present on this machine); CI/README target Node 20. The build and dev server both worked fine on 24, but this combination is otherwise unverified upstream - flagging as a minor, currently-inert risk.

## Frontend observations (read-only - no changes made; for a future redesign session)

- Structure: a small, flat component tree - `App.tsx` (765 lines, the graph-view/library shell and most state), `GraphView.tsx` (417 lines, the Cytoscape.js + cytoscape-cola wrapper), `Composer.tsx` (235 lines, chapter-ingest/editing UI), `Library.tsx` (100 lines, the work-selection landing view), plus small `api.ts`/`ontology.ts`/`types.ts` helpers. No routing library, no state-management library (Redux/Zustand/etc.) - state lives in plain React hooks in `App.tsx`, which is doing a lot (it's the largest file by a wide margin).
- Styling: a single hand-written `styles.css`, no Tailwind/CSS-in-JS/CSS-modules. `DESIGN.md` documents a deliberate, cohesive "constellation" design language (dark midnight background, gold reserved exclusively for identity reveals, an 8-color typed-node palette, Spectral/IBM Plex Sans/IBM Plex Mono via self-hosted `@fontsource` - no external font CDN calls). This is unusually well-specified for a personal project; a redesign session should read `DESIGN.md` first rather than guessing intent.
- What looks weak: `App.tsx` at 765 lines is doing view state, data fetching, and multiple feature toggles (degree filter, salience-demotion, type-isolation, focus/click navigation per PROGRESS.md) all in one component - a natural refactor target if the codebase grows further, though PROGRESS.md's own dead-code pass found no actual dead code, so this is a structure observation, not a correctness one. The production JS bundle is 699 KB (223 KB gzipped) with a "chunk larger than 500kB" warning - Cytoscape.js is the likely bulk; code-splitting or `manualChunks` could help if load time ever matters, but this is pre-existing and known (PROGRESS.md already notes it).
