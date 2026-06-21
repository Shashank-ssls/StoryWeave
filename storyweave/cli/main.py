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


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
