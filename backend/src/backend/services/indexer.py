from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import chromadb
from sqlalchemy import delete, text
from sqlmodel import Session, select

from backend.core.config import get_settings
from backend.db.models import (
    Affiliation,
    Author,
    AuthorAffiliation,
    Chunk,
    Conference,
    Paper,
    PaperAuthor,
    ReferenceEntry,
)
from backend.db.session import engine
from backend.services.embeddings import embed_texts
from backend.services.extractor import extract_pdf
from backend.services.scraper import PaperSeed, crawl_archive
from backend.services.tei_parser import ParsedAuthor, ParsedReference


@dataclass(slots=True)
class SearchHit:
    paper: Paper
    score: float
    snippet: str


def _get_chroma_collection():
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_dir.as_posix())
    desired_metadata = {
        "embedding_backend": "sentence_transformers",
        "embedding_model": settings.local_embedding_model,
    }
    collection = client.get_or_create_collection(name="paper_chunks", metadata=desired_metadata)
    existing_metadata = collection.metadata or {}

    if existing_metadata.get("embedding_model") != settings.local_embedding_model:
        client.delete_collection(name="paper_chunks")
        collection = client.get_or_create_collection(name="paper_chunks", metadata=desired_metadata)

    return collection


def _chunk_markdown(markdown_text: str) -> list[dict[str, str]]:
    settings = get_settings()
    sections: list[tuple[str, str]] = []
    current_heading = "Overview"
    buffer: list[str] = []
    seen_heading = False

    for line in markdown_text.splitlines():
        if not line.strip() and not buffer and not seen_heading:
            continue

        stripped_line = line.lstrip()
        if stripped_line.startswith("#"):
            if buffer:
                sections.append((current_heading, "\n".join(buffer).strip()))
                buffer = []
            current_heading = stripped_line.lstrip("#").strip() or "Overview"
            seen_heading = True
            continue

        buffer.append(line)

    if buffer:
        sections.append((current_heading, "\n".join(buffer).strip()))

    chunks: list[dict[str, str]] = []
    for heading, section_text in sections:
        clean_text = " ".join(section_text.split())
        if not clean_text:
            continue

        start = 0
        while start < len(clean_text):
            end = min(len(clean_text), start + settings.chunk_size)
            chunk_text = clean_text[start:end].strip()
            if chunk_text:
                chunks.append({"heading": heading, "text": chunk_text})
            if end >= len(clean_text):
                break
            start = max(start + settings.chunk_size - settings.chunk_overlap, end)

    return chunks


def _conference_for_seed(session: Session, seed: PaperSeed) -> Conference:
    conference = session.exec(
        select(Conference).where(Conference.slug == seed.conference_slug)
    ).first()
    if conference is not None:
        return conference

    conference = Conference(
        slug=seed.conference_slug,
        name=seed.conference_name,
        year=seed.year,
        location=seed.location,
    )
    session.add(conference)
    session.flush()
    return conference


def _paper_for_seed(session: Session, seed: PaperSeed, searchable_text: str) -> Paper:
    paper = session.exec(select(Paper).where(Paper.source_url == seed.source_url)).first()
    if paper is None:
        paper = Paper(
            source_url=seed.source_url,
            pdf_url=seed.pdf_url,
            slug=seed.slug,
            title=seed.title,
            year=seed.year,
            location=seed.location,
            document_type=seed.document_type,
            authors_text=seed.authors_text,
            pdf_path=seed.pdf_path,
            searchable_text=searchable_text,
        )
        session.add(paper)
        session.flush()
        return paper

    paper.pdf_url = seed.pdf_url
    paper.slug = seed.slug
    paper.title = seed.title
    paper.year = seed.year
    paper.location = seed.location
    paper.document_type = seed.document_type
    paper.authors_text = seed.authors_text
    paper.pdf_path = seed.pdf_path
    paper.searchable_text = searchable_text
    paper.updated_at = datetime.utcnow()
    session.add(paper)
    session.flush()
    return paper


def _get_or_create_affiliation(session: Session, affiliation_name: str) -> Affiliation:
    affiliation = session.exec(select(Affiliation).where(Affiliation.name == affiliation_name)).first()
    if affiliation is not None:
        return affiliation

    affiliation = Affiliation(name=affiliation_name)
    session.add(affiliation)
    session.flush()
    return affiliation


def _dedupe_authors(authors: list[ParsedAuthor]) -> list[ParsedAuthor]:
    deduped: list[ParsedAuthor] = []
    index_by_name: dict[str, int] = {}

    for author in authors:
        author_name = author.full_name.strip()
        if not author_name:
            continue

        key = author_name.casefold()
        existing_index = index_by_name.get(key)
        if existing_index is None:
            deduped.append(
                ParsedAuthor(
                    full_name=author_name,
                    given_name=author.given_name,
                    surname=author.surname,
                    affiliations=list(dict.fromkeys(affiliation for affiliation in author.affiliations if affiliation)),
                    email=author.email,
                )
            )
            index_by_name[key] = len(deduped) - 1
            continue

        existing_author = deduped[existing_index]
        merged_affiliations = list(
            dict.fromkeys(
                [
                    *existing_author.affiliations,
                    *(affiliation for affiliation in author.affiliations if affiliation),
                ]
            )
        )
        existing_author.affiliations = merged_affiliations
        if not existing_author.email and author.email:
            existing_author.email = author.email

    return deduped


def _sync_authors(session: Session, paper: Paper, authors: list[ParsedAuthor], affiliations: list[str]) -> None:
    session.exec(delete(PaperAuthor).where(PaperAuthor.paper_id == paper.id))
    session.exec(delete(AuthorAffiliation).where(AuthorAffiliation.paper_id == paper.id))
    session.flush()

    default_company = affiliations[0] if affiliations else None
    for index, parsed_author in enumerate(_dedupe_authors(authors)):
        author_name = parsed_author.full_name.strip()
        if not author_name:
            continue

        author = session.exec(select(Author).where(Author.name == author_name)).first()
        if author is None:
            author = Author(name=author_name)
            session.add(author)
            session.flush()

        session.add(
            PaperAuthor(
                paper_id=paper.id,
                author_id=author.id,
                author_order=index,
                company_name=(parsed_author.affiliations[0] if parsed_author.affiliations else default_company),
            )
        )

        author_affiliations = parsed_author.affiliations or ([default_company] if default_company else [])
        for affiliation_name in author_affiliations:
            if not affiliation_name:
                continue
            affiliation = _get_or_create_affiliation(session, affiliation_name)
            session.add(
                AuthorAffiliation(
                    paper_id=paper.id,
                    author_id=author.id,
                    affiliation_id=affiliation.id,
                    author_order=index,
                )
            )


def _sync_references(session: Session, paper: Paper, references: list[ParsedReference]) -> None:
    session.exec(delete(ReferenceEntry).where(ReferenceEntry.paper_id == paper.id))
    for reference in references:
        session.add(
            ReferenceEntry(
                paper_id=paper.id,
                citation_text=reference.citation_text,
                normalized_title=reference.normalized_title,
                authors_text=reference.authors_text,
                journal_or_book=reference.journal_or_book,
                publication_year=reference.publication_year,
                doi=reference.doi,
                raw_tei_json=reference.raw_tei_json,
            )
        )


def _sync_chunks(session: Session, paper: Paper, chunks: list[dict[str, str]]) -> None:
    collection = _get_chroma_collection()
    existing_chunks = session.exec(select(Chunk).where(Chunk.paper_id == paper.id)).all()
    if existing_chunks:
        collection.delete(ids=[chunk.chroma_id for chunk in existing_chunks])
        session.exec(delete(Chunk).where(Chunk.paper_id == paper.id))

    if not chunks:
        return

    ids = [f"paper-{paper.id}-chunk-{index}" for index in range(len(chunks))]
    embeddings = embed_texts([chunk["text"] for chunk in chunks])
    collection.add(
        ids=ids,
        documents=[chunk["text"] for chunk in chunks],
        embeddings=embeddings,
        metadatas=[
            {
                "paper_id": str(paper.id),
                "heading": chunk["heading"],
                "title": paper.title,
                "year": paper.year,
                "location": paper.location,
            }
            for chunk in chunks
        ],
    )

    for index, chunk in enumerate(chunks):
        session.add(
            Chunk(
                paper_id=paper.id,
                chunk_index=index,
                heading=chunk["heading"],
                text=chunk["text"],
                chroma_id=ids[index],
            )
        )


def _sync_fts(session: Session, paper: Paper) -> None:
    session.exec(
        text("DELETE FROM paper_fts WHERE paper_id = :paper_id"),
        params={"paper_id": paper.id},
    )
    session.exec(
        text(
            """
            INSERT INTO paper_fts (
                paper_id,
                title,
                abstract,
                authors,
                affiliations,
                reference_list,
                content
            ) VALUES (
                :paper_id,
                :title,
                :abstract,
                :authors,
                :affiliations,
                :reference_list,
                :content
            )
            """
        ),
        params={
            "paper_id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract or "",
            "authors": paper.authors_text,
            "affiliations": paper.affiliations_text,
            "reference_list": paper.references_text,
            "content": paper.searchable_text,
        },
    )


def index_seed(seed: PaperSeed) -> Paper:
    extracted = extract_pdf(seed)
    markdown_text = (get_settings().repo_root / extracted.markdown_path).read_text(encoding="utf-8")
    chunks = _chunk_markdown(markdown_text)
    searchable_text = "\n\n".join(
        [
            extracted.title,
            extracted.abstract,
            extracted.authors_text,
            "\n".join(extracted.affiliations),
            "\n".join(reference.citation_text for reference in extracted.references),
            markdown_text,
        ]
    ).strip()

    with Session(engine) as session:
        conference = _conference_for_seed(session, seed)
        paper = _paper_for_seed(session, seed, searchable_text)
        paper.conference_id = conference.id
        paper.title = extracted.title
        paper.authors_text = extracted.authors_text
        paper.abstract = extracted.abstract
        paper.markdown_path = extracted.markdown_path
        paper.tei_path = extracted.tei_path
        paper.affiliations_text = "\n".join(extracted.affiliations)
        paper.references_text = "\n".join(reference.citation_text for reference in extracted.references)
        paper.metadata_json = extracted.metadata_json
        paper.searchable_text = searchable_text
        paper.last_ingested_at = datetime.utcnow()
        paper.updated_at = datetime.utcnow()

        _sync_authors(session, paper, extracted.authors, extracted.affiliations)
        _sync_references(session, paper, extracted.references)
        _sync_chunks(session, paper, chunks)
        _sync_fts(session, paper)

        session.add(paper)
        session.commit()
        session.refresh(paper)
        return paper


def run_ingestion(*, limit: int | None = None, force: bool = False) -> list[Paper]:
    seeds = crawl_archive(limit=limit, force=force)
    papers: list[Paper] = []
    for seed in seeds:
        papers.append(index_seed(seed))
    return papers


def list_papers(
    *,
    limit: int = 25,
    year: int | None = None,
    location: str | None = None,
    conference_id: int | None = None,
) -> list[Paper]:
    with Session(engine) as session:
        query = select(Paper).order_by(Paper.year.desc(), Paper.title)
        if year is not None:
            query = query.where(Paper.year == year)
        if location:
            query = query.where(Paper.location == location.lower())
        if conference_id is not None:
            query = query.where(Paper.conference_id == conference_id)
        return session.exec(query.limit(limit)).all()


def keyword_search(
    query_text: str,
    *,
    limit: int = 25,
    year: int | None = None,
    location: str | None = None,
) -> list[SearchHit]:
    with Session(engine) as session:
        if not query_text.strip():
            return [
                SearchHit(paper=paper, score=1.0, snippet=paper.abstract or paper.title)
                for paper in list_papers(limit=limit, year=year, location=location)
            ]

        statement = text(
            """
            SELECT paper_id, bm25(paper_fts) AS rank
            FROM paper_fts
            WHERE paper_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
            """
        )
        rows = session.exec(statement, params={"query": query_text, "limit": limit * 3}).all()
        paper_ids = [row[0] for row in rows]
        if not paper_ids:
            return []

        papers = session.exec(select(Paper).where(Paper.id.in_(paper_ids))).all()
        paper_map = {paper.id: paper for paper in papers}
        hits: list[SearchHit] = []
        for paper_id, rank in rows:
            paper = paper_map.get(paper_id)
            if paper is None:
                continue
            if year is not None and paper.year != year:
                continue
            if location and paper.location != location.lower():
                continue
            score = 1.0 / (1.0 + abs(float(rank)))
            snippet = paper.abstract or paper.searchable_text[:280]
            hits.append(SearchHit(paper=paper, score=score, snippet=snippet))

        return hits[:limit]


def semantic_search(
    query_text: str,
    *,
    limit: int = 25,
    paper_ids: list[int] | None = None,
    year: int | None = None,
    location: str | None = None,
) -> list[SearchHit]:
    if not query_text.strip():
        return []

    collection = _get_chroma_collection()
    results = collection.query(
        query_embeddings=embed_texts([query_text]),
        n_results=max(limit * 3, 10),
    )

    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ranked_ids: list[int] = []
    snippets: dict[int, str] = {}
    scores: dict[int, float] = {}

    for metadata, document, distance in zip(metadatas, documents, distances, strict=False):
        paper_id = int(metadata["paper_id"])
        if paper_ids and paper_id not in paper_ids:
            continue
        ranked_ids.append(paper_id)
        snippets.setdefault(paper_id, document[:400])
        score = 1.0 / (1.0 + float(distance))
        scores[paper_id] = max(scores.get(paper_id, 0.0), score)

    if not ranked_ids:
        return []

    unique_ids = list(dict.fromkeys(ranked_ids))
    with Session(engine) as session:
        papers = session.exec(select(Paper).where(Paper.id.in_(unique_ids))).all()
        paper_map = {paper.id: paper for paper in papers}

    hits: list[SearchHit] = []
    for paper_id in unique_ids:
        paper = paper_map.get(paper_id)
        if paper is None:
            continue
        if year is not None and paper.year != year:
            continue
        if location and paper.location != location.lower():
            continue
        hits.append(
            SearchHit(
                paper=paper,
                score=scores[paper_id],
                snippet=snippets.get(paper_id, paper.abstract or paper.title),
            )
        )

    return hits[:limit]


def hybrid_search(
    query_text: str,
    *,
    limit: int = 25,
    year: int | None = None,
    location: str | None = None,
) -> list[SearchHit]:
    keyword_hits = keyword_search(query_text, limit=limit, year=year, location=location)
    semantic_hits = semantic_search(query_text, limit=limit, year=year, location=location)
    merged: dict[int, SearchHit] = {}

    for hit in keyword_hits:
        merged[hit.paper.id] = hit

    for hit in semantic_hits:
        existing = merged.get(hit.paper.id)
        if existing is None:
            merged[hit.paper.id] = hit
            continue
        existing.score = max(existing.score, hit.score)
        if len(existing.snippet) < len(hit.snippet):
            existing.snippet = hit.snippet

    ordered = sorted(
        merged.values(),
        key=lambda item: (item.score, item.paper.year, item.paper.title),
        reverse=True,
    )
    return ordered[:limit]


def get_stats() -> dict[str, Any]:
    with Session(engine) as session:
        paper_count = session.exec(select(Paper)).all()
        conference_count = session.exec(select(Conference)).all()
        years = {paper.year for paper in paper_count}
        locations = {paper.location for paper in paper_count}
        return {
            "paper_count": len(paper_count),
            "year_count": len(years),
            "conference_count": len(conference_count),
            "locations": sorted(locations),
            "years": sorted(years, reverse=True),
        }


def get_paper(paper_id: int) -> Paper | None:
    with Session(engine) as session:
        return session.get(Paper, paper_id)


def get_paper_chunks(paper_id: int) -> list[Chunk]:
    with Session(engine) as session:
        return session.exec(
            select(Chunk).where(Chunk.paper_id == paper_id).order_by(Chunk.chunk_index)
        ).all()
