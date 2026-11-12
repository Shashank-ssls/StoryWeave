"""Assert that nothing in this session's toolchain writes to the C: drive.

Retrofit rule "Local-only environment (HARD RULE - nothing on C:)": every cache,
model, browser and temp directory must live on the project drive. This script is
the gate that proves it, and is meant to be run right after `dev.ps1` / `dev.bat`
and before anything that installs, downloads or pulls a model.

Usage (inside an activated venv):
    python tools/check_local_env.py
    python tools/check_local_env.py --c-drive-report

Exit status is 0 only when every check passes. Stdlib only, so it runs in either
venv without installing anything.

The checking logic is a pure function (`evaluate`) over an injected environment,
so `tests/test_check_local_env.py` can exercise it against fake paths on either
drive without touching this machine's real settings.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Variables whose value must sit inside <repo>\.local\.
IN_LOCAL_VARS: tuple[str, ...] = (
    "PIP_CACHE_DIR",
    "TORCH_HOME",
    "npm_config_cache",
    "PLAYWRIGHT_BROWSERS_PATH",
    "OLLAMA_MODELS",
    "TEMP",
    "TMP",
)

# HF_HOME is the documented exception: the HuggingFace weights live in the
# machine-wide cache F:\Dev\shared\hf-cache, outside the repo but still off C:.
# The rule for it is therefore "exists and is not on C:", not "inside the repo".
OFF_C_VARS: tuple[str, ...] = ("HF_HOME",)

# Caches that would grow on C: if a variable were missing. Reported, never touched.
C_DRIVE_WATCHLIST: tuple[str, ...] = (
    r"~\.cache",
    r"~\AppData\Local\pip",
    r"~\.ollama",
    r"~\AppData\Local\ms-playwright",
    r"~\AppData\Local\Temp",
)


@dataclass(frozen=True)
class CheckResult:
    """One row of the printed table."""

    name: str
    value: str
    ok: bool
    detail: str


def _norm(path: str) -> str:
    """Absolute, normalised, case-folded form, for comparing paths on Windows."""
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def _drive(path: str) -> str:
    return os.path.splitdrive(_norm(path))[0]


def _is_within(child: str, parent: Path) -> bool:
    c, p = _norm(child), _norm(str(parent))
    return c == p or c.startswith(p + os.sep)


def _looks_like_c_drive_path(value: str) -> bool:
    """True only for an explicit C: path; a non-path value like 'true' is not one."""
    drive, _rest = os.path.splitdrive(value)
    return os.path.normcase(drive) == os.path.normcase("c:")


def evaluate(
    env: Mapping[str, str],
    repo_root: Path,
    sys_prefix: str,
    pip_config: Mapping[str, str],
) -> list[CheckResult]:
    """Return one CheckResult per rule. Pure: no filesystem writes, no env reads."""
    results: list[CheckResult] = []
    local_root = repo_root / ".local"

    # 1. The interpreter itself must be one of the repo's two venvs.
    prefix_ok = any(_is_within(sys_prefix, repo_root / name) for name in (".venv", ".venv-ml"))
    results.append(
        CheckResult(
            name="sys.prefix",
            value=sys_prefix,
            ok=prefix_ok,
            detail="in <repo>\\.venv or .venv-ml"
            if prefix_ok
            else "NOT a repo venv - activate via dev.ps1 / dev.bat",
        )
    )

    # 2. Caches that must live under <repo>\.local\.
    for name in IN_LOCAL_VARS:
        value = env.get(name, "")
        if not value:
            results.append(CheckResult(name, "<unset>", False, "not set - run dev.ps1 / dev.bat"))
            continue
        ok = _is_within(value, local_root)
        results.append(
            CheckResult(
                name,
                value,
                ok,
                "inside <repo>\\.local" if ok else f"outside {local_root}",
            )
        )

    # 3. The off-C-but-outside-the-repo exception.
    for name in OFF_C_VARS:
        value = env.get(name, "")
        if not value:
            results.append(CheckResult(name, "<unset>", False, "not set - run dev.ps1 / dev.bat"))
            continue
        exists = Path(value).is_dir()
        off_c = _drive(value) != os.path.normcase("c:")
        ok = exists and off_c
        if not off_c:
            detail = "ON C: - forbidden"
        elif not exists:
            detail = "off C: but directory is missing"
        else:
            detail = "exists, off C: (outside the repo by decision)"
        results.append(CheckResult(name, value, ok, detail))

    # 4. pip's own config must not redirect anything back onto C:.
    for key, value in sorted(pip_config.items()):
        short = key.split(".", 1)[-1]
        if short not in {"cache-dir", "target", "prefix", "user", "build"}:
            continue
        ok = not _looks_like_c_drive_path(value)
        results.append(
            CheckResult(f"pip config {key}", value, ok, "off C:" if ok else "points at C:")
        )
    if not any(r.name.startswith("pip config") for r in results):
        results.append(CheckResult("pip config", "<no path entries>", True, "nothing to redirect"))

    return results


def read_pip_config() -> dict[str, str]:
    """`pip config list` as a dict. A missing or failing pip yields {} (not a failure)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "config", "list"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}
    parsed: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        parsed[key.strip()] = raw.strip().strip("'\"")
    return parsed


def dir_size(path: Path) -> int | None:
    """Total bytes under `path`, or None if it does not exist. Read-only."""
    if not path.exists():
        return None
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda _e: None):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def human(size: int | None) -> str:
    if size is None:
        return "absent"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def format_table(results: Sequence[CheckResult]) -> str:
    name_w = max(len("variable"), *(len(r.name) for r in results))
    value_w = max(len("path"), *(len(r.value) for r in results))
    lines = [
        f"{'variable'.ljust(name_w)}  {'path'.ljust(value_w)}  status  note",
        f"{'-' * name_w}  {'-' * value_w}  ------  ----",
    ]
    for r in results:
        status = "OK  " if r.ok else "FAIL"
        lines.append(f"{r.name.ljust(name_w)}  {r.value.ljust(value_w)}  {status}    {r.detail}")
    return "\n".join(lines)


def ollama_report() -> str:
    """Report only: where ollama is, whether OLLAMA_MODELS is set, and any C: models."""
    lines = ["", "Ollama (report only - nothing is installed, pulled or moved):"]
    found = shutil.which("ollama")
    lines.append(f"  where ollama        : {found or 'not found on PATH'}")
    models = os.environ.get("OLLAMA_MODELS", "")
    lines.append(f"  OLLAMA_MODELS       : {models or '<unset>'}")
    c_models = Path.home() / ".ollama" / "models"
    size = dir_size(c_models)
    lines.append(f"  {c_models}: {human(size)}")
    if size:
        lines.append(
            "  -> Models exist on C:. To move them yourself: stop Ollama, then "
            f'`robocopy "{c_models}" "{os.environ.get("OLLAMA_MODELS", "<OLLAMA_MODELS>")}" '
            "/E /MOVE`. This script never moves or deletes anything."
        )
    return "\n".join(lines)


def c_drive_report() -> str:
    lines = ["", "C: cache baseline (read-only):"]
    for pattern in C_DRIVE_WATCHLIST:
        path = Path(os.path.expanduser(pattern))
        lines.append(f"  {str(path).ljust(52)} {human(dir_size(path))}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify no toolchain path lands on C:.")
    parser.add_argument(
        "--c-drive-report",
        action="store_true",
        help="also print the sizes of the C: cache folders (read-only)",
    )
    args = parser.parse_args(argv)

    results = evaluate(os.environ, REPO_ROOT, sys.prefix, read_pip_config())
    print(f"repo root: {REPO_ROOT}")
    print(format_table(results))
    print(ollama_report())
    if args.c_drive_report:
        print(c_drive_report())

    failures = [r for r in results if not r.ok]
    print()
    if failures:
        print(f"FAIL: {len(failures)} check(s) resolve off the project drive:")
        for r in failures:
            print(f"  - {r.name}: {r.value} ({r.detail})")
        print("Fix by activating with dev.ps1 / dev.bat. Do not work around this.")
        return 1
    print(f"PASS: all {len(results)} checks are on the project drive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
