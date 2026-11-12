# Initialization prompt — paste into a fresh Claude Code session (Sonnet, high effort)

Before pasting: the folder `docs\retrofit\` exists in the repo on F: and holds
README.md, INIT_PROMPT.md, CLAUDE_RETROFIT.md and R0–R8. Not committed yet.

```
You are starting a new work track on StoryWeave: the RETROFIT (v2 fixes applied inside v1).

Everything for this track lives in docs/retrofit/. Read these files in this order before doing anything:
1. docs/retrofit/README.md               — the phase map (R0–R8) and stop conditions
2. docs/retrofit/CLAUDE_RETROFIT.md      — the rules for this track; they override CLAUDE.md where they conflict
3. CLAUDE.md and SETUP_NOTES.md          — existing standing rules and the local F:-drive setup
4. evidence/EVAL_V1.md and FINDINGS.md   — the measured v1 results this track is fixing
   (these live on origin/integration/demo-scale; read them with `git show` if not on your current branch)

HARD RULE: nothing is installed, downloaded or cached on C:. Every venv, pip/npm cache, HuggingFace
model, Ollama model, Playwright browser and temp file stays inside this repo on F:, as listed in the
"Local-only environment" table in CLAUDE_RETROFIT.md. Never use --user, -g, system installers, or change
system/user environment variables. If anything would write to C:, stop and tell me.

Then confirm back to me, briefly:
- the one-line purpose of the retrofit
- the 10 retrofit rules in your own words, one line each
- where each cache and model will live (the local-environment table), and anything currently on C:
  that you can detect (report only; change nothing)
- which files are frozen and must never be modified
- the phase you will run first and its acceptance checklist

Do NOT write or change any code, install anything, or download anything in this message.
After I reply "go", run phase R0 exactly as written in docs/retrofit/R0_branch_and_baseline.md, then stop.

Standing instructions for every later session on this track:
- Start by activating via .\dev.ps1 (or .\dev.ps1 -Ml), running python tools/check_local_env.py,
  reading docs/retrofit/RETROFIT_PROGRESS.md, and stating the current phase.
- One phase per session. Never start the next phase until the current one is green, committed and pushed.
- Every number you write is labelled [MEASURED], [PREDICTED] or [PROJECTED].
- If you hit a stop condition from README.md, stop and report instead of working around it.
```

## For every phase after R0 (fresh session each time)

```
Activate with .\dev.ps1 -Ml (R7: .\dev.ps1), run python tools/check_local_env.py and stop if it fails.
Then read CLAUDE.md, docs/retrofit/RETROFIT_PROGRESS.md and docs/retrofit/R<N>_*.md.
Run phase R<N> exactly as written, then stop.
```
Replace `<N>` with the phase number.
