"""`tools/check_local_env.py` logic, exercised against fake paths.

These tests never read this machine's real environment: `evaluate` is pure and takes
the environment, repo root, interpreter prefix and pip config as arguments, so a
fake F:-style repo and a fake C: leak can both be constructed here.
"""

from __future__ import annotations

from pathlib import Path

from tools.check_local_env import IN_LOCAL_VARS, CheckResult, evaluate, format_table, human

REPO = Path(r"F:\fake\repo")


def _good_env() -> dict[str, str]:
    local = REPO / ".local"
    return {
        "PIP_CACHE_DIR": str(local / "pip_cache"),
        "TORCH_HOME": str(local / "torch_cache"),
        "npm_config_cache": str(local / "npm_cache"),
        "PLAYWRIGHT_BROWSERS_PATH": str(local / "ms-playwright"),
        "OLLAMA_MODELS": str(local / "ollama_models"),
        "TEMP": str(local / "tmp"),
        "TMP": str(local / "tmp"),
        # HF_HOME must be a directory that really exists, so point it at the repo
        # itself: off C:, outside <repo>\.local - exactly the documented exception.
        "HF_HOME": str(Path(__file__).resolve().parents[1]),
    }


def _by_name(results: list[CheckResult]) -> dict[str, CheckResult]:
    return {r.name: r for r in results}


def _run(
    env: dict[str, str], prefix: str | None = None, pip: dict[str, str] | None = None
) -> list[CheckResult]:
    return evaluate(
        env,
        REPO,
        prefix if prefix is not None else str(REPO / ".venv"),
        pip if pip is not None else {},
    )


def test_all_local_paths_pass() -> None:
    results = _run(_good_env())
    assert all(r.ok for r in results), [r for r in results if not r.ok]


def test_ml_venv_prefix_also_passes() -> None:
    results = _run(_good_env(), prefix=str(REPO / ".venv-ml"))
    assert _by_name(results)["sys.prefix"].ok


def test_system_python_prefix_fails() -> None:
    results = _run(_good_env(), prefix=r"C:\Python312")
    assert not _by_name(results)["sys.prefix"].ok


def test_a_venv_outside_the_repo_fails() -> None:
    results = _run(_good_env(), prefix=r"F:\somewhere\else\.venv")
    assert not _by_name(results)["sys.prefix"].ok


def test_each_cache_var_is_checked_independently() -> None:
    for name in IN_LOCAL_VARS:
        env = _good_env()
        env[name] = r"C:\Users\someone\AppData\Local\cache"
        result = _by_name(_run(env))[name]
        assert not result.ok, name


def test_unset_cache_var_fails_with_a_pointer_to_dev_ps1() -> None:
    env = _good_env()
    del env["PIP_CACHE_DIR"]
    result = _by_name(_run(env))["PIP_CACHE_DIR"]
    assert not result.ok
    assert "dev.ps1" in result.detail


def test_off_local_but_off_c_still_fails_for_local_only_vars() -> None:
    env = _good_env()
    env["TORCH_HOME"] = r"F:\elsewhere\torch"
    assert not _by_name(_run(env))["TORCH_HOME"].ok


def test_hf_home_may_live_outside_the_repo() -> None:
    result = _by_name(_run(_good_env()))["HF_HOME"]
    assert result.ok
    assert "outside the repo" in result.detail


def test_hf_home_on_c_drive_fails() -> None:
    env = _good_env()
    env["HF_HOME"] = str(Path.home())  # a real directory, but on C:
    result = _by_name(_run(env))["HF_HOME"]
    assert not result.ok
    assert "C:" in result.detail


def test_hf_home_that_does_not_exist_fails() -> None:
    env = _good_env()
    env["HF_HOME"] = r"F:\fake\hf-cache\does-not-exist"
    assert not _by_name(_run(env))["HF_HOME"].ok


def test_pip_config_pointing_at_c_fails() -> None:
    results = _run(_good_env(), pip={"global.cache-dir": r"C:\Users\someone\pipcache"})
    assert not _by_name(results)["pip config global.cache-dir"].ok


def test_pip_config_on_project_drive_passes() -> None:
    results = _run(_good_env(), pip={"user.cache-dir": str(REPO / ".local" / "pip_cache")})
    assert _by_name(results)["pip config user.cache-dir"].ok


def test_non_path_pip_settings_are_ignored() -> None:
    results = _run(_good_env(), pip={"global.timeout": "60"})
    assert all(r.ok for r in results)
    assert "pip config" in _by_name(results)


def test_table_marks_failures() -> None:
    env = _good_env()
    env["TEMP"] = r"C:\Temp"
    table = format_table(_run(env))
    assert "FAIL" in table
    assert r"C:\Temp" in table


def test_human_sizes() -> None:
    assert human(None) == "absent"
    assert human(0) == "0.0 B"
    assert human(2048) == "2.0 KB"
