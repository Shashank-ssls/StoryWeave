"""The ``storyweave`` CLI.

Phase 0 ships a skeleton with a ``version`` command. Pipeline commands (ingest,
extract, …) arrive in later phases and run under ``.venv-ml``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from storyweave import __version__
from storyweave.config import get_settings

app = typer.Typer(
    help="StoryWeave — a spoiler-aware knowledge engine for web novels.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the StoryWeave version."""
    typer.echo(__version__)


@app.command()
def info() -> None:
    """Show effective configuration (confirms the LLM layer is off by default)."""
    settings = get_settings()
    typer.echo(f"version:     {__version__}")
    typer.echo(f"db_path:     {settings.db_path}")
    typer.echo(f"llm_enabled: {settings.llm_enabled}")


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(help="A .txt file or a directory of .txt chapters.")],
    title: Annotated[str | None, typer.Option(help="Work title (overrides config).")] = None,
    slug: Annotated[str | None, typer.Option(help="Work slug (overrides config).")] = None,
    config: Annotated[
        Path | None, typer.Option(help="Path to a storyweave.toml (else auto-detected).")
    ] = None,
    db: Annotated[
        Path | None, typer.Option(help="SQLite path (overrides STORYWEAVE_DB_PATH).")
    ] = None,
) -> None:
    """Ingest a novel: clean, split into chapters, chunk, and store. Idempotent."""
    # Lazy imports keep ``version``/``info`` instant and dependency-light.
    from storyweave.db.repository import Repository
    from storyweave.ingest.pipeline import ingest as run_ingest
    from storyweave.ingest.work_config import find_work_config, load_work_config

    if not path.exists():
        typer.echo(f"error: source not found: {path}", err=True)
        raise typer.Exit(code=1)

    db_path = db or get_settings().db_path
    config_path = config or find_work_config(path)
    work_config = load_work_config(config_path)

    with Repository(db_path) as repo:
        repo.initialize_schema()
        report = run_ingest(path, repo, work_config, slug=slug, title=title)

    typer.echo(report.summary())
    for warning in report.warnings:
        typer.echo(f"  warning: {warning}", err=True)


@app.command()
def extract(
    slug: Annotated[str, typer.Argument(help="Work slug to extract entities for.")],
    config: Annotated[
        Path | None, typer.Option(help="storyweave.toml with extraction overrides.")
    ] = None,
    model: Annotated[str | None, typer.Option(help="GLiNER model id override.")] = None,
    threshold: Annotated[float | None, typer.Option(help="GLiNER score threshold.")] = None,
    device: Annotated[str | None, typer.Option(help="cpu or cuda.")] = None,
    db: Annotated[Path | None, typer.Option(help="SQLite path override.")] = None,
) -> None:
    """Run the GLiNER floor over an ingested work: mentions -> canonical entities.

    Requires the .venv-ml environment (GLiNER + torch). Idempotent.
    """
    from storyweave.config import get_settings
    from storyweave.db.repository import Repository
    from storyweave.ingest.work_config import load_work_config
    from storyweave.nlp.pipeline import extract_work

    settings = get_settings()
    db_path = db or settings.db_path
    work_config = load_work_config(config)
    if model is not None:
        work_config.extraction.model = model
    if threshold is not None:
        work_config.extraction.threshold = threshold
    if device is not None:
        work_config.extraction.device = device

    with Repository(db_path) as repo:
        repo.initialize_schema()
        work = repo.get_work_by_slug(slug)
        if work is None or work.id is None:
            typer.echo(f"error: no work with slug '{slug}' (ingest it first)", err=True)
            raise typer.Exit(code=1)
        report = extract_work(work.id, repo, work_config, settings)

    typer.echo(report.summary())


@app.command()
def relate(
    slug: Annotated[str, typer.Argument(help="Work slug to build Tier-1 relations for.")],
    config: Annotated[Path | None, typer.Option(help="storyweave.toml overrides.")] = None,
    db: Annotated[Path | None, typer.Option(help="SQLite path override.")] = None,
) -> None:
    """Build Tier-1 structural relationships (proximity/rule, zero LLM). Idempotent."""
    from storyweave.config import get_settings
    from storyweave.db.repository import Repository
    from storyweave.graph.builder import build_relationships
    from storyweave.ingest.work_config import load_work_config

    db_path = db or get_settings().db_path
    work_config = load_work_config(config)
    with Repository(db_path) as repo:
        repo.initialize_schema()
        work = repo.get_work_by_slug(slug)
        if work is None or work.id is None:
            typer.echo(f"error: no work with slug '{slug}'", err=True)
            raise typer.Exit(code=1)
        report = build_relationships(work.id, repo, work_config)
    typer.echo(report.summary())


@app.command()
def graph(
    slug: Annotated[str, typer.Argument(help="Work slug.")],
    chapter: Annotated[int, typer.Option("--chapter", "-n", help="Reading position N (fence).")],
    out: Annotated[Path | None, typer.Option(help="Write Cytoscape JSON here.")] = None,
    db: Annotated[Path | None, typer.Option(help="SQLite path override.")] = None,
) -> None:
    """Emit the fenced graph at chapter N as Cytoscape JSON."""
    import json

    from storyweave.config import get_settings
    from storyweave.db.repository import Repository
    from storyweave.graph.serialize import graph_json

    if chapter < 0:
        typer.echo("error: --chapter must be >= 0", err=True)
        raise typer.Exit(code=1)

    db_path = db or get_settings().db_path
    with Repository(db_path) as repo:
        repo.initialize_schema()
        work = repo.get_work_by_slug(slug)
        if work is None or work.id is None:
            typer.echo(f"error: no work with slug '{slug}'", err=True)
            raise typer.Exit(code=1)
        payload = graph_json(repo, work.id, chapter)

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if out is not None:
        out.write_text(text, encoding="utf-8")
        n_nodes = len(payload["elements"]["nodes"])
        n_edges = len(payload["elements"]["edges"])
        typer.echo(f"wrote {out} ({n_nodes} nodes, {n_edges} edges at n={chapter})")
    else:
        typer.echo(text)


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
