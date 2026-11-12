# R0 — local-environment lock-down and the C: baseline

**Purpose.** Prove that nothing this track downloads, caches, builds or unpacks lands on
the C: drive, and record the C: sizes *now* so every later phase can show they did not
grow. Read-only: nothing here deletes or moves anything.

Date: 2026-09-28 · branch `retrofit/v2-core` · commit `0202df1` (branch point).
Gate: `tools/check_local_env.py`, stdlib only, run after `dev.ps1`. Exit code 0 = pass.
Logs: `evidence/retrofit/logs/R0_check_local_env_venv.log`, `…_venv_ml.log`.

---

## 1. Gate result, `.venv` (light) — [MEASURED]

```
repo root: F:\Dev\Claude_folder_project_and_stuff\StoryWeave
variable                    path                                                                     status  note
--------------------------  -----------------------------------------------------------------------  ------  ----
sys.prefix                  F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.venv                  OK      in <repo>\.venv or .venv-ml
PIP_CACHE_DIR               F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\pip_cache       OK      inside <repo>\.local
TORCH_HOME                  F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\torch_cache     OK      inside <repo>\.local
npm_config_cache            F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\npm_cache       OK      inside <repo>\.local
PLAYWRIGHT_BROWSERS_PATH    F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\ms-playwright   OK      inside <repo>\.local
OLLAMA_MODELS               F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\ollama_models   OK      inside <repo>\.local
TEMP                        F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\tmp             OK      inside <repo>\.local
TMP                         F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\tmp             OK      inside <repo>\.local
HF_HOME                     F:\Dev\shared\hf-cache                                                   OK      exists, off C: (outside the repo by decision)
pip config :env:.cache-dir  F:\\Dev\\Claude_folder_project_and_stuff\\StoryWeave\\.local\\pip_cache  OK      off C:

PASS: all 10 checks are on the project drive.
```

## 2. Gate result, `.venv-ml` (heavy) — [MEASURED]

Identical table with `sys.prefix = F:\…\StoryWeave\.venv-ml`, verbatim:

```
sys.prefix                  F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.venv-ml               OK      in <repo>\.venv or .venv-ml
…
PASS: all 10 checks are on the project drive.
```

Full output: `evidence/retrofit/logs/R0_check_local_env_venv_ml.log`.

---

## 3. What R0 changed to make that true

`dev.ps1` and `dev.bat` previously set only `PIP_CACHE_DIR`, `TORCH_HOME` and
`PLAYWRIGHT_BROWSERS_PATH`. They now also set `npm_config_cache`, `OLLAMA_MODELS`,
`TEMP`, `TMP` and `HF_HOME`, and create the `.local\…` directories if missing. All of it
is session scope (`$env:` / `set`); **no system or user environment variable is written**,
and `.local\` stays gitignored.

`TEMP`/`TMP` mattered most: they were on C: (`C:\Users\space\AppData\Local\Temp`), which is
where pip builds wheels and where torch and HuggingFace unpack archives. Anything large
this track installs would have passed through C: even with every cache variable correct.

### The one deliberate exception: `HF_HOME`

`HF_HOME = F:\Dev\shared\hf-cache` — on F:, but **outside** the repo. The GLiNER,
deberta-v3-small and gliner-relex weights are already there (verified: `hub/models--*`
directories for all three), and the repo's own `.hf-cache/` is empty. Repointing
`HF_HOME` into the repo would split the cache and force a ~1 GB re-download of weights
that are already on the project drive, for no gain against the actual rule, which is
"nothing on C:".

So the gate's rule for `HF_HOME` is deliberately weaker than for the rest: **must exist
and must not be on C:**, rather than must be inside `<repo>\.local`. Every other cache
must be inside `<repo>\.local`, and the gate fails a path that is merely elsewhere on F:.
The cache table in `CLAUDE.md` (retrofit block) was updated to record this path.

Note for later phases: `storyweave/config.py` still *defaults* `hf_home` to
`<repo>\.hf-cache`. That default is now dead in practice — `configure_hf_cache()` uses
`os.environ.setdefault`, so the explicit `HF_HOME` from `dev.ps1` wins for any process
started from an activated shell. `storyweave/` was off-limits in R0, so the default was
left alone; a phase that is allowed to touch `storyweave/` should align it.

---

## 4. C: baseline — [MEASURED]

Sizes at R0, read-only (`tools/check_local_env.py --c-drive-report`). Later phases compare
against this table; any growth in rows 1–4 is a violation of the local-only rule.

| path | size at R0 |
| --- | ---: |
| `C:\Users\space\.cache` | 135.8 MB |
| `C:\Users\space\AppData\Local\pip` | absent |
| `C:\Users\space\.ollama` | absent |
| `C:\Users\space\AppData\Local\ms-playwright` | absent |
| `C:\Users\space\AppData\Local\Temp` | 92.3 MB |

Three of the four watched caches **do not exist at all**: no pip cache, no Ollama models,
no Playwright browsers on C:. The two non-zero rows are not StoryWeave's:

- `.cache` is 135.6 MB `chrome-devtools-mcp` plus 0.2 MB `python-tldextract` — both
  belong to the editor/agent tooling, not to this project, and predate the track.
- `AppData\Local\Temp` is the OS temp directory, shared by everything on the machine.
  It is now bypassed by this project (`TEMP` → `<repo>\.local\tmp`), so it should stay
  flat from here on. It is the one row expected to drift for reasons outside the project;
  the meaningful rows are 1–4.

`AppData\Local\Temp` is also listed in the gate's watchlist for exactly this reason: it is
the cache that silently grows when a variable is missed.

---

## 5. Ollama — report only, nothing installed — [MEASURED]

```
  where ollama        : not found on PATH
  OLLAMA_MODELS       : F:\Dev\Claude_folder_project_and_stuff\StoryWeave\.local\ollama_models
  C:\Users\space\.ollama\models: absent
```

Ollama is **not installed on this machine** and no models exist on C:, so there is nothing
to move. `OLLAMA_MODELS` is set in advance, so that *if* R5 ever runs, `ollama pull`
writes into the repo. Nothing was installed, pulled or moved in R0, per rule I3/R5's
optionality.

If Ollama is installed later, it must be installed with `OLLAMA_MODELS` already set by
`dev.ps1`; the gate will fail the moment that variable is missing. Should models ever end
up under `C:\Users\space\.ollama\models`, the gate prints the exact `robocopy … /E /MOVE`
command to relocate them — it never moves anything itself.

---

## 6. The gate is tested — [MEASURED]

`tests/test_check_local_env.py`, 15 tests, `15 passed in 0.04s`. `evaluate()` is a pure
function over an injected environment, so the tests run against a fake `F:\fake\repo` and
a fake C: leak without reading this machine's real settings. They cover: a system Python
prefix, a venv outside the repo, each of the seven `.local` variables individually
poisoned to C:, an unset variable, a path that is off C: but outside `.local`, `HF_HOME`
on C:, `HF_HOME` pointing at a directory that does not exist, a `pip config` entry
redirecting to C:, and a non-path pip setting that must be ignored.
