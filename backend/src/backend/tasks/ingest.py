from __future__ import annotations

import typer

from backend.db.session import create_db_and_tables
from backend.services.indexer import run_ingestion


app = typer.Typer(help="DVCon archive ingestion utilities.")


@app.command()
def run(
    limit: int | None = typer.Option(default=None, help="Maximum number of papers to ingest."),
    force: bool = typer.Option(default=False, help="Re-download and re-index existing papers."),
) -> None:
    create_db_and_tables()
    papers = run_ingestion(limit=limit, force=force)
    typer.echo(f"Indexed {len(papers)} paper(s).")
