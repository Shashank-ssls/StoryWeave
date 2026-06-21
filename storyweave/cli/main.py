"""The ``storyweave`` CLI.

Phase 0 ships a skeleton with a ``version`` command. Pipeline commands (ingest,
extract, …) arrive in later phases and run under ``.venv-ml``.
"""

from __future__ import annotations

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


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
