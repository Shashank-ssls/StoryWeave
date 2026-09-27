"""Screenshot harness: capture the Stemma at a set of chapters, for one label.

DELIVERABLE 2 of the measurement harness. Playwright (sync API) against Chromium.

Two shots per chapter, at an identical viewport for every label:
    <label>_ch<NN>_full.png   the full graph, no focus
    <label>_ch<NN>_ego.png    the same graph focused on --focus (a node NAME)

Notes on how this drives the real app rather than a test double:

* The chapter bookmark MUST NOT appear in a URL (DESIGN_SPEC.md §5, enforced by
  ``router/useHashRoute.ts``). It lives in ``localStorage`` under
  ``storyweave:bookmark:<slug>`` (``codex/chapter/bookmarkStore.ts``), so the bookmark is
  seeded with an init script that runs before any app code.
* Settling is detected from the rendered canvas itself, never a fixed sleep: the Cytoscape
  container is screenshotted repeatedly and the layout counts as settled once two polls
  500 ms apart are byte-identical. ``cytoscape-cola`` fires ``layoutstop`` twice per burst
  for small graphs (see ``StemmaCanvas.tsx``), so pixel stability is the more trustworthy
  signal here.
* Focusing DIMS context nodes, it does not drop them (``StemmaCanvas.tsx``), so the live
  node/edge counts are the same in both shots and both can be cross-checked against
  DELIVERABLE 1. Fit differs by design: no focus fits everything, a focus fits the focus
  set -- identical behaviour for every label, since every label runs this same build.

Usage:
    python tools/capture.py --url http://127.0.0.1:8000 --label rendered_view \
        --slug the-ninth-house --focus "Sunny" --chapters 10,20,30,40 --out evidence/shots/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import Page, ViewportSize, sync_playwright  # noqa: E402

VIEWPORT: ViewportSize = {"width": 1600, "height": 900}
DEVICE_SCALE_FACTOR = 2

#: Poll interval for the settle check, in ms (the task's 500ms stability window).
SETTLE_POLL_MS = 500
#: Give up on settling after this long.
SETTLE_TIMEOUT_MS = 90_000

#: Any of these visible at capture time means the page is not in a good state.
FAILURE_SELECTORS = (
    '[data-testid="loading-dots"]',
    '[data-testid^="state-"]',
    '[data-testid$="-error"]',
    '[data-testid$="-loading"]',
)

# Reads the live Cytoscape instance off its container. Cytoscape registers itself on the
# container element as `_cyreg`, so this is pure read-only introspection -- no app change,
# no test hook added to the frontend.
COUNTS_JS = """() => {
  const el = document.querySelector('[data-testid="stemma-cy"]');
  if (!el) return { error: 'no stemma-cy container' };
  const reg = el._cyreg;
  if (!reg || !reg.cy) return { error: 'cytoscape not registered on container' };
  const cy = reg.cy;
  return {
    nodes: cy.nodes().length,
    edges: cy.edges().length,
    zoom: cy.zoom(),
  };
}"""


@dataclass
class Shot:
    """One captured image plus the live counts observed when it was taken."""

    label: str
    slug: str
    chapter: int
    view: str  # "full" | "ego"
    path: str
    dom_nodes: int
    dom_edges: int
    zoom: float
    focus_name: str | None
    focus_id: str | None
    cast: str


# --- helpers ------------------------------------------------------------------ #


def fetch_graph(base_url: str, slug: str, chapter: int) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/v1/works/{slug}/graph?n={chapter}"
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - local dev server
        if resp.status != 200:
            raise RuntimeError(f"GET {url} -> HTTP {resp.status}")
        return cast("dict[str, Any]", json.load(resp))


def resolve_focus_id(base_url: str, slug: str, chapter: int, name: str) -> str:
    """The node id whose label is `name` in the fenced payload at `chapter`."""
    payload = fetch_graph(base_url, slug, chapter)
    wanted = name.strip().casefold()
    for node in payload["elements"]["nodes"]:
        if str(node["data"]["label"]).strip().casefold() == wanted:
            return str(node["data"]["id"])
    raise RuntimeError(
        f"--focus {name!r} is not in the fenced payload at chapter {chapter} for {slug!r}. "
        "Pick a node revealed by the earliest captured chapter, so the same node can be "
        "focused at every chapter."
    )


def assert_healthy(page: Page, context: str) -> None:
    """Fail loudly if the page is showing a loading or error state."""
    for selector in FAILURE_SELECTORS:
        for handle in page.query_selector_all(selector):
            if handle.is_visible():
                testid = handle.get_attribute("data-testid")
                text = (handle.inner_text() or "").strip().replace("\n", " ")[:160]
                raise RuntimeError(
                    f"{context}: page is in a bad state -- visible "
                    f'[data-testid="{testid}"] ({text!r})'
                )


def live_counts(page: Page, context: str) -> dict[str, Any]:
    result = page.evaluate(COUNTS_JS)
    if "error" in result:
        raise RuntimeError(f"{context}: cannot read Cytoscape counts -- {result['error']}")
    if result["nodes"] == 0:
        raise RuntimeError(f"{context}: the rendered graph is EMPTY (0 nodes)")
    return cast("dict[str, Any]", result)


def wait_for_settle(page: Page, context: str) -> None:
    """Block until the canvas stops changing, or raise.

    Compares byte-identical screenshots of the Cytoscape container taken
    ``SETTLE_POLL_MS`` apart. No fixed sleep is used as the capture gate.
    """
    canvas = page.wait_for_selector('[data-testid="stemma-cy"]', state="visible", timeout=30_000)
    if canvas is None:
        raise RuntimeError(f"{context}: stemma canvas never became visible")

    previous: str | None = None
    waited = 0
    while waited < SETTLE_TIMEOUT_MS:
        digest = hashlib.sha256(canvas.screenshot()).hexdigest()
        if previous is not None and digest == previous:
            return
        previous = digest
        page.wait_for_timeout(SETTLE_POLL_MS)
        waited += SETTLE_POLL_MS
    raise RuntimeError(
        f"{context}: canvas never settled -- still changing after "
        f"{SETTLE_TIMEOUT_MS / 1000:.0f}s of {SETTLE_POLL_MS}ms polls"
    )


def set_cast(page: Page, cast: str, context: str) -> None:
    """Put the Stemma's cast toggle into `cast`, opening the rail first if it is closed.

    The toggle is `[data-testid="cast-principal"|"cast-everyone"]` in the left rail
    (Stemma.tsx). "principal" is the app's default, so selecting it is a no-op assertion
    rather than a click; "everyone" is clicked.
    """
    button = page.query_selector(f'[data-testid="cast-{cast}"]')
    if button is None:
        raise RuntimeError(f"{context}: no cast toggle [data-testid=\"cast-{cast}\"] on the page")
    if not button.is_visible():
        toggle = page.query_selector('[data-testid="rail-toggle"]')
        if toggle is not None and toggle.is_visible():
            toggle.click()
            page.wait_for_timeout(SETTLE_POLL_MS)
    if button.get_attribute("aria-checked") == "true":
        return  # already in this state
    button.click()


def capture_one(
    page: Page,
    base_url: str,
    slug: str,
    chapter: int,
    view: str,
    focus_id: str | None,
    focus_name: str | None,
    label: str,
    cast: str,
    out_dir: Path,
) -> Shot:
    suffix = f"?focus={focus_id}" if focus_id else ""
    url = f"{base_url.rstrip('/')}/#/work/{slug}/web{suffix}"
    context = f"{label} ch{chapter:02d} {view}"

    # Seed the bookmark before any app code runs (never in the URL, per DESIGN_SPEC §5).
    page.add_init_script(
        f"try {{ window.localStorage.setItem('storyweave:bookmark:{slug}', '{chapter}'); }} catch (e) {{}}"
    )
    page.goto(url, wait_until="load")
    page.wait_for_selector('[data-testid="stemma-root"]', state="visible", timeout=30_000)
    wait_for_settle(page, context)
    # Set the cast AFTER the first settle: changing it re-runs the layout, so the canvas has
    # to settle again before anything is captured.
    set_cast(page, cast, context)
    wait_for_settle(page, context)

    if focus_id is None:
        # `#/work/:slug/web` with no ?focus does NOT land unfocused: the app redirects to
        # the highest-degree person (the R4 redirect noted in router/useHashRoute.ts), so a
        # naive "full" shot comes out focused and fitted to the focus set. Clearing focus
        # through the app's own control runs focusOn(null) + fitAll(), which is the
        # identical fit path for every label.
        clear = page.query_selector('[data-testid="clear-focus"]')
        if clear is not None and clear.is_visible():
            clear.click()
            wait_for_settle(page, context)
        if page.query_selector('[data-testid="clear-focus"]') is not None:
            raise RuntimeError(
                f"{context}: focus is still set after clicking clear-focus -- "
                "the full shot would not be the full graph"
            )
    assert_healthy(page, context)
    counts = live_counts(page, context)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{label}_ch{chapter:02d}_{view}.png"
    page.screenshot(path=str(path))
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{context}: screenshot was not written to {path}")

    print(
        f"  {context}: nodes={counts['nodes']} edges={counts['edges']} "
        f"zoom={counts['zoom']:.4f} -> {path.name}"
    )
    return Shot(
        label=label,
        slug=slug,
        chapter=chapter,
        view=view,
        path=str(path),
        dom_nodes=int(counts["nodes"]),
        dom_edges=int(counts["edges"]),
        zoom=float(counts["zoom"]),
        focus_name=focus_name,
        focus_id=focus_id,
        cast=cast,
    )


def capture(
    base_url: str,
    label: str,
    slug: str,
    focus: str,
    chapters: list[int],
    out_dir: Path,
    cast: str = "principal",
) -> list[Shot]:
    # Resolve the focus node once, at the EARLIEST chapter, so every chapter focuses the
    # same node (a node revealed later would not exist at the earlier chapters).
    focus_id = resolve_focus_id(base_url, slug, min(chapters), focus)
    print(f"focus {focus!r} -> node id {focus_id} (resolved at chapter {min(chapters)})")

    shots: list[Shot] = []
    with sync_playwright() as pw:
        # channel="chrome": use the installed system Chrome, so no browser is downloaded
        # into the repo (matches the project's existing screenshot-gate workflow).
        browser = pw.chromium.launch(channel="chrome", headless=True)
        try:
            context = browser.new_context(
                viewport=VIEWPORT, device_scale_factor=DEVICE_SCALE_FACTOR
            )
            try:
                for chapter in chapters:
                    for view, fid in (("full", None), ("ego", focus_id)):
                        page = context.new_page()
                        try:
                            shots.append(
                                capture_one(
                                    page, base_url, slug, chapter, view, fid,
                                    focus if fid else None, label, cast, out_dir,
                                )
                            )
                        finally:
                            page.close()
            finally:
                context.close()
        finally:
            browser.close()
    return shots


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="base URL of the running app")
    ap.add_argument("--label", required=True, help="label used in output filenames")
    ap.add_argument("--slug", default="the-ninth-house")
    ap.add_argument("--focus", required=True, help="node NAME to focus for the ego shots")
    ap.add_argument("--chapters", default="10,20,30,40")
    ap.add_argument(
        "--cast",
        default="principal",
        choices=("principal", "everyone"),
        help="the Stemma cast toggle state to capture in",
    )
    ap.add_argument("--out", required=True, type=Path, help="output directory for the PNGs")
    args = ap.parse_args(argv)

    chapters = [int(p) for p in args.chapters.split(",") if p.strip()]
    shots = capture(
        args.url, args.label, args.slug, args.focus, chapters, args.out, args.cast
    )

    manifest = args.out / f"{args.label}_shots.json"
    manifest.write_text(json.dumps([asdict(s) for s in shots], indent=2), encoding="utf-8")
    print(f"\ncaptured {len(shots)} shots; wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
