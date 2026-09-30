"""Regenerate every figure in ``evidence/retrofit/figures/``: six PNGs, six CSVs.

**Nothing here re-extracts anything.** Every number is read from an artifact that already
exists in the repository:

* the frozen v1 database ``evidence/v1_ninth_house.db`` (opened strictly read-only,
  through ``tools/swconfig.open_readonly``);
* the final retrofit database ``data/retrofit/ninth_house_r6.db``;
* the reference annotation ``evidence/annotation/ch{09,17,37}.json``, via the SAME
  loader, validator, normaliser, matcher and projections the scorer uses
  (``tools/eval_score.py``) -- none of that logic is re-implemented here;
* the per-relation counts already written to ``evidence/retrofit/*_scores_*.csv``;
* the recall-accounting and pre-registered-band tables in the phase result documents,
  transcribed as literals below with the file and section each came from.

Every figure caption carries **[MEASURED]**, the path of this script, and an ``n`` on
every bar or cell.

Run from the repo root in the LIGHT venv (``.\\dev.ps1``), which is where matplotlib is
installed::

    python tools/make_figures.py

``--only entity_confusion`` (repeatable) regenerates a subset.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # no display on this machine; never open a window
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import swconfig  # noqa: E402
from tools.eval_score import (  # noqa: E402
    CHAPTERS,
    SLUG,
    load_v1,
    match_entities,
    project_to_graph_types,
    project_to_twelve_relations,
    validate,
)

#: A confusion matrix: (gold label, predicted label) -> count.
CellCounts = Counter[tuple[str, str]]

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_DB = REPO_ROOT / "evidence" / "v1_ninth_house.db"
FINAL_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r6.db"
ANNOTATION_DIR = REPO_ROOT / "evidence" / "annotation"
SCORES = REPO_ROOT / "evidence" / "retrofit"
OUT = REPO_ROOT / "evidence" / "retrofit" / "figures"

SCRIPT = "tools/make_figures.py"

# The Codex palette, so the figures sit beside the app's own screenshots. Plot on a light
# background: these go into a document that is read, and printed, not into the dark UI.
INK = "#231512"
ACCENT = "#B23A22"
MUTED = "#8A7768"
GRID = "#D9CEC1"
PAPER = "#FBF7F1"

plt.rcParams.update({
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
    "font.family": "serif",
    "font.serif": ["Georgia", "DejaVu Serif"],
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.edgecolor": MUTED,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.grid": False,
})


def caption(fig: Any, text: str) -> None:
    """One caption line per figure: [MEASURED] + what it is + where it came from."""
    fig.text(0.005, 0.005, f"[MEASURED] {text}  ·  source: {SCRIPT}",
             fontsize=7, color=MUTED, ha="left", va="bottom")


def save(fig: Any, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.relative_to(REPO_ROOT)}")
    return path


def write_csv(name: str, header: list[str], rows: list[list[Any]]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {path.relative_to(REPO_ROOT)}")
    return path


# --------------------------------------------------------------------------- #
# shared loading
# --------------------------------------------------------------------------- #

def load_side(db: Path, four_type: bool, twelve_relation: bool,
              grade: str = "all", exclude: tuple[str, ...] = ()
              ) -> tuple[dict[int, Any], dict[int, Any]]:
    """(annotations, per-chapter DB view) under one answer key.

    The projections mutate the annotation in place, exactly as the scorer's `main` does,
    so each side gets its own freshly validated copy of the reference.
    """
    annotations: dict[int, Any] = {}
    for chapter in CHAPTERS:
        ann = validate(chapter, ANNOTATION_DIR)
        if four_type:
            project_to_graph_types(ann, chapter)
        if twelve_relation:
            project_to_twelve_relations(ann, chapter)
        annotations[chapter] = ann
    repo = swconfig.open_readonly(db)
    try:
        work = repo.get_work_by_slug(SLUG)
        if work is None or work.id is None:
            raise ValueError(f"work {SLUG!r} not found in {db}")
        side = load_v1(repo, work.id, CHAPTERS, grade=grade, exclude_methods=exclude)
    finally:
        repo.close()
    return annotations, side


# --------------------------------------------------------------------------- #
# 1. entity confusion
# --------------------------------------------------------------------------- #

MISSED = "missed"
SPURIOUS = "spurious"


def entity_confusion_counts(db: Path, four_type: bool) -> tuple[CellCounts, list[str], list[str]]:
    """Counter over (gold type, predicted type), pooled across the three chapters.

    Built from `match_entities` (strict), whose `pairs` require name AND type to agree,
    whose `name_only` is the same-name-different-type case, and whose leftovers are the
    two margins:

    * gold entity with no counterpart and no same-name candidate -> (gold, "missed")
    * predicted node with no counterpart and no same-name gold   -> ("spurious", pred)
    """
    annotations, side = load_side(db, four_type=four_type, twelve_relation=False)
    cells: CellCounts = Counter()
    gold_types: set[str] = set()
    pred_types: set[str] = set()
    for chapter in CHAPTERS:
        ann, view = annotations[chapter], side[chapter]
        match = match_entities(view, ann, alias_aware=False)
        for entity in ann.scored_entities:
            gold_types.add(str(entity["type"]))
        for node_id in view.names:
            pred_types.add(view.types[node_id])

        # agreed on both name and type
        for ref_i in match.pairs.values():
            t = str(ann.scored_entities[ref_i]["type"])
            cells[(t, t)] += 1

        # same name, different type: the type-disagreement cells
        gold_typed: set[int] = set()
        pred_typed: set[int] = set()
        for node_id, ref_i in match.name_only:
            if ref_i in match.reverse or ref_i in gold_typed or node_id in pred_typed:
                continue
            gold = str(ann.scored_entities[ref_i]["type"])
            cells[(gold, view.types[node_id])] += 1
            gold_typed.add(ref_i)
            pred_typed.add(node_id)

        # margins
        for ref_i in match.false_negatives:
            if ref_i in gold_typed:
                continue
            cells[(str(ann.scored_entities[ref_i]["type"]), MISSED)] += 1
        for node_id in match.false_positives:
            if node_id in pred_typed:
                continue
            cells[(SPURIOUS, view.types[node_id])] += 1
    return cells, sorted(gold_types), sorted(pred_types)


def draw_matrix(ax: Any, cells: CellCounts, rows: list[str], cols: list[str], title: str,
                unit: str = "entity") -> int:
    grid = np.array([[cells.get((r, c), 0) for c in cols] for r in rows], dtype=float)
    total = int(grid.sum())
    vmax = max(grid.max(), 1)
    # Colour by count, but the NUMBER is the datum — every cell is annotated, zeros too.
    ax.imshow(np.where(grid > 0, grid, np.nan), cmap="pink_r", aspect="auto",
              vmin=0, vmax=vmax)
    ax.set_xticks(range(len(cols)), cols, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(rows)), rows, fontsize=8)
    ax.set_xlabel(f"predicted {unit}", fontsize=9)
    ax.set_ylabel(f"gold {unit}", fontsize=9)
    ax.set_title(f"{title}\nn = {total} {unit} decisions", fontsize=10, pad=10)
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = int(grid[i, j])
            # The darkest cells of `pink_r` are near-black, so the count has to flip to
            # paper or the largest number in the figure is the one nobody can read.
            dark = v / vmax > 0.6
            ax.text(j, i, str(v), ha="center", va="center", fontsize=8,
                    color=(PAPER if dark else INK) if v else GRID,
                    fontweight="bold" if v and rows[i] == cols[j] else "normal")
    ax.set_xticks(np.arange(-0.5, len(cols), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(rows), 1), minor=True)
    ax.grid(which="minor", color=GRID, linewidth=0.6)
    ax.tick_params(which="minor", length=0)
    return total


def fig_entity_confusion() -> None:
    print("entity_confusion")
    v1_cells, v1_gold, v1_pred = entity_confusion_counts(V1_DB, four_type=False)
    fi_cells, fi_gold, fi_pred = entity_confusion_counts(FINAL_DB, four_type=True)

    v1_rows = v1_gold + [SPURIOUS]
    v1_cols = v1_pred + [MISSED]
    fi_rows = fi_gold + [SPURIOUS]
    fi_cols = fi_pred + [MISSED]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    n1 = draw_matrix(axes[0], v1_cells, v1_rows, v1_cols, "v1 — scored on the 8-type key")
    n2 = draw_matrix(axes[1], fi_cells, fi_rows, fi_cols, "final — scored on the 4-type key")
    fig.suptitle("Entity type confusion, pooled over chapters 9 / 17 / 37",
                 fontsize=12, y=0.99)
    # The two panels are DIFFERENT answer keys. Said on the figure, not just in prose.
    fig.text(0.5, 0.935,
             "Two different answer keys — the panels are not a before/after delta.",
             ha="center", fontsize=8.5, color=ACCENT, style="italic")
    caption(fig, f"left n={n1}, right n={n2} entity decisions; "
                 "reference = evidence/annotation (model-generated, see PROVENANCE.md)")
    fig.tight_layout(rect=(0, 0.03, 1, 0.91))
    save(fig, "entity_confusion")

    rows: list[list[Any]] = []
    for panel, cells, rr, cc in (("v1_8type", v1_cells, v1_rows, v1_cols),
                                 ("final_4type", fi_cells, fi_rows, fi_cols)):
        for r in rr:
            for c in cc:
                rows.append([panel, r, c, cells.get((r, c), 0)])
    write_csv("entity_confusion", ["panel", "gold_type", "predicted_type", "n"], rows)


# --------------------------------------------------------------------------- #
# 2. relation confusion
# --------------------------------------------------------------------------- #

NONE = "NONE"


def fig_relation_confusion() -> None:
    print("relation_confusion")
    annotations, side = load_side(FINAL_DB, four_type=True, twelve_relation=True,
                                  grade="all", exclude=("curated",))
    cells: CellCounts = Counter()
    gold_rels: set[str] = set()
    pred_rels: set[str] = set()

    for chapter in CHAPTERS:
        ann, view = annotations[chapter], side[chapter]
        match = match_entities(view, ann, alias_aware=False)
        edges = view.edges_cumulative  # the pooled `cumulative` variant, as R5 §3 reports

        # predicted edges keyed by endpoint pair, both orders, so a gold relation can be
        # paired with a predicted edge that named the SAME pair a DIFFERENT relation —
        # which is the only thing an off-diagonal cell can mean.
        by_pair: dict[frozenset[int], list[tuple[int, int, str, int]]] = defaultdict(list)
        for e in edges:
            by_pair[frozenset({e[0], e[1]})].append(e)

        ref_index = {str(e["name"]): i for i, e in enumerate(ann.scored_entities)}
        used: set[tuple[int, int, str]] = set()
        for relation in ann.scored_relations:
            rel = str(relation["relation"])
            gold_rels.add(rel)
            si = ref_index.get(str(relation["source"]))
            ti = ref_index.get(str(relation["target"]))
            src = match.reverse.get(si) if si is not None else None
            tgt = match.reverse.get(ti) if ti is not None else None
            if src is None or tgt is None:
                # endpoints v1/final never found: the relation is a miss with no
                # predicted counterpart at all.
                cells[(rel, NONE)] += 1
                continue
            directed = bool(relation.get("directed", True))
            hit = None
            for e in by_pair.get(frozenset({src, tgt}), []):
                key = (e[0], e[1], e[2])
                if key in used:
                    continue
                if directed and (e[0], e[1]) != (src, tgt):
                    continue
                hit = e
                break
            if hit is None:
                cells[(rel, NONE)] += 1
            else:
                used.add((hit[0], hit[1], hit[2]))
                cells[(rel, hit[2])] += 1
                pred_rels.add(hit[2])

        # predicted edges nothing in the gold set claimed: the spurious row
        for e in edges:
            if (e[0], e[1], e[2]) in used:
                continue
            cells[(NONE, e[2])] += 1
            pred_rels.add(e[2])

    rows = sorted(gold_rels) + [NONE]
    cols = sorted(pred_rels) + [NONE]

    fig, ax = plt.subplots(figsize=(9.5, 7.2))
    n = draw_matrix(ax, cells, rows, cols,
                    "final system, 12-relation key, pooled ch 9 / 17 / 37 (`cumulative`)",
                    unit="relation")
    diag = sum(cells.get((r, r), 0) for r in rows if r != NONE)
    fp = sum(v for (g, pr), v in cells.items() if g == NONE)
    fig.suptitle("Relation confusion", fontsize=12)
    # The requested caption was "0 true positives". That is the STATED-only figure
    # (0 TP / 10 FP, R5_RESULT.md §3). This matrix is the configuration the graph
    # actually SERVES since the rule-4 amendment — STATED **and** INFERRED — which the
    # same table measures at 1 TP / 25 FP, and that is what the cells below add up to.
    # The sentence therefore says what is drawn, and names the stricter number too.
    fig.text(0.5, 0.925,
             f"{diag} true positive of 23 gold relations ({fp} false positives); "
             "shown to locate losses, not to claim accuracy.",
             ha="center", fontsize=9, color=ACCENT, style="italic")
    fig.text(0.5, 0.902,
             "Served grades (STATED + INFERRED), per the rule-4 amendment. "
             "STATED only is 0 TP / 10 FP — R5_RESULT.md §3.",
             ha="center", fontsize=8, color=MUTED, style="italic")
    caption(fig, f"n={n} relation decisions, of which {diag} on the diagonal; "
                 "curated seed edges excluded; row NONE = spurious, column NONE = missed")
    fig.tight_layout(rect=(0, 0.02, 1, 0.885))
    save(fig, "relation_confusion")

    write_csv("relation_confusion", ["gold_relation", "predicted_relation", "n"],
              [[r, c, cells.get((r, c), 0)] for r in rows for c in cols])


# --------------------------------------------------------------------------- #
# 3. recall funnel
# --------------------------------------------------------------------------- #

# Transcribed from the recall-accounting tables in the phase results:
#   R4  -> evidence/retrofit/R4_RESULT.md  (the "stage / n / share" table)
#   R4b -> evidence/retrofit/R4b_RESULT.md ("Recall accounting, R4 -> R4b")
#   R4c -> evidence/retrofit/R4c_RESULT.md ("R4 | R4b | R4c")
#   R5  -> evidence/retrofit/R5_RESULT.md  ("Recall accounting, R4c -> R5")
# Each column sums to the 51 gold relations; the script asserts that below.
FUNNEL_STAGES = [
    ("NOT_IN_THE_TWELVE", "outside the closed list by design"),
    ("NO_PROPOSAL", "endpoints exist, nothing proposed for the pair"),
    ("ENTITY_MISSING", "an endpoint was never created"),
    ("WRONG_TYPE", "the pair was proposed with a different relation"),
    ("VALIDATOR_REJECTED", "proposed, rejected by the validator"),
    ("GRADE_INFERRED", "validated but not STATED"),
    ("FOUND", "present in the shipped graph"),
]
FUNNEL = {
    "R4":  [28, 12, 6, 2, 1, 1, 1],
    "R4b": [28, 18, 0, 2, 1, 1, 1],
    "R4c": [28, 18, 0, 2, 1, 1, 1],
    "R5":  [28, 17, 0, 2, 1, 2, 1],
}
GOLD_RELATIONS = 51


def fig_recall_funnel() -> None:
    print("recall_funnel")
    phases = list(FUNNEL)
    for p, col in FUNNEL.items():
        assert sum(col) == GOLD_RELATIONS, (p, sum(col))

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(phases))
    bottom = np.zeros(len(phases))
    shades = plt.cm.pink(np.linspace(0.15, 0.85, len(FUNNEL_STAGES)))
    for i, (stage, _why) in enumerate(FUNNEL_STAGES):
        vals = np.array([FUNNEL[p][i] for p in phases], dtype=float)
        ax.bar(x, vals, bottom=bottom, width=0.62, label=stage,
               color=shades[i], edgecolor=INK, linewidth=0.6)
        for xi, (v, b) in enumerate(zip(vals, bottom, strict=True)):
            if v:  # n on every segment
                ax.text(xi, b + v / 2, f"{int(v)}", ha="center", va="center",
                        fontsize=8.5, color=INK)
        bottom += vals

    for xi in range(len(phases)):
        ax.text(xi, GOLD_RELATIONS + 0.8, f"n = {GOLD_RELATIONS}", ha="center",
                fontsize=8.5, color=MUTED)
    ax.set_xticks(x, phases)
    ax.set_ylim(0, GOLD_RELATIONS + 4)
    ax.set_ylabel("gold relations")
    ax.set_title("Where all 51 gold relations go, by phase", fontsize=12)
    ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)
    caption(fig, "n=51 gold relations at every phase; "
                 "transcribed from R4/R4b/R4c/R5_RESULT.md recall-accounting tables")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "recall_funnel")

    write_csv("recall_funnel", ["phase", "stage", "n", "of_total"],
              [[p, s, FUNNEL[p][i], GOLD_RELATIONS]
               for p in phases for i, (s, _) in enumerate(FUNNEL_STAGES)])


# --------------------------------------------------------------------------- #
# 4. phase timeline
# --------------------------------------------------------------------------- #

# (label, scores CSV) on the v1 8-type/15-relation answer key, so the points ARE
# comparable with each other. Phases that did not change the relation build reuse the
# preceding phase's scores and say so in the `note` column of the CSV.
#: The headline figures (micro-F1 0.0459, 162 false positives) are the `chapter_local`
#: variant: relations whose `first_seen_chapter` is the scored chapter. The scorer reports
#: `cumulative` beside it and privileges neither; one is picked here so the six points are
#: comparable, and it is the one the reports quote.
VARIANT = "chapter_local"

TIMELINE_SOURCES = [
    ("v1", "R0_scores_v1", ""),
    ("R1", "R1_scores_rule_off", ""),
    ("R4", "R4_scores_v1key", ""),
    ("R4c", "R4c_scores_v1key", ""),
    ("R5", "R5_scores_v1key", ""),
    ("R7", "r8_scores_final_v1key", "R6 and R7 changed no extraction; "
                                    "the R8 like-for-like rescore is the R7 state"),
]


def pooled_relation_counts(csv_name: str, variant: str = VARIANT) -> tuple[int, int, int, float]:
    """(tp, fp, fn, micro_f1) for one scores CSV, on the `chapter_local` variant.

    The counts are the per-chapter `ALL` rows summed over ch 9/17/37 — which is how the
    headline "162 false positives" is arrived at (102 + 42 + 18). The F1 is **read from
    the file's own `pooled` row**, not recomputed here: the scorer is the authority on its
    own metric, and a figure that re-derives it could silently disagree with the report.
    """
    tp = fp = fn = 0
    f1: float | None = None
    path = SCORES / f"{csv_name}.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 6 or row[1] != "relation" or row[2] != variant or row[3] != "ALL":
                continue
            if row[0] == "pooled":
                if row[4] == "micro_f1":
                    f1 = float(row[5])
                continue
            if row[4] == "tp":
                tp += int(row[5])
            elif row[4] == "fp":
                fp += int(row[5])
            elif row[4] == "fn":
                fn += int(row[5])
    if f1 is None:
        raise ValueError(f"no pooled micro_f1 for variant {variant!r} in {path}")
    return tp, fp, fn, f1


def fig_phase_timeline() -> None:
    print("phase_timeline")
    labels, fps, f1s, tps, fns, notes = [], [], [], [], [], []
    for label, csv_name, note in TIMELINE_SOURCES:
        tp, fp, fn, f1 = pooled_relation_counts(csv_name)
        labels.append(label)
        tps.append(tp)
        fps.append(fp)
        fns.append(fn)
        f1s.append(f1)
        notes.append(note)

    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(len(labels))
    ax.bar(x, fps, width=0.55, color="#E3CDBE", edgecolor=INK, linewidth=0.7,
                  label="false positives")
    for xi, v in zip(x, fps, strict=True):
        ax.text(float(xi), v + max(fps) * 0.02, f"n = {v}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(x, labels)
    ax.set_ylabel("relation false positives")
    ax.set_ylim(0, max(fps) * 1.18)

    ax2 = ax.twinx()
    ax2.plot(x, f1s, color=ACCENT, marker="o", linewidth=1.8, label="micro-F1")
    # Five of the six F1 values are exactly 0.0000 and five of the six bars are 7 or
    # shorter, so both series crowd the axis floor and their labels collided (measured by
    # looking at the PNG). Headroom UNDER the F1 line separates them: the bottom of the
    # right-hand axis is padded below zero, exactly as the left-hand axis is padded above
    # its tallest bar. The padding is blank space, not a claim that F1 can be negative —
    # the ticks are set explicitly from 0 up so no negative value is ever printed.
    top = max(max(f1s) * 1.9, 0.08)
    ax2.set_ylim(-top * 0.34, top)
    ax2.set_yticks([t for t in np.arange(0, top + 1e-9, 0.02)])
    for xf, vf in zip(x, f1s, strict=True):
        # A paper-coloured halo: the steep v1 -> R1 segment otherwise runs through the
        # leading digit of R1's label. Cheaper and more robust than nudging one label.
        ax2.annotate(f"{vf:.4f}", (float(xf), vf), textcoords="offset points", xytext=(0, 11),
                     ha="center", fontsize=8.5, color=ACCENT, zorder=5,
                     path_effects=[pe.withStroke(linewidth=3, foreground=PAPER)])
    ax2.set_ylabel("relation micro-F1 (v1 key)", color=ACCENT)
    ax2.tick_params(axis="y", colors=ACCENT)

    ax.set_title("Relation false positives and micro-F1, v1 through R7\n"
                 f"(one answer key throughout: v1's, `{VARIANT}`, pooled ch 9/17/37)",
                 fontsize=11)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8.5, frameon=False, loc="upper right")
    caption(fig, "n on every bar = pooled false positives; "
                 "read from evidence/retrofit/*_scores_*.csv")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "phase_timeline")

    write_csv("phase_timeline", ["phase", "tp", "fp", "fn", "micro_f1", "source_csv", "note"],
              [[labels[i], tps[i], fps[i], fns[i], f"{f1s[i]:.6f}",
                TIMELINE_SOURCES[i][1] + ".csv", notes[i]] for i in range(len(labels))])


# --------------------------------------------------------------------------- #
# 5. predictions vs measured
# --------------------------------------------------------------------------- #

# The 19 pre-registered bands, transcribed from evidence/retrofit/PROJECTION_CHECK.md,
# plus the withdrawn headline projection from its §0 (marked, and drawn differently).
# (label, low, high, measured, verdict, phase). `high is None` = a point target, not a band.
BANDS: list[tuple[str, float | None, float | None, float | None, str, str]] = [
    ("relation micro-F1 (withdrawn)",        0.20, 0.35, 0.0000, "WITHDRAWN", "R1"),
    ("STATED micro-F1",                      0.05, 0.20, 0.0000, "OUT", "R4"),
    ("ring-1 edges @ch40",                   4,    25,   4,      "IN",  "R4c"),
    ("ring-2 edges @ch40",                   60,   150,  64,     "IN",  "R4c"),
    ("STATED micro-F1",                      0.05, 0.25, 0.0000, "OUT", "R4c"),
    ("ring-1 edges @ch40, STATED",           5,    25,   4,      "OUT", "R5"),
    ("default-view edges @ch40",             3,    15,   1,      "OUT", "R5"),
    ("STATED micro-F1",                      0.05, 0.30, 0.0000, "OUT", "R5"),
    ("STATED precision",                     0.50, 0.90, 0.0000, "OUT", "R5"),
    ("antecedent diagnostic",                5,    20,   2,      "OUT", "R5"),
    ("salience AUC",                         0.70, 0.92, 0.6667, "OUT", "R6"),
    ("salience P@10",                        0.55, 0.85, 0.8750, "OUT", "R6"),
    ("default-view dots @ch10",              8,    20,   10,     "IN",  "R6"),
    ("default-view dots @ch20",              15,   20,   7,      "OUT", "R6"),
    ("default-view dots @ch40",              20,   None, 12,     "OUT", "R6"),
    ("INFERRED share of lines @ch10 (%)",    70,   100,  100,    "IN",  "R7"),
    ("INFERRED share of lines @ch20 (%)",    70,   100,  100,    "IN",  "R7"),
    ("rendered == payload elements",         None, None, None,   "MIS-SPECIFIED", "R7"),
    ("edge labels legible @ch40 (%)",        80,   100,  31,     "OUT", "R7"),
    ("chapters needing the low-edge note",   0,    0,    0,      "IN",  "R7"),
]


def fig_predictions_vs_measured() -> None:
    print("predictions_vs_measured")
    # Bands span wildly different units (F1 in [0,1], edge counts in the hundreds), so
    # each row is drawn on its OWN normalised axis: 0 = band low, 1 = band high. The raw
    # numbers stay on the row as text, and the CSV carries them unnormalised.
    fig, ax = plt.subplots(figsize=(11.5, 8.6))
    ys = np.arange(len(BANDS))[::-1]
    labels = []
    for y, (label, lo, hi, meas, verdict, phase) in zip(ys, BANDS, strict=True):
        labels.append(f"{phase}  ·  {label}")
        if lo is None or meas is None:
            ax.text(0.5, y, "criterion mis-specified — not evaluable",
                    ha="center", va="center", fontsize=8.5, color=MUTED, style="italic")
            continue
        span = (hi - lo) if (hi is not None and hi != lo) else 0.0
        withdrawn = verdict == "WITHDRAWN"

        if span == 0:
            ax.plot([0.5], [y], marker="|", markersize=18,
                    color=MUTED if not withdrawn else ACCENT)
        else:
            ax.plot([0, 1], [y, y], linewidth=7, solid_capstyle="butt",
                    color="#EADCCD" if not withdrawn else "#F0D3CC",
                    zorder=1)
            ax.plot([0, 0], [y - 0.28, y + 0.28], color=MUTED, linewidth=1)
            ax.plot([1, 1], [y - 0.28, y + 0.28], color=MUTED, linewidth=1)
        normalised = 0.5 if span == 0 else (meas - lo) / span
        mx = float(np.clip(normalised, -0.28, 1.28))
        inside = verdict == "IN"
        ax.plot([mx], [y], marker="o", markersize=8, zorder=3,
                color=INK if inside else ACCENT,
                markerfacecolor=INK if inside else PAPER,
                markeredgecolor=INK if inside else ACCENT, markeredgewidth=1.8)
        band_txt = f"{lo:g}" if span == 0 else f"{lo:g}–{hi:g}"
        tag = "withdrawn" if withdrawn else ("inside" if inside else "outside")
        ax.text(1.38, y, f"band {band_txt}   measured {meas:g}   [{tag}]",
                va="center", fontsize=8.2,
                color=MUTED if withdrawn else (INK if inside else ACCENT))

    ax.set_yticks(ys, labels, fontsize=8.5)
    ax.set_xticks([0, 0.5, 1], ["band low", "", "band high"], fontsize=8.5)
    ax.set_xlim(-0.35, 2.45)
    ax.set_ylim(-0.8, len(BANDS) - 0.2)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    n_in = sum(1 for b in BANDS if b[4] == "IN")
    n_out = sum(1 for b in BANDS if b[4] == "OUT")
    ax.set_title("Every pre-registered band against its measured value\n"
                 f"n = {len(BANDS) - 1} pre-registered bands "
                 f"({n_in} inside, {n_out} outside, 1 mis-specified), "
                 "plus 1 withdrawn projection", fontsize=11)
    caption(fig, f"n={len(BANDS) - 1} bands + 1 withdrawn; each row normalised to its own "
                 "band (0 = low, 1 = high); transcribed from PROJECTION_CHECK.md")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "predictions_vs_measured")

    write_csv("predictions_vs_measured",
              ["phase", "quantity", "band_low", "band_high", "measured", "verdict"],
              [[p, label, "" if lo is None else lo, "" if hi is None else hi,
                "" if meas is None else meas, verdict]
               for (label, lo, hi, meas, verdict, p) in BANDS])


# --------------------------------------------------------------------------- #
# 6. graph size
# --------------------------------------------------------------------------- #

GRAPH_CHAPTERS = (10, 20, 30, 40)
ALL_TYPES = "Character,Organization,Place,Item"


def fig_graph_size() -> None:
    print("graph_size")
    # Local imports: heavy, and needed by this figure alone.
    import os

    from fastapi.testclient import TestClient

    from storyweave.api.app import create_app
    from storyweave.config import get_settings

    def client_for(db: Path) -> TestClient:
        get_settings.cache_clear()
        os.environ["STORYWEAVE_DB_PATH"] = str(db)
        return TestClient(create_app())

    def sizes(client: TestClient, **params: str) -> dict[int, tuple[int, int]]:
        base = f"/api/v1/works/{SLUG}"
        out = {}
        for n in GRAPH_CHAPTERS:
            r = client.get(f"{base}/graph", params={"n": n, **params})
            r.raise_for_status()
            el = r.json()["elements"]
            out[n] = (len(el["nodes"]), len(el["edges"]))
        return out

    # The frozen v1 DB is read-only and the API migrates schema on open, so it is served
    # from a scratch COPY on F: — the original is never touched (CLAUDE.md frozen
    # artifacts). Same approach as tools/r8_compare.py.
    scratch = Path(tempfile.mkdtemp(dir=REPO_ROOT / ".local" / "tmp", prefix="figs_v1_"))
    try:
        v1_copy = scratch / V1_DB.name
        shutil.copy2(V1_DB, v1_copy)
        v1_copy.chmod(0o644)
        v1 = sizes(client_for(v1_copy), cast="all", types=ALL_TYPES)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    final = sizes(client_for(FINAL_DB))  # the DEFAULT view: Characters, cast 20

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0))
    for ax, idx, what in ((axes[0], 0, "dots"), (axes[1], 1, "lines")):
        xs = list(GRAPH_CHAPTERS)
        a = [v1[n][idx] for n in xs]
        b = [final[n][idx] for n in xs]
        ax.plot(xs, a, marker="o", color=ACCENT, linewidth=1.8,
                label="v1 payload (whole fenced graph)")
        ax.plot(xs, b, marker="s", color=INK, linewidth=1.8,
                label="final, default view (Characters, cast 20)")
        ax.set_yscale("symlog")
        # Headroom BEFORE the annotations, so "n=..." never lands on the frame or under
        # the legend (both happened on the first render, measured by looking at it).
        ax.set_ylim(min(b) * 0.55, max(a) * 3.2)
        for x, v in zip(xs, a, strict=True):
            ax.annotate(f"n={v}", (x, v), textcoords="offset points", xytext=(0, 10),
                        ha="center", fontsize=8.5, color=ACCENT)
        for x, v in zip(xs, b, strict=True):
            ax.annotate(f"n={v}", (x, v), textcoords="offset points", xytext=(0, 10),
                        ha="center", fontsize=8.5, color=INK)
        ax.set_xticks(xs, [f"ch{n}" for n in xs])
        ax.set_ylabel(f"{what} served")
        ax.set_title(what, fontsize=10)
        ax.legend(fontsize=8, frameon=False, loc="lower center",
                  bbox_to_anchor=(0.5, -0.30), ncol=1)
    fig.suptitle("What the client is handed, v1 versus the final default view", fontsize=12)
    fig.text(0.5, 0.925, "log scale — the v1 line runs two orders of magnitude higher",
             ha="center", fontsize=8.5, color=MUTED, style="italic")
    caption(fig, "n on every point; served through the real API (TestClient), "
                 "frozen v1 DB read from a scratch copy")
    fig.tight_layout(rect=(0, 0.10, 1, 0.91))
    save(fig, "graph_size")

    write_csv("graph_size", ["chapter", "config", "dots", "lines"],
              [[n, "v1_payload_all", v1[n][0], v1[n][1]] for n in GRAPH_CHAPTERS]
              + [[n, "final_default_view", final[n][0], final[n][1]] for n in GRAPH_CHAPTERS])


# --------------------------------------------------------------------------- #

FIGURES = {
    "entity_confusion": fig_entity_confusion,
    "relation_confusion": fig_relation_confusion,
    "recall_funnel": fig_recall_funnel,
    "phase_timeline": fig_phase_timeline,
    "predictions_vs_measured": fig_predictions_vs_measured,
    "graph_size": fig_graph_size,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", choices=sorted(FIGURES), default=[],
                    help="regenerate only these figures (repeatable)")
    args = ap.parse_args(argv)
    wanted = args.only or list(FIGURES)
    for name in wanted:
        FIGURES[name]()
    print(f"\n{len(wanted)} figure(s) + CSVs in {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
