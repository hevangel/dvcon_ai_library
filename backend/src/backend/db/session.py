from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from backend.core.config import get_settings


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


def _existing_columns(session: Session, table_name: str) -> set[str]:
    rows = session.exec(text(f"PRAGMA table_info({table_name})")).all()
    return {row[1] for row in rows}


def _ensure_column(session: Session, table_name: str, column_name: str, definition: str) -> None:
    if column_name in _existing_columns(session, table_name):
        return
    session.exec(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        _ensure_column(session, "paper", "tei_path", "TEXT")
        _ensure_column(session, "referenceentry", "authors_text", "TEXT")
        _ensure_column(session, "referenceentry", "journal_or_book", "TEXT")
        _ensure_column(session, "referenceentry", "publication_year", "INTEGER")
        _ensure_column(session, "referenceentry", "doi", "TEXT")
        _ensure_column(session, "referenceentry", "raw_tei_json", "TEXT")
        session.exec(
            text(
                """
            CREATE VIRTUAL TABLE IF NOT EXISTS paper_fts USING fts5(
                paper_id UNINDEXED,
                title,
                abstract,
                authors,
                affiliations,
                reference_list,
                content
            )
            """
            )
        )
        session.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
