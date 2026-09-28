"""Verify captured screenshots and build side-by-side comparison plates.

DELIVERABLE 3 of the measurement harness.

Per image it checks and reports:
  * dimensions match the capture viewport x deviceScaleFactor
  * not blank: the greyscale standard deviation is above a floor
  * ink ratio: the fraction of pixels that differ from the page background, a crude but
    real proxy for visual density
  * obvious-failure detection: a uniform image, or ink confined to a small box (the shape
    an error card or a lone text block makes)

Then it composes ``evidence/plates/compare_ch<NN>.png`` -- one label on the left, one on
the right at the same scale, under a caption bar naming the label and the chapter.

On the OpenCV question the task raises: PIL (for IO and composition) plus numpy (for the
stdev, the background-distance mask and the ink bounding box) covers every check here.
Nothing in this file would be shorter or more accurate in OpenCV, so OpenCV is NOT a
dependency of this harness.

Usage:
    python tools/verify_shots.py --shots evidence/shots --out evidence/plates \
        --left rendered_view --right rendered_everyone --chapters 10,20,30,40
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from PIL.ImageFont import ImageFont as BitmapFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: What capture.py produces: 1600x900 at deviceScaleFactor 2.
EXPECTED_SIZE = (3200, 1800)

#: A greyscale stdev below this means the image carries essentially no variation.
BLANK_STDEV_FLOOR = 2.0
#: A pixel this far (0-255, per-channel max) from the modal background colour is "ink".
INK_DISTANCE = 24
#: Ink covering less than this fraction of the frame is suspiciously empty.
MIN_INK_RATIO = 0.005
#: Ink whose bounding box covers less than this fraction of the frame looks like a lone
#: card / text block rather than a rendered graph.
MIN_INK_BBOX_FRACTION = 0.05


@dataclass
class Check:
    """The verification result for one image."""

    path: str
    width: int
    height: int
    size_ok: bool
    stdev: float
    blank: bool
    ink_ratio: float
    ink_bbox_fraction: float
    uniform: bool
    single_block: bool
    ok: bool
    problems: str


def background_colour(arr: np.ndarray) -> np.ndarray:
    """The modal RGB colour, taken as the page background.

    Colours are quantised into 8-level buckets per channel before the mode is taken, so
    the background's anti-aliasing noise does not split the peak.
    """
    quantised = (arr // 32).reshape(-1, 3)
    packed = quantised[:, 0] * 64 + quantised[:, 1] * 8 + quantised[:, 2]
    winner = np.bincount(packed).argmax()
    mask = packed == winner
    return np.asarray(arr.reshape(-1, 3)[mask].mean(axis=0))


def verify_image(path: Path) -> Check:
    with Image.open(path) as handle:
        image = handle.convert("RGB")
        width, height = image.size
        arr = np.asarray(image, dtype=np.int16)

    grey = arr.mean(axis=2)
    stdev = float(grey.std())

    bg = background_colour(arr.astype(np.uint8))
    # "ink" = any pixel whose largest per-channel deviation from the background exceeds
    # INK_DISTANCE. Cheap, and it does not assume the background is black.
    ink_mask = np.abs(arr - bg).max(axis=2) > INK_DISTANCE
    ink_ratio = float(ink_mask.mean())

    rows = np.flatnonzero(ink_mask.any(axis=1))
    cols = np.flatnonzero(ink_mask.any(axis=0))
    if rows.size and cols.size:
        box_h = int(rows[-1] - rows[0] + 1)
        box_w = int(cols[-1] - cols[0] + 1)
        ink_bbox_fraction = (box_h * box_w) / (height * width)
    else:
        ink_bbox_fraction = 0.0

    size_ok = (width, height) == EXPECTED_SIZE
    blank = stdev < BLANK_STDEV_FLOOR
    uniform = len(np.unique(arr.reshape(-1, 3), axis=0)) <= 2
    single_block = ink_ratio < MIN_INK_RATIO or ink_bbox_fraction < MIN_INK_BBOX_FRACTION

    problems: list[str] = []
    if not size_ok:
        problems.append(f"dimensions {width}x{height} != {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}")
    if blank:
        problems.append(f"blank (stdev {stdev:.3f} < {BLANK_STDEV_FLOOR})")
    if uniform:
        problems.append("uniform colour")
    if single_block:
        problems.append(
            f"ink too sparse/confined (ratio {ink_ratio:.5f}, bbox {ink_bbox_fraction:.4f})"
        )

    return Check(
        path=str(path),
        width=width,
        height=height,
        size_ok=size_ok,
        stdev=round(stdev, 4),
        blank=blank,
        ink_ratio=round(ink_ratio, 6),
        ink_bbox_fraction=round(ink_bbox_fraction, 6),
        uniform=uniform,
        single_block=single_block,
        ok=not problems,
        problems="; ".join(problems),
    )


# --- plates -------------------------------------------------------------------- #

CAPTION_H = 96
PLATE_BG = (12, 6, 5)  # tokens.css --deep
PLATE_INK = (232, 216, 194)  # tokens.css --ink
PLATE_LINE = (58, 36, 32)  # tokens.css --line
PLATE_SCALE = 0.5  # half-size panels keep the plate a sane file size


def _font(size: int) -> FreeTypeFont | BitmapFont:
    for name in ("georgia.ttf", "seguisb.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_plate(
    left: Path, right: Path, left_label: str, right_label: str, chapter: int, out: Path
) -> Path:
    """Compose a captioned side-by-side plate. Both panels are scaled identically."""
    with Image.open(left) as lh, Image.open(right) as rh:
        limg = lh.convert("RGB")
        rimg = rh.convert("RGB")
        if limg.size != rimg.size:
            raise ValueError(
                f"cannot plate images of different sizes: {left} {limg.size} vs {right} {rimg.size}"
            )
        panel = (int(limg.width * PLATE_SCALE), int(limg.height * PLATE_SCALE))
        limg = limg.resize(panel, Image.Resampling.LANCZOS)
        rimg = rimg.resize(panel, Image.Resampling.LANCZOS)

    gap = 8
    plate = Image.new("RGB", (panel[0] * 2 + gap, panel[1] + CAPTION_H), PLATE_BG)
    plate.paste(limg, (0, CAPTION_H))
    plate.paste(rimg, (panel[0] + gap, CAPTION_H))

    draw = ImageDraw.Draw(plate)
    title = _font(34)
    small = _font(24)
    draw.text((16, 14), f"The Ninth House — chapter {chapter}", font=title, fill=PLATE_INK)
    draw.text((16, 58), left_label, font=small, fill=PLATE_INK)
    draw.text((panel[0] + gap + 16, 58), right_label, font=small, fill=PLATE_INK)
    draw.line([(0, CAPTION_H - 1), (plate.width, CAPTION_H - 1)], fill=PLATE_LINE, width=2)
    mid = panel[0] + gap // 2
    draw.line([(mid, CAPTION_H), (mid, plate.height)], fill=PLATE_LINE, width=2)

    out.parent.mkdir(parents=True, exist_ok=True)
    plate.save(out)
    return out


# --- CLI ----------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--shots", required=True, type=Path, help="directory of captured PNGs")
    ap.add_argument("--out", required=True, type=Path, help="directory for the plates")
    ap.add_argument("--left", required=True, help="label shown on the left of each plate")
    ap.add_argument("--right", required=True, help="label shown on the right of each plate")
    ap.add_argument("--chapters", default="10,20,30,40")
    ap.add_argument("--report", type=Path, default=None, help="where to write the checks CSV")
    args = ap.parse_args(argv)

    chapters = [int(p) for p in args.chapters.split(",") if p.strip()]
    images = sorted(args.shots.glob("*.png"))
    if not images:
        raise SystemExit(f"no PNGs found in {args.shots}")

    checks = [verify_image(p) for p in images]
    print(f"{'image':<44} {'size':>11} {'stdev':>8} {'ink':>9} {'bbox':>8}  status")
    for check in checks:
        status = "OK" if check.ok else f"FAIL: {check.problems}"
        print(
            f"{Path(check.path).name:<44} {check.width}x{check.height:<5} "
            f"{check.stdev:>8.3f} {check.ink_ratio:>9.5f} {check.ink_bbox_fraction:>8.4f}  {status}"
        )

    report = args.report or (args.out.parent / "shot_checks.csv")
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(checks[0])))
        writer.writeheader()
        for check in checks:
            writer.writerow(asdict(check))
    print(f"\nwrote {report}")

    failed = [c for c in checks if not c.ok]
    if failed:
        print(f"\n{len(failed)} image(s) FAILED verification:")
        for check in failed:
            print(f"  {Path(check.path).name}: {check.problems}")
        return 1

    plates: list[str] = []
    for chapter in chapters:
        left = args.shots / f"{args.left}_ch{chapter:02d}_full.png"
        right = args.shots / f"{args.right}_ch{chapter:02d}_full.png"
        for path in (left, right):
            if not path.is_file():
                raise SystemExit(f"missing shot for the plate: {path}")
        out = args.out / f"compare_ch{chapter:02d}.png"
        build_plate(left, right, args.left, args.right, chapter, out)
        plates.append(str(out))
        print(f"plate -> {out}")

    manifest = args.out / "plates.json"
    manifest.write_text(json.dumps(plates, indent=2), encoding="utf-8")
    print(f"\nall {len(checks)} images verified OK; {len(plates)} plates written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
