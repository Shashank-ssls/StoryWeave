"""One command: measure, capture, verify, plot, and write evidence/REPORT.md.

DELIVERABLE 5 of the measurement harness. Runs every other tool in order, cross-checks the
live DOM counts against the computed metrics, and writes the report.

REPORT.md carries MEASURED VALUES ONLY. Anything that could not be computed is written as
"not measured". There is no interpretation and no estimate anywhere in the generated text.

Usage:
    python tools/run_evidence.py --db storyweave-demo.sqlite --url http://127.0.0.1:8000 \
        --slug the-ninth-house --focus Sorrel --chapters 10,20,30,40
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import capture as capture_mod  # noqa: E402
from tools import graph_metrics, plot_growth, swconfig, verify_shots  # noqa: E402
from tools.swconfig import (  # noqa: E402
    API_PAYLOAD,
    CONFIGS,
    FILTER_DESCRIPTIONS,
    RENDERABLE_CAST,
    RENDERED_EVERYONE,
    RENDERED_VIEW,
)

NOT_MEASURED = "not measured"


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
        head = out.stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"{head}{' (working tree dirty at run time)' if dirty else ''}"
    except (subprocess.CalledProcessError, OSError):
        return NOT_MEASURED


def require_server(url: str) -> None:
    probe = f"{url.rstrip('/')}/api/v1/health"
    try:
        with urllib.request.urlopen(probe, timeout=10) as resp:  # noqa: S310
            payload = json.load(resp)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise SystemExit(
            f"cannot reach the app at {probe} ({exc}).\n"
            "Start it first, e.g.:  .\\run.ps1 -SkipBuild"
        ) from exc
    if payload.get("status") != "ok":
        raise SystemExit(f"{probe} reports status={payload.get('status')!r}: {payload}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cross_check(
    shots: list[dict[str, Any]], rows_by_label: dict[str, list[dict[str, str]]]
) -> list[str]:
    """Compare every shot's live DOM counts against the computed metrics.

    A disagreement is a bug in the harness or in the app, so it is returned as a problem
    and the run fails -- never silently tolerated.
    """
    problems: list[str] = []
    for shot in shots:
        label, chapter = shot["label"], int(shot["chapter"])
        rows = rows_by_label.get(label, [])
        row = next((r for r in rows if int(r["chapter"]) == chapter), None)
        if row is None:
            problems.append(f"{label} ch{chapter}: no metrics row to cross-check against")
            continue
        if int(row["nodes"]) != shot["dom_nodes"] or int(row["edges"]) != shot["dom_edges"]:
            problems.append(
                f"{label} ch{chapter} ({shot['view']}): DOM nodes/edges "
                f"{shot['dom_nodes']}/{shot['dom_edges']} != CSV "
                f"{row['nodes']}/{row['edges']}"
            )
    return problems


# --- report ------------------------------------------------------------------- #

TABLE_COLUMNS = (
    ("chapter", "chapter"),
    ("nodes", "nodes"),
    ("edges", "edges"),
    ("mean_degree", "mean deg"),
    ("median_degree", "median deg"),
    ("max_degree", "max deg"),
    ("edge_density", "density"),
    ("isolated_nodes", "isolated"),
    ("degree1_nodes", "degree-1"),
)


def metrics_table(rows: list[dict[str, str]]) -> str:
    header = "| " + " | ".join(title for _k, title in TABLE_COLUMNS) + " |"
    rule = "| " + " | ".join("---" for _ in TABLE_COLUMNS) + " |"
    body = [
        "| " + " | ".join(row[key] for key, _t in TABLE_COLUMNS) + " |"
        for row in sorted(rows, key=lambda r: int(r["chapter"]))
    ]
    return "\n".join([header, rule, *body])


def breakdown_table(path: Path) -> str:
    if not path.is_file():
        return f"_{NOT_MEASURED}_"
    rows = read_rows(path)
    if not rows:
        return f"_{NOT_MEASURED}_"
    key = "node_type" if "node_type" in rows[0] else "relation"
    chapters = sorted({int(r["chapter"]) for r in rows})
    keys = sorted({r[key] for r in rows})
    lookup = {(int(r["chapter"]), r[key]): r["count"] for r in rows}
    header = f"| {key} | " + " | ".join(f"ch {c}" for c in chapters) + " |"
    rule = "| --- | " + " | ".join("---" for _ in chapters) + " |"
    body = []
    for name in keys:
        counts = [lookup.get((c, name), "0") for c in chapters]
        if all(v == "0" for v in counts):
            continue
        body.append(f"| {name} | " + " | ".join(counts) + " |")
    return "\n".join([header, rule, *body])


def write_report(
    out: Path,
    db: Path,
    slug: str,
    chapters: list[int],
    focus: str,
    rows_by_label: dict[str, list[dict[str, str]]],
    shots: list[dict[str, Any]],
    plates: list[Path],
    plots: list[Path],
    evidence_dir: Path,
    commit: str,
    chapter_count: int,
) -> None:
    def rel(path: Path) -> str:
        return path.relative_to(evidence_dir).as_posix()

    lines: list[str] = []
    add = lines.append

    add("# StoryWeave — graph density evidence")
    add("")
    add(f"Work: `{slug}` · chapters measured: {', '.join(str(c) for c in chapters)} "
        f"of {chapter_count} · generated by `tools/run_evidence.py`.")
    add("")
    add("All values below are measured. Nothing here is estimated or interpreted; a value "
        f"that could not be computed is written as \"{NOT_MEASURED}\".")
    add("")

    add("## Metrics")
    add("")
    for config in CONFIGS:
        rows = rows_by_label.get(config)
        add(f"### `{config}`")
        add("")
        if not rows:
            add(f"_{NOT_MEASURED}_")
            add("")
            continue
        add(metrics_table(rows))
        add("")
        add("Node counts by type:")
        add("")
        add(breakdown_table(evidence_dir / f"metrics_{config}_by_node_type.csv"))
        add("")
        add("Edge counts by relation:")
        add("")
        add(breakdown_table(evidence_dir / f"metrics_{config}_by_relation.csv"))
        add("")

    add("## Comparison plates")
    add("")
    if plates:
        add(f"Left: `{RENDERED_VIEW}`. Right: `{RENDERED_EVERYONE}`. Full-graph view, no focus.")
        add("")
        for plate in plates:
            chapter = plate.stem.replace("compare_ch", "").lstrip("0")
            add(f"**Chapter {chapter}**")
            add("")
            add(f"![{plate.stem}]({rel(plate)})")
            add("")
    else:
        add(f"_{NOT_MEASURED}_")
        add("")

    add("## Growth plots")
    add("")
    if plots:
        for plot in plots:
            add(f"![{plot.stem}]({rel(plot)})")
            add("")
    else:
        add(f"_{NOT_MEASURED}_")
        add("")

    add("## Live DOM cross-check")
    add("")
    add("Node and edge counts read from the live Cytoscape instance at the moment each "
        "screenshot was taken, against the computed metrics for the same configuration "
        "and chapter.")
    add("")
    add("| label | chapter | view | DOM nodes | DOM edges | CSV nodes | CSV edges | match | zoom |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for shot in shots:
        rows = rows_by_label.get(shot["label"], [])
        row = next((r for r in rows if int(r["chapter"]) == int(shot["chapter"])), None)
        csv_nodes = row["nodes"] if row else NOT_MEASURED
        csv_edges = row["edges"] if row else NOT_MEASURED
        counts_agree = (
            bool(row)
            and int(csv_nodes) == shot["dom_nodes"]
            and int(csv_edges) == shot["dom_edges"]
        )
        match = "yes" if counts_agree else "NO"
        add(
            f"| {shot['label']} | {shot['chapter']} | {shot['view']} | {shot['dom_nodes']} | "
            f"{shot['dom_edges']} | {csv_nodes} | {csv_edges} | {match} | {shot['zoom']:.4f} |"
        )
    add("")

    add("## Measurement conditions")
    add("")
    add("**Both configurations come from the same codebase and the same database. "
        "No rebuilt system has been measured. There is no \"v2\" in this run — "
        "these are two points in one pipeline, not two versions of the app.**")
    add("")
    add(f"- Repository commit (identical for every configuration measured here): `{commit}`")
    add(f"- Database: `{db.name}` (opened `mode=ro`; never written by this harness)")
    add(f"- Work measured: `{slug}` — every figure is scoped to this work alone")
    add(f"- Chapters: {', '.join(str(c) for c in chapters)} (of {chapter_count})")
    add(f"- Viewport: {capture_mod.VIEWPORT['width']}x{capture_mod.VIEWPORT['height']} CSS px "
        f"at deviceScaleFactor {capture_mod.DEVICE_SCALE_FACTOR} "
        f"(PNG {verify_shots.EXPECTED_SIZE[0]}x{verify_shots.EXPECTED_SIZE[1]})")
    add(
        '- Browser: Chromium via Playwright `channel="chrome"` '
        "(system Chrome; no browser downloaded)"
    )
    add(f"- Ego-view focus node: `{focus}`")
    add("")
    add("### Filters active per configuration")
    add("")
    for config in CONFIGS:
        add(f"- **`{config}`** — {FILTER_DESCRIPTIONS[config]}")
    add("")
    add("### Parameters the task asked for that do not exist in this codebase")
    add("")
    add(f"- **Salience rank / salience cast size:** {NOT_MEASURED}. There is no salience "
        "ranking in this codebase. The only cast control is the Stemma's two-state toggle "
        f"(`principal` / `everyone`), measured as `{RENDERED_VIEW}` and "
        f"`{RENDERED_EVERYONE}`; it takes a mode, not a size.")
    add(f"- **Disparity filter alpha:** {NOT_MEASURED}. No disparity or backbone filter "
        "exists in this codebase, so no alpha was in effect.")
    add("")
    add("### Renderability")
    add("")
    add(f"- `{API_PAYLOAD}` is measured in the tables above but has **no screenshot**: the "
        "app has no view that draws the unfiltered payload, so capturing one would have "
        "meant inventing a view that does not exist.")
    for config, cast in RENDERABLE_CAST.items():
        add(f"- `{config}` is rendered with the Stemma cast toggle set to `{cast}`.")
    add("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- main --------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="storyweave-demo.sqlite", type=Path)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--slug", default="the-ninth-house")
    ap.add_argument("--focus", default="Sorrel")
    ap.add_argument("--chapters", default="10,20,30,40")
    ap.add_argument("--evidence", default=REPO_ROOT / "evidence", type=Path)
    args = ap.parse_args(argv)

    chapters = graph_metrics.parse_chapters(args.chapters)
    evidence = args.evidence
    shots_dir = evidence / "shots"
    plates_dir = evidence / "plates"
    plots_dir = evidence / "plots"

    require_server(args.url)

    # 1. metrics for every configuration.
    print("== metrics ==")
    rows_by_label: dict[str, list[dict[str, str]]] = {}
    for config in CONFIGS:
        out = evidence / f"metrics_{config}.csv"
        rows, by_type, by_relation = graph_metrics.collect(
            args.db, config, config, args.slug, chapters
        )
        graph_metrics.write_csv(rows, out)
        stem = out.with_suffix("")
        graph_metrics.write_breakdown_csv(
            by_type, "node_type", config, config, Path(f"{stem}_by_node_type.csv")
        )
        graph_metrics.write_breakdown_csv(
            by_relation, "relation", config, config, Path(f"{stem}_by_relation.csv")
        )
        rows_by_label[config] = read_rows(out)
        print(f"  {config}: {len(rows)} rows -> {out}")

    # 2. capture every renderable configuration.
    print("== capture ==")
    shots: list[dict[str, Any]] = []
    for config, cast in RENDERABLE_CAST.items():
        captured = capture_mod.capture(
            args.url, config, args.slug, args.focus, chapters, shots_dir, cast
        )
        shots.extend(json.loads(json.dumps([s.__dict__ for s in captured])))

    # 3. verify images + build plates.
    print("== verify ==")
    rc = verify_shots.main(
        [
            "--shots", str(shots_dir),
            "--out", str(plates_dir),
            "--left", RENDERED_VIEW,
            "--right", RENDERED_EVERYONE,
            "--chapters", args.chapters,
            "--report", str(evidence / "shot_checks.csv"),
        ]
    )
    if rc != 0:
        raise SystemExit("image verification FAILED — not writing REPORT.md")

    # 4. plots.
    print("== plots ==")
    plot_args: list[str] = []
    for config in CONFIGS:
        plot_args += ["--csv", str(evidence / f"metrics_{config}.csv")]
    plot_growth.main([*plot_args, "--out", str(plots_dir)])

    # 5. cross-check the live DOM against the metrics.
    print("== cross-check ==")
    problems = cross_check(shots, rows_by_label)
    if problems:
        for problem in problems:
            print(f"  MISMATCH: {problem}")
        raise SystemExit(
            f"{len(problems)} DOM/CSV mismatch(es) — this is a bug, not a rounding "
            "difference. REPORT.md not written."
        )
    print(f"  all {len(shots)} shots agree with the computed metrics")

    # 6. report.
    repo = swconfig.open_readonly(args.db)
    try:
        work = repo.get_work_by_slug(args.slug)
        chapter_count = len(repo.list_chapters(work.id)) if work and work.id else 0
    finally:
        repo.close()

    plates = sorted(plates_dir.glob("compare_ch*.png"))
    plots = [plots_dir / name for _c, name, _a, _t in plot_growth.PLOTS]
    report = evidence / "REPORT.md"
    write_report(
        report, args.db, args.slug, chapters, args.focus, rows_by_label, shots,
        plates, plots, evidence, git_commit(), chapter_count,
    )
    print(f"\nwrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
