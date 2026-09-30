# C: drive ledger

Every write this project has made to `C:`, with what made it, when, and how to undo it.
The "nothing on C:" rule in `CLAUDE_RETROFIT.md` is only auditable if the exceptions are
written down, so this file is the exception list.

**Audited 2026-09-29** on branch `retrofit/v2-core`, by direct filesystem and registry
inspection. Every size and timestamp below is **[MEASURED]**, read off the machine, not
estimated. Nothing was deleted or modified during the audit.

**Total attributable to this project: 280,593 bytes (0.27 MB) of files, plus 2 Start Menu
shortcuts and 1 registry uninstall key.** No service, no scheduled task, no firewall rule, no HKLM
change. The user-PATH entry (item 7) was **removed on 2026-09-29** — see §2.5.

**Open items: 1, 2, 3, 4, 6. Retired: 5, 7.**

> **Honesty note.** Two of the entries below were NOT in my earlier report of the Ollama
> install, and are recorded here because the audit found them, not because they were
> expected: the `%LOCALAPPDATA%\Ollama` log/database folder (277 KB), and the persistent
> **user PATH edit**. I had previously stated ollama was "not on PATH"; that was true of
> the already-running shell, and wrong about the registry. See §2.5.

---

## 1. Summary table

| # | What | Where | Size | Created by | Date |
| --- | --- | --- | ---: | --- | --- |
| 1 | keypair + recommendations cache | `C:\Users\space\.ollama\` | 2,284 B | Ollama tray app, first run | 2026-09-29 |
| 2 | app logs + local sqlite | `C:\Users\space\AppData\Local\Ollama\` | 276,845 B | Ollama tray app + server | 2026-09-29 |
| 3 | Start Menu folder + shortcut | `%APPDATA%\...\Start Menu\Programs\Ollama\` | 732 B | `OllamaSetup.exe` | 2026-09-29 |
| 4 | Start Menu shortcut | `%APPDATA%\...\Start Menu\Programs\Ollama.lnk` | 732 B | `OllamaSetup.exe` | 2026-09-29 |
| 5 | ~~Startup shortcut (auto-start)~~ — **REMOVED 2026-09-29**, see §5 | `%APPDATA%\...\Programs\Startup\Ollama.lnk` | — | `OllamaSetup.exe` | 2026-09-29 |
| 6 | Uninstall registry key | `HKCU\...\Uninstall\{44E83376-...}_is1` | key | `OllamaSetup.exe` | 2026-09-29 |
| 7 | ~~User PATH entry `F:\Tools\Ollama`~~ — **REMOVED 2026-09-29** | `HKCU\Environment\Path` | — | `OllamaSetup.exe` | 2026-09-29 |
| 8 | Claude Code session data | `C:\Users\space\.claude\projects\F--Dev-...-StoryWeave\` | 118.35 MB | Claude Code harness | 2026-06-21 |
| 9 | Claude Code scratchpad | `%LOCALAPPDATA%\Temp\claude\F--Dev-...-StoryWeave\` | 2.64 MB | Claude Code harness | 2026-09-27 |

Items 8 and 9 are **harness-managed, not written by the project's own code or by
`dev.ps1`**. They are listed for completeness and are NOT removed by the uninstall
script — deleting item 8 would destroy this project's conversation history.

### Items 8 and 9 grow with session length — [MEASURED] 2026-09-29

| | at the first audit | later the same day | delta |
| --- | ---: | ---: | ---: |
| 8, `.claude\projects\F--Dev-…-StoryWeave` | 118.35 MB | **121.1 MB** | **+2.75 MB** |
| 9, `%LOCALAPPDATA%\Temp\claude\…` | 2.64 MB | **9.02 MB** | **+6.4 MB** |

**These two are the only C: items this project causes to grow during a working session**,
and the growth is Claude Code's transcript and scratchpad storage, not anything the
pipeline writes. Recorded here because the rule is that every C: write is recorded, not
because either is a defect.

Checked at the same moment, for contrast: **Ollama wrote nothing to C: during the entire
R5 LLM run** — `.ollama` and `%LOCALAPPDATA%\Ollama` were byte-identical to items 1 and 2
above, with no file modified since 11:26, while the run itself was making hundreds of
model calls. The weights (4.47 GB) and the LLM response cache both stayed on F:.
`.ollama\models`, `Ollama\models` and `.ollamalobs` are all **absent**.

For scale, the largest C: consumers measured at the same time were **not this project**:
`AppData\Local\Google` 3.87 GB, `.vscode` 1.94 GB, `AppData\Local\Packages` 676 MB,
`.dartServer` 531 MB. C: had 114.4 GB free.

---

## 2. Ollama install — detail and removal

Installed 2026-09-29 from `F:\Tools\OllamaSetup.exe` (downloaded 1,498.3 MB) with
`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=F:\Tools\Ollama`. **The program itself
(2,826.1 MB) and all models (4,466.1 MB, `qwen2.5:7b`) are on F: and are not in this
ledger.** Only the C: spill is.

### 2.1 `C:\Users\space\.ollama\` — 2,284 bytes

| file | size | what it is |
| --- | ---: | --- |
| `id_ed25519` | 387 B | Ollama's client identity keypair (private) |
| `id_ed25519.pub` | 81 B | the public half |
| `cache\model-recommendations.json` | 1,816 B | a catalogue blob the tray app fetched |

**No model data.** The `models\blobs` / `models\manifests` subtree the tray app created
was **already deleted on 2026-09-29** (recorded here so a future audit does not look for
it); it was empty, because `OLLAMA_MODELS` was redirected to F: before any pull.

*Remove:* `Remove-Item "$env:USERPROFILE\.ollama" -Recurse -Force`. Ollama regenerates the
keypair on next run; nothing is lost but the client identity.

### 2.2 `C:\Users\space\AppData\Local\Ollama\` — 276,845 bytes

`app.log` (120,572 B), `server.log` (4,012 B), `db.sqlite` + `-shm` + `-wal`
(152,256 B), `ollama.pid` (5 B). Logs and a small local database. **This is the largest
single item and was not previously reported.**

*Remove:* `Remove-Item "$env:LOCALAPPDATA\Ollama" -Recurse -Force` (with ollama stopped).

### 2.3 Start Menu entries — 2,232 bytes total

Three `.lnk` files, all targeting `F:\Tools\Ollama\ollama app.exe`:

- `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Ollama.lnk` (732 B)
- `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Ollama\Ollama.lnk` (732 B, plus the
  containing folder)
- `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Ollama.lnk` (768 B) — **see §5**

*Remove:* delete the three paths (the uninstaller also does this).

### 2.4 Uninstall registry key

```
HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{44E83376-CE68-45EB-8FC1-393500EB558C}_is1
  DisplayName     : Ollama version 0.34.4
  InstallLocation : F:\Tools\Ollama\
  UninstallString : "F:\Tools\Ollama\unins000.exe"
  EstimatedSize   : 2,893,654 KB
```

**Nothing in HKLM** (checked both the 64-bit and `WOW6432Node` views), and no
`HKCU\Software\Ollama` or `HKLM\Software\Ollama`.

*Remove:* run `F:\Tools\Ollama\unins000.exe`, which removes the key, the shortcuts and the
program directory together. This is the preferred full removal.

### 2.5 User PATH — the one persistent environment change

`HKCU\Environment\Path` now ends with an added entry:

```
F:\Tools\Ollama
```

**Before/after:** a literal before-image was not captured (the installer ran before this
audit existed), so this is inferred rather than measured — but the inference is tight:
the entry points at a directory that did not exist before 2026-09-29, it is the **last**
element of the value, and `HKLM` machine PATH does **not** contain it. The rest of the
user PATH is pre-existing and untouched.

This matters for two reasons:

1. It is a **persistent user environment variable change**, which the local-only rule in
   `CLAUDE_RETROFIT.md` otherwise forbids. It was made by the installer, not by
   `dev.ps1`, and it is recorded here rather than quietly accepted.
2. It explains an earlier wrong statement of mine. `where ollama` failed *in the already
   running shell* (whose PATH was captured before the install), so I reported ollama was
   not on PATH. It is — in every **new** shell.

#### Status: REMOVED 2026-09-29 — [MEASURED]

Removed with `tools/uninstall_project_c_traces.ps1 -Only 7 -Apply`, after a dry run of the
same command printed the before/after. The raw value was backed up first to
`.local\hkcu_path_backup_20260929.txt` (989 chars, on F:, gitignored).

| | before | after |
| --- | ---: | ---: |
| PATH elements | 32 | **31** |
| contains `F:\Tools\Ollama` | yes | **no** |
| value kind | `ExpandString` (REG_EXPAND_SZ) | **`ExpandString`** — preserved |

Exactly one element changed. The other 31 — including the two empty elements the value
already contained — were written back byte-for-byte; the script filters on an exact match
and never rebuilds the list. Reading and writing through
`RegistryValueOptions::DoNotExpandEnvironmentNames` is what keeps `REG_EXPAND_SZ` from
being flattened into a literal `REG_SZ` with today's `%USERPROFILE%` baked in.

**Verified in two genuinely new shells** (`Start-Process powershell -NoProfile -File`):

```
NEW shell WITHOUT dev.ps1 :  NOT FOUND
NEW shell WITH .\dev.ps1  :  FOUND F:\Tools\Ollama\ollama.exe
```

That is the intended end state: ollama is reachable only inside a `dev.ps1` session, where
`OLLAMA_MODELS` also points at F:. Items 1–6 were confirmed untouched by the same run.

*Restore, if ever needed:* re-append `F:\Tools\Ollama` to `HKCU\Environment\Path`, or
restore the whole value from the backup file above.

**No `OLLAMA_*` variables were persisted.** `OLLAMA_MODELS` is set per-session by
`dev.ps1` / `dev.bat` only, which is what keeps models on F:.

### 2.6 Confirmed absent

Checked and **not present**: Windows service, scheduled task, firewall rule,
`%LOCALAPPDATA%\Programs\Ollama`, HKLM uninstall entry (either view), `HKCU`/`HKLM`
`Software\Ollama`, any `Run` key entry (the only `Run` value is a pre-existing Steam one),
any Ollama entry in the machine PATH.

---

## 3. NOT created by this project — never delete these

These predate this work. They are listed **so they are never removed by mistake**, and the
uninstall script does not touch them.

| What | Where | Size | Created |
| --- | --- | ---: | --- |
| Chrome DevTools MCP browser cache | `C:\Users\space\.cache\chrome-devtools-mcp\` | 135.60 MB | 2026-05-25 |
| tldextract suffix-list cache | `C:\Users\space\.cache\python-tldextract\` | 0.16 MB | 2026-06-22 |

Together these are the **135.8 MB** figure recorded as the C: baseline in
`evidence/retrofit/R0_local_paths.md` and re-verified unchanged at R0, R3, R4 and R4b.
**This project did not create them and has never written to them.** Both are dated months
before the retrofit branch existed.

Also pre-existing and unrelated: `C:\Users\space\.local\bin`, the Oracle/Java, NVIDIA,
dotnet, Python-launcher and WinGet PATH entries, and the Steam `Run` key.

Confirmed still **absent**, as the local-only rule requires: `%LOCALAPPDATA%\pip`,
`%LOCALAPPDATA%\ms-playwright`, `%APPDATA%\npm`.

---

## 4. Removal

`tools/uninstall_project_c_traces.ps1` removes **only** items 1–7. It is **dry-run by
default** and requires `-Apply` to change anything. It has **not** been run with `-Apply`.

```powershell
.\tools\uninstall_project_c_traces.ps1                 # dry run, all items
.\tools\uninstall_project_c_traces.ps1 -Only 7         # dry run, one item
.\tools\uninstall_project_c_traces.ps1 -Only 7 -Apply  # remove that one item
.\tools\uninstall_project_c_traces.ps1 -Apply          # remove everything in the ledger
```

`-Only <id>` restricts the run to the given ledger item(s); everything else prints as
`skipped (out of scope)`. Retiring one item at a time is the normal case — the ledger is
a list of independent traces, not a single all-or-nothing install. Item 7 was retired this
way on 2026-09-29, and the run confirmed items 1–6 untouched.

For a complete removal of Ollama including the F: program directory, prefer the vendor
uninstaller `F:\Tools\Ollama\unins000.exe`, then run this script to sweep the C: leftovers
it leaves behind (`.ollama` and `%LOCALAPPDATA%\Ollama` survive a normal uninstall).

---

## 5. Item 5 — the Startup shortcut: REMOVED 2026-09-29

**Status: removed.** `tools/uninstall_project_c_traces.ps1 -Only 5 -Apply`, after the
same command dry-ran first. Verified: the file is gone and the Startup folder now holds
only `desktop.ini`. Items 1, 2, 3, 4, 6 were re-checked immediately afterwards and are
all still present — the `-Only` scope held.

Ollama no longer auto-starts at login, so it can no longer come up in a context without
`OLLAMA_MODELS` set and default to `C:\Users\space\.ollama\models`. Start it deliberately
instead:

```powershell
.\dev.ps1          # sets OLLAMA_MODELS to .local\ollama_models on F: and PATHs ollama
ollama serve
```

### Why it was removed rather than disabled — [MEASURED]

A Task Manager disable was attempted first and **did not take effect**. Probed before
removal, across all six approval locations:

| probe | result |
| --- | --- |
| `StartupApproved\StartupFolder`, HKCU | key exists, **0 values** |
| `StartupApproved\StartupFolder`, HKLM | key exists, **0 values** |
| `StartupApproved\Run` / `Run32`, HKCU + HKLM | 3 / 0 / 2 / 1 values, **none matching `*llama*`** |
| the shortcut file | present, attributes `Archive`, `LastWriteTime` still 2026-09-29 11:09:31 (install time) |

Disabling a Startup-**folder** item writes a value named for the shortcut into
`HKCU\...\Explorer\StartupApproved\StartupFolder` with bit 0 of the first byte set. No
such value existed, so the toggle had not applied. Deleting the shortcut is the
unambiguous equivalent and is what the ledger now records.

*Restore, if ever wanted:* recreate a shortcut to `F:\Tools\Ollama\ollama app.exe` in
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`, or re-run the vendor
installer. The two Start Menu shortcuts (items 3 and 4) are untouched, so Ollama is still
launchable from the Start Menu by hand.

---

## Re-audit at the end of phase R7 — 2026-09-29, [MEASURED]

R7 touched the frontend and one SQL method. It installed nothing, downloaded nothing and
pulled no model, so no ledger item was added.

| item | at the R6 check | at the R7 check | verdict |
| --- | ---: | ---: | --- |
| 1 `C:\Users\space\.ollama\` | 2,284 B | **2,284 B** | byte-identical |
| 2 `%LOCALAPPDATA%\Ollama\` | 276,845 B | **276,845 B** | byte-identical |
| 5 Startup shortcut | removed | **still absent** | stays removed |
| 7 `HKCU\Environment\Path` entry | removed | **still absent** | stays removed |
| 8 `.claude\projects\…` | 121.1 MB | **134.8 MB** | Claude Code harness, grows with the session |
| 9 `%LOCALAPPDATA%\Temp\claude\…` | 9.02 MB | **4.44 MB** | scratchpad, shrank |

Checked for and did not find any new C: cache this phase: `%LOCALAPPDATA%\pip\Cache`,
`C:\Users\space\.cache\huggingface`, `%APPDATA%\npm-cache` and
`%LOCALAPPDATA%\ms-playwright` are all **absent**. The R7 screenshot harness runs
`playwright-core` against the system Chrome from `.local\pw\` on F:, which is exactly why
no browser was downloaded to either drive.

---

## Re-audit 2026-09-30 — the Playwright-browsers question, answered — [MEASURED]

This session fixed frontend defects and ran the Playwright suite. It **installed nothing,
downloaded nothing and pulled no model**, so no ledger item was added.

### Why `.local\ms-playwright` is empty, and always was

The session started from the belief that R7's 101 passing Playwright tests implied a
browser download that had since gone missing. That belief was wrong, and the evidence is
already in this file (the closing paragraph of the R7 re-audit above).

| checked | found |
| --- | --- |
| `.local\ms-playwright` on F: | exists, **0 MB**, holds only `.links` |
| `.local\ms-playwright\.links` | one registry link -> `frontend\node_modules\playwright-core` |
| `%LOCALAPPDATA%\ms-playwright` | **absent** |
| `C:\ProgramData\ms-playwright` | **absent** |
| `PLAYWRIGHT_BROWSERS_PATH`, every reference in the repo | `<repo>\.local\ms-playwright`, never a C: path |

`frontend/playwright.config.ts` sets `channel: "chrome"`, which drives the machine's
installed Chrome (`C:\Program Files\Google\Chrome`) instead of a Playwright-managed
download — its own comment says the bundled Chromium download is blocked on this network.
So **no browser was ever downloaded to either drive**, the empty directory is the
*expected* state, and the suite runs from it unchanged: **`1 skipped, 101 passed (3.0m)`**
and again **`1 skipped, 101 passed (3.1m)`**, two consecutive runs at `--workers=1`.

No Chromium was therefore installed into `.local\ms-playwright`. Installing one would
have downloaded ~140 MB that the config does not use, so the download was not made.

### One C: directory found that this project did not create

| What | Where | Size | Created | Likely creator |
| --- | --- | ---: | --- | --- |
| `ms-playwright-go` | `C:\Users\space\AppData\Local\ms-playwright-go` | **0 bytes, empty** | 2026-06-04 (modified 2026-07-16) | `playwright-go`, a Go binding unrelated to this repo |

It is **empty**, it predates the retrofit branch by three months, and this repo contains
no Go code and no `playwright-go` dependency. It is recorded here because the rule is that
everything found on C: is written down — it belongs in §3 ("NOT created by this project"),
**not** in the removable items 1–7, and `tools/uninstall_project_c_traces.ps1` was
deliberately **not** extended to cover it: that script removes only traces this project
made, and deleting another tool's directory is not its job. Say the word and it can be
added, or simply removed by hand.

### Item check

| item | at the R7 check | at this check | verdict |
| --- | ---: | ---: | --- |
| 1 `C:\Users\space\.ollama\` | 2,284 B | **2,284 B** | byte-identical |
| 2 `%LOCALAPPDATA%\Ollama\` | 276,845 B | **276,845 B** | byte-identical |
| 5 Startup shortcut | removed | **still absent** | stays removed |
| 7 `HKCU\Environment\Path` entry | removed | **still absent** | stays removed |
| 8 `.claude\projects\...` | 134.8 MB | **153.98 MB** | Claude Code harness, grows with the session |
| 9 `%LOCALAPPDATA%\Temp\claude\...` | 4.44 MB | **5.02 MB** | scratchpad |

Confirmed still absent: `%LOCALAPPDATA%\pip\Cache`, `C:\Users\space\.cache\huggingface`,
`%APPDATA%\npm-cache`, `%LOCALAPPDATA%\ms-playwright`.

The pre-existing Chrome DevTools MCP browser cache (§3) has grown on its own from
135.60 MB to **144.72 MB**. It is not this project's — it is the MCP browser the harness
drives — and it is listed here only so the next audit does not read the change as new.

