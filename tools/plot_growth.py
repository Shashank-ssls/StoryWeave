"""Growth charts: how each measured configuration grows with the chapter bookmark.

DELIVERABLE 4 of the measurement harness. Reads the CSVs written by
``tools/graph_metrics.py`` and draws one line per CSV (labelled by its ``label`` column),
so it works unchanged for two configurations or for five.

Produces:
    evidence/plots/nodes_vs_chapter.png
    evidence/plots/density_vs_chapter.png
    evidence/plots/max_degree_vs_chapter.png

Colours are the project's own tokens (``frontend/src/styles/tokens.css``) so the plots sit
beside the screenshots without clashing.

Usage:
    python tools/plot_growth.py --csv evidence/metrics_api_payload.csv \
        --csv evidence/metrics_rendered_view.csv --out evidence/plots/
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: never try to open a window
import matplotlib.pyplot as plt  # noqa: E402

# frontend/src/styles/tokens.css
BG = "#150B0A"
DEEP = "#0C0605"
INK = "#E8D8C2"
DIM = "#A8917D"
LINE = "#3A2420"
ACCENT = "#D9503A"

#: Line colours, in the order CSVs are supplied.
SERIES_COLOURS = (INK, ACCENT, DIM, "#F4C0B0")
SERIES_MARKERS = ("o", "s", "^", "D")

#: (csv column, output filename, axis label, title)
PLOTS: tuple[tuple[str, str, str, str], ...] = (
    (
        "nodes",
        "nodes_vs_chapter.png",
        "visible nodes (count)",
        "Visible nodes vs chapter",
    ),
    (
        "edge_density",
        "density_vs_chapter.png",
        "edge density  2P / (N(N-1)), P = distinct node pairs",
        "Edge density vs chapter",
    ),
    (
        "max_degree",
        "max_degree_vs_chapter.png",
        "highest single-node degree (edges)",
        "Max degree vs chapter",
    ),
)


def read_series(path: Path) -> tuple[str, list[int], dict[str, list[float]]]:
    """(label, chapters, {column: values}) from one metrics CSV."""
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path} has no rows")
    label = rows[0]["label"]
    rows.sort(key=lambda r: int(r["chapter"]))
    chapters = [int(r["chapter"]) for r in rows]
    columns = {
        column: [float(r[column]) for r in rows] for column, _f, _a, _t in PLOTS
    }
    return label, chapters, columns


def draw(
    series: list[tuple[str, list[int], dict[str, list[float]]]],
    column: str,
    ylabel: str,
    title: str,
    out: Path,
) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5), dpi=160)
    fig.patch.set_facecolor(DEEP)
    ax.set_facecolor(BG)

    for index, (label, chapters, columns) in enumerate(series):
        ax.plot(
            chapters,
            columns[column],
            marker=SERIES_MARKERS[index % len(SERIES_MARKERS)],
            color=SERIES_COLOURS[index % len(SERIES_COLOURS)],
            linewidth=2,
            markersize=6,
            label=label,
        )

    ax.set_title(title, color=INK, fontsize=13, pad=12)
    ax.set_xlabel("chapter bookmark (chapters read)", color=INK, fontsize=10)
    ax.set_ylabel(ylabel, color=INK, fontsize=10)
    ax.tick_params(colors=DIM, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(LINE)
    ax.grid(True, color=LINE, linewidth=0.7, alpha=0.7)
    ax.set_axisbelow(True)
    if series:
        ax.set_xticks(series[0][1])

    legend = ax.legend(facecolor=BG, edgecolor=LINE, fontsize=9, labelcolor=INK)
    legend.get_frame().set_alpha(0.95)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="append", required=True, type=Path, help="a metrics CSV (repeatable)")
    ap.add_argument("--out", required=True, type=Path, help="output directory for the plots")
    args = ap.parse_args(argv)

    series = [read_series(path) for path in args.csv]
    labels = ", ".join(s[0] for s in series)
    print(f"plotting {len(series)} series: {labels}")

    for column, filename, ylabel, title in PLOTS:
        out = draw(series, column, ylabel, title, args.out / filename)
        print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
