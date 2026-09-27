"""Performance of the v1 system on this machine.

DELIVERABLE 3 of the v1 evaluation. Everything here is wall-clock or bytes measured in
the process that prints it; nothing is scaled, extrapolated or taken from a previous run.

What is measured
----------------
* **machine** -- OS, CPU, RAM, GPU, Python, torch, and whether CUDA is available.
* **extraction** -- the REAL pipeline. A scratch database is created in a temporary
  directory, the first ``--chapters`` chapters of the-ninth-house sample are ingested
  through ``ingest.pipeline.ingest`` with the work's own ``storyweave.toml``, and then:
    - ``model_load`` -- constructing ``GlinerExtractor`` and forcing the weights in.
    - ``extract_chapter`` -- per chapter, the GLiNER stage over that chapter's chunks,
      i.e. exactly the ``ext.extract(chunk.text)`` loop ``nlp.pipeline.extract_work``
      runs, with the model already loaded. This is the per-chapter number.
    - ``extract_work_total`` -- one call to the real ``extract_work`` over the same
      chapters, so the per-chapter stage timings can be placed against the full
      pipeline (which also clears, persists mentions and runs the work-level
      alias-clustering pass -- those are not per-chapter costs).
* **peak RSS** -- peak working set of THIS process, read from the Win32
  ``GetProcessMemoryInfo`` (``PeakWorkingSetSize``) via ctypes, sampled before the model
  is loaded and again after extraction finishes. No third-party dependency is added.
* **model size on disk** -- per model, the bytes each occupies under the Hugging Face
  cache, which ``storyweave.config`` points at ``<repo>/.hf-cache`` (never C:).
* **database size** -- bytes of each measured database file.
* **API response time** -- median of 10 calls per chapter endpoint, against the real
  FastAPI app over a read-only connection to the populated database.

Requires ``.venv-ml`` for the extraction section (GLiNER + torch). With ``--skip-extraction``
the API and file-size sections run under the light ``.venv``, and the extraction rows are
written as ``not measured`` rather than guessed.

Usage:
    .venv-ml/Scripts/python tools/eval_performance.py --out evidence/performance_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

# Make the repo root importable when run as `python tools/eval_performance.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from storyweave.api.app import API_PREFIX, create_app  # noqa: E402
from storyweave.api.deps import get_repository  # noqa: E402
from storyweave.config import get_settings  # noqa: E402
from tools import swconfig  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "data" / "samples" / "the-ninth-house"

FIELDNAMES: tuple[str, ...] = ("section", "metric", "value", "unit", "detail")

NOT_MEASURED = "not measured"


# --------------------------------------------------------------------------- #
# Machine
# --------------------------------------------------------------------------- #


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def peak_rss_bytes() -> int:
    """Peak working set of this process, in bytes (Windows ``PeakWorkingSetSize``)."""
    counters = _PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.windll.kernel32
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    # K32GetProcessMemoryInfo is kernel32's forwarder for the psapi entry point; it is
    # the one that exists on every supported Windows without an extra DLL dependency.
    fn = kernel32.K32GetProcessMemoryInfo
    fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    fn.restype = wintypes.BOOL
    if not fn(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.PeakWorkingSetSize)


def total_ram_bytes() -> int:
    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return int(status.ullTotalPhys)


def gpu_description() -> str:
    """GPU name + VRAM from the OS, via PowerShell CIM. Falls back to a stated failure."""
    script = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object -Property Name,AdapterRAM,DriverVersion | ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout.strip()
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        parts = []
        for card in data:
            ram = card.get("AdapterRAM")
            # AdapterRAM is a signed 32-bit field and wraps above 4 GB; report it only
            # when it is a plausible positive value, never a corrected guess.
            ram_text = f"{ram / 1024**3:.2f} GiB (Win32_VideoController.AdapterRAM)" if (
                isinstance(ram, int) and ram > 0
            ) else "VRAM not reported by Win32_VideoController"
            parts.append(f"{card.get('Name')} [{ram_text}, driver {card.get('DriverVersion')}]")
        return "; ".join(parts) if parts else NOT_MEASURED
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"{NOT_MEASURED}: PowerShell CIM query failed ({type(exc).__name__})"


def cpu_description() -> str:
    name = os.environ.get("PROCESSOR_IDENTIFIER", "")
    try:
        script = (
            "Get-CimInstance Win32_Processor | "
            "Select-Object -Property Name,NumberOfCores,NumberOfLogicalProcessors,"
            "MaxClockSpeed | ConvertTo-Json -Compress"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout.strip()
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        card = data[0]
        return (
            f"{card.get('Name')} — {card.get('NumberOfCores')} cores / "
            f"{card.get('NumberOfLogicalProcessors')} threads, "
            f"max {card.get('MaxClockSpeed')} MHz"
        )
    except Exception:  # pragma: no cover - environment dependent
        return name or NOT_MEASURED


def dir_size_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #


def section_machine(rows: list[dict[str, object]]) -> None:
    def add(metric: str, value: object, unit: str = "", detail: str = "") -> None:
        rows.append({"section": "machine", "metric": metric, "value": value,
                     "unit": unit, "detail": detail})

    add("os", platform.platform())
    add("os_version", platform.version())
    add("cpu", cpu_description())
    add("cpu_count_logical", os.cpu_count() or NOT_MEASURED, "threads")
    add("ram_total", total_ram_bytes(), "bytes",
        f"{total_ram_bytes() / 1024**3:.2f} GiB")
    add("gpu", gpu_description())
    add("python", platform.python_version(), "", sys.executable)
    try:
        import torch

        add("torch", torch.__version__)
        add("torch_cuda_available", torch.cuda.is_available(), "",
            "the configured extraction device is read from storyweave.config")
    except ImportError:
        add("torch", NOT_MEASURED, "", "torch is not importable in this interpreter")
        add("torch_cuda_available", NOT_MEASURED, "", "torch not importable")


def section_files(rows: list[dict[str, object]], databases: list[Path]) -> None:
    def add(metric: str, value: object, unit: str = "", detail: str = "") -> None:
        rows.append({"section": "files", "metric": metric, "value": value,
                     "unit": unit, "detail": detail})

    for db in databases:
        if db.is_file():
            add(f"database:{db.name}", db.stat().st_size, "bytes", str(db.resolve()))
        else:
            add(f"database:{db.name}", NOT_MEASURED, "", f"file absent: {db.resolve()}")

    hf_home = Path(get_settings().hf_home)
    hub = hf_home / "hub"
    if not hub.is_dir():
        add("model_cache", NOT_MEASURED, "",
            f"no Hugging Face hub cache at {hub} — no model weights are on disk")
        return
    add("model_cache_total", dir_size_bytes(hub), "bytes", str(hub))
    for entry in sorted(hub.iterdir()):
        if entry.is_dir() and entry.name.startswith("models--"):
            repo_id = entry.name.removeprefix("models--").replace("--", "/")
            add(f"model:{repo_id}", dir_size_bytes(entry), "bytes", str(entry))


def section_api(
    rows: list[dict[str, object]], db: Path, slug: str, chapters: list[int], calls: int
) -> None:
    """Median wall-clock per chapter endpoint, `calls` repetitions each."""
    def add(metric: str, value: object, unit: str = "", detail: str = "") -> None:
        rows.append({"section": "api", "metric": metric, "value": value,
                     "unit": unit, "detail": detail})

    repo = swconfig.open_readonly(db)
    try:
        app = create_app()
        app.dependency_overrides[get_repository] = lambda: repo
        client = TestClient(app)
        base = f"{API_PREFIX}/works/{slug}"
        endpoints = ("entities", "graph", "arcs")
        for name in endpoints:
            for chapter in chapters:
                url = f"{base}/{name}"
                params = {"n": chapter}
                client.get(url, params=params).raise_for_status()  # warm-up, not timed
                samples: list[float] = []
                for _ in range(calls):
                    start = time.perf_counter()
                    response = client.get(url, params=params)
                    samples.append((time.perf_counter() - start) * 1000.0)
                    response.raise_for_status()
                add(
                    f"{name}@n={chapter}",
                    round(statistics.median(samples), 3), "ms",
                    f"median of {calls} calls; min {min(samples):.3f} "
                    f"max {max(samples):.3f}; {slug}",
                )
    finally:
        repo.close()


def section_extraction(
    rows: list[dict[str, object]], chapter_limit: int, workdir: Path
) -> None:
    """The real extraction pipeline on a scratch database, timed per chapter."""
    from storyweave.db.repository import Repository
    from storyweave.ingest.pipeline import ingest as run_ingest
    from storyweave.ingest.work_config import load_work_config
    from storyweave.nlp.pipeline import build_extractor, extract_work

    def add(metric: str, value: object, unit: str = "", detail: str = "") -> None:
        rows.append({"section": "extraction", "metric": metric, "value": value,
                     "unit": unit, "detail": detail})

    settings = get_settings()
    cfg = load_work_config(SAMPLE_DIR / "storyweave.toml")
    # The per-work toml leaves these None, meaning "use the global Settings default";
    # report the EFFECTIVE values the extractor will actually run with.
    effective_threshold = (
        cfg.extraction.threshold
        if cfg.extraction.threshold is not None
        else settings.gliner_threshold
    )
    add(
        "gliner_model",
        cfg.extraction.model or settings.gliner_model,
        "",
        f"device={cfg.extraction.device or settings.gliner_device}, "
        f"threshold={effective_threshold}"
        f"; per-work toml overrides: "
        f"model={cfg.extraction.model}, device={cfg.extraction.device}, "
        f"threshold={cfg.extraction.threshold}",
    )

    # Only the first `chapter_limit` chapter files, copied into the scratch source dir.
    source = workdir / "chapters"
    source.mkdir(parents=True)
    files = sorted(SAMPLE_DIR.glob("ch*.txt"))[:chapter_limit]
    for f in files:
        (source / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    add("chapters_measured", len(files), "chapters", ", ".join(f.name for f in files))

    db_path = workdir / "perf.sqlite"
    with Repository(db_path) as repo:
        repo.initialize_schema()
        start = time.perf_counter()
        report = run_ingest(source, repo, cfg, slug="perf-ninth-house",
                            title="Perf Ninth House")
        ingest_s = time.perf_counter() - start
        add("ingest_total", round(ingest_s, 4), "s", report.summary())
        work_id = report.work_id

        rss_before_model = peak_rss_bytes()
        add("peak_rss_before_model_load", rss_before_model, "bytes",
            f"{rss_before_model / 1024**2:.1f} MiB")

        cache_state = "warm" if (Path(settings.hf_home) / "hub").is_dir() else "cold"
        start = time.perf_counter()
        extractor = build_extractor(cfg, settings)
        extractor.extract("A warm-up sentence naming Sorrel in the Ninth House.")
        load_s = time.perf_counter() - start
        add("model_load", round(load_s, 4), "s",
            f"GlinerExtractor construction + first inference; Hugging Face cache was "
            f"{cache_state} at the start of this run (a cold cache includes the download)")

        rss_after_model = peak_rss_bytes()
        add("peak_rss_after_model_load", rss_after_model, "bytes",
            f"{rss_after_model / 1024**2:.1f} MiB")

        # Per-chapter GLiNER stage, model already loaded.
        per_chapter: list[float] = []
        for chapter in repo.list_chapters(work_id):
            assert chapter.id is not None
            chunks = repo.list_chunks(chapter.id)
            chars = len(chapter.clean_text)
            start = time.perf_counter()
            spans = 0
            for chunk in chunks:
                spans += len(extractor.extract(chunk.text))
            elapsed = time.perf_counter() - start
            per_chapter.append(elapsed)
            add(f"extract_chapter:ch{chapter.ordinal:02d}", round(elapsed, 4), "s",
                f"{len(chunks)} chunks, {chars} chars, {spans} raw spans")
        add("extract_chapter_median", round(statistics.median(per_chapter), 4), "s",
            f"over {len(per_chapter)} chapters")
        add("extract_chapter_mean", round(statistics.fmean(per_chapter), 4), "s",
            f"over {len(per_chapter)} chapters")
        add("extract_chapter_min", round(min(per_chapter), 4), "s")
        add("extract_chapter_max", round(max(per_chapter), 4), "s")

        # The real end-to-end call, reusing the already-loaded extractor.
        start = time.perf_counter()
        extract_report = extract_work(work_id, repo, cfg, settings, extractor=extractor)
        work_s = time.perf_counter() - start
        add("extract_work_total", round(work_s, 4), "s", extract_report.summary())
        add("extract_work_per_chapter", round(work_s / len(files), 4), "s",
            f"extract_work_total / {len(files)} chapters (model already loaded)")

        rss_peak = peak_rss_bytes()
        add("peak_rss_after_extraction", rss_peak, "bytes",
            f"{rss_peak / 1024**2:.1f} MiB — peak working set of the whole process")
        add("scratch_db_size", db_path.stat().st_size, "bytes",
            f"{len(files)} chapters ingested + extracted (scratch DB, then deleted)")


def section_extraction_skipped(rows: list[dict[str, object]], reason: str) -> None:
    rows.append({"section": "extraction", "metric": "all", "value": NOT_MEASURED,
                 "unit": "", "detail": reason})


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="storyweave-demo.sqlite", type=Path)
    ap.add_argument("--baseline-db", default=Path("evidence/v1_ninth_house.db"), type=Path)
    ap.add_argument("--slug", default="the-ninth-house")
    ap.add_argument("--chapters", default="10,20,30,40")
    ap.add_argument("--calls", default=10, type=int, help="repetitions per API endpoint")
    ap.add_argument("--extract-chapters", default=5, type=int,
                    help="how many chapters of the sample to actually extract")
    ap.add_argument("--skip-extraction", action="store_true")
    ap.add_argument("--out", default=Path("evidence/performance_v1.csv"), type=Path)
    args = ap.parse_args(argv)

    chapters = [int(c) for c in args.chapters.split(",") if c.strip()]
    rows: list[dict[str, object]] = []

    section_machine(rows)
    section_api(rows, args.db, args.slug, chapters, args.calls)

    if args.skip_extraction:
        section_extraction_skipped(rows, "--skip-extraction was passed")
    else:
        with tempfile.TemporaryDirectory(prefix="storyweave-perf-") as tmpdir:
            section_extraction(rows, args.extract_chapters, Path(tmpdir))

    # File sizes last, so the model cache is measured AFTER any download extraction
    # triggered — otherwise a cold cache would be reported as an absent model.
    section_files(rows, [args.db, args.baseline_db, Path(get_settings().db_path)])

    width = max(len(f"{r['section']}.{r['metric']}") for r in rows)
    current = ""
    for row in rows:
        if row["section"] != current:
            current = str(row["section"])
            print(f"\n=== {current} ===")
        key = f"{row['section']}.{row['metric']}".ljust(width)
        unit = f" {row['unit']}" if row["unit"] else ""
        detail = f"   ({row['detail']})" if row["detail"] else ""
        print(f"{key}  {row['value']}{unit}{detail}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(FIELDNAMES))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {args.out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
