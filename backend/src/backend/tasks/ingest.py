from __future__ import annotations

import typer

from backend.db.session import create_db_and_tables
from backend.services.indexer import run_ingestion


app = typer.Typer(help="DVCon archive ingestion utilities.")


@app.command()
def run(
    limit: int | None = typer.Option(default=None, help="Maximum number of papers to ingest."),
    force: bool = typer.Option(default=False, help="Re-download and re-index existing papers."),
    years: str = typer.Option(
        default=None,
        help=(
            "Comma-separated 4-digit years to crawl (e.g. '2025,2026'). "
            "When unset, crawls every year filter exposed on the homepage. "
            "Scoping to recent years skips a pointless re-walk of years you "
            "already have, which is the slow part of an unbounded crawl."
        ),
    ),
) -> None:
    year_filter: list[int] | None = None
    if years:
        year_filter = []
        for token in years.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                year_filter.append(int(token))
            except ValueError as error:
                raise typer.BadParameter(f"Invalid year {token!r}; use 4-digit years like '2025,2026'.") from error
        if not year_filter:
            raise typer.BadParameter("--years was empty after parsing.")

    create_db_and_tables()
    papers = run_ingestion(limit=limit, force=force, years=year_filter)
    typer.echo(f"Indexed {len(papers)} paper(s).")
