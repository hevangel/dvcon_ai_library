from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Conference(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    location: str = Field(index=True)
    year: int = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    papers: List["Paper"] = Relationship(back_populates="conference")


class PaperAuthor(SQLModel, table=True):
    paper_id: int | None = Field(default=None, foreign_key="paper.id", primary_key=True)
    author_id: int | None = Field(default=None, foreign_key="author.id", primary_key=True)
    author_order: int = Field(default=0, nullable=False)
    company_name: str | None = None


class AuthorAffiliation(SQLModel, table=True):
    paper_id: int | None = Field(default=None, foreign_key="paper.id", primary_key=True)
    author_id: int | None = Field(default=None, foreign_key="author.id", primary_key=True)
    affiliation_id: int | None = Field(default=None, foreign_key="affiliation.id", primary_key=True)
    author_order: int = Field(default=0, nullable=False)


class Paper(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_url: str = Field(unique=True, index=True)
    pdf_url: str
    slug: str = Field(index=True)
    title: str = Field(index=True)
    abstract: str | None = None
    year: int = Field(index=True)
    location: str = Field(index=True)
    document_type: str = Field(default="Paper", index=True)
    authors_text: str = ""
    affiliations_text: str = ""
    references_text: str = ""
    searchable_text: str = ""
    pdf_path: str
    markdown_path: str | None = None
    tei_path: str | None = None
    metadata_json: str | None = None
    last_ingested_at: datetime | None = None
    conference_id: int | None = Field(default=None, foreign_key="conference.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    conference: Optional[Conference] = Relationship(back_populates="papers")
    authors: List["Author"] = Relationship(back_populates="papers", link_model=PaperAuthor)
    chunks: List["Chunk"] = Relationship(back_populates="paper")
    references: List["ReferenceEntry"] = Relationship(back_populates="paper")


class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    papers: List[Paper] = Relationship(back_populates="authors", link_model=PaperAuthor)


class Affiliation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)


class Chunk(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(foreign_key="paper.id", index=True)
    chunk_index: int = Field(index=True)
    heading: str | None = None
    text: str
    chroma_id: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    paper: Paper = Relationship(back_populates="chunks")


class ReferenceEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(foreign_key="paper.id", index=True)
    citation_text: str
    normalized_title: str | None = None
    authors_text: str | None = None
    journal_or_book: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    raw_tei_json: str | None = None

    paper: Paper = Relationship(back_populates="references")
