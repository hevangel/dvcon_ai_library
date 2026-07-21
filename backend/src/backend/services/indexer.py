from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import logging
import re
import time
from typing import Any

import chromadb
from sqlalchemy.exc import OperationalError
from sqlalchemy import delete, func, text
from sqlmodel import Session, select

from backend.core.config import get_settings
from backend.db.models import (
    Affiliation,
    Author,
    AuthorAffiliation,
    Chunk,
    Company,
    Conference,
    Paper,
    PaperAuthor,
    ReferenceEntry,
)
from backend.db.session import engine
from backend.services.embeddings import embed_texts
from backend.services.extractor import ExtractedPaper, extract_pdf
from backend.services.scraper import ManifestStore, PaperSeed, crawl_archive
from backend.services.tei_parser import ParsedAffiliation, ParsedAuthor, ParsedReference


DATABASE_LOCK_RETRY_ATTEMPTS = 5
DATABASE_LOCK_RETRY_SECONDS = 5

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SearchHit:
    paper: Paper
    score: float
    snippet: str


def _fts_match_query(query_text: str) -> str:
    tokens = re.findall(r"[0-9A-Za-z]+(?:'[0-9A-Za-z]+)?", query_text.casefold())
    unique_tokens = list(dict.fromkeys(token for token in tokens if token))
    return " OR ".join(f'"{token}"' for token in unique_tokens)


def _get_chroma_collection():
    """Return the (cached) paper_chunks Chroma collection for the configured model.

    The PersistentClient and collection are cached so reads (search/chat) and
    writes (ingest) share one client/connection. If the on-disk collection was
    built with a different embedding model than the current setting, we raise
    rather than silently wiping the index — a settings typo must not destroy
    hundreds of embedded papers. Set `ALLOW_CHROMA_WIPE=1` to restore the old
    auto-reset behavior, or run `ingest --force` to rebuild deliberately.
    """
    collection = _cached_chroma_collection()
    existing_metadata = collection.metadata or {}
    if existing_metadata.get("embedding_model") != _desired_embedding_model():
        if not get_settings().allow_chroma_wipe:
            raise RuntimeError(
                "Chroma collection was built with embedding model "
                f"{existing_metadata.get('embedding_model')!r} but the current "
                f"setting is {_desired_embedding_model()!r}. "
                "Run `uv run --project backend ingest --limit 1 --force` to rebuild, "
                "or set ALLOW_CHROMA_WIPE=1 to allow automatic reset."
            )
        # Explicit opt-in path: reset and re-cache.
        client = _cached_chroma_client()
        client.delete_collection(name="paper_chunks")
        _cached_chroma_collection.cache_clear()
        collection = _cached_chroma_collection()
    return collection


@lru_cache(maxsize=1)
def _cached_chroma_client():
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.chroma_dir.as_posix())


@lru_cache(maxsize=1)
def _cached_chroma_collection():
    settings = get_settings()
    client = _cached_chroma_client()
    desired_metadata = {
        "embedding_backend": "sentence_transformers",
        "embedding_model": settings.local_embedding_model,
    }
    return client.get_or_create_collection(name="paper_chunks", metadata=desired_metadata)


@lru_cache(maxsize=1)
def _desired_embedding_model() -> str:
    return get_settings().local_embedding_model


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
    paper.updated_at = datetime.now(timezone.utc)
    session.add(paper)
    session.flush()
    return paper


def _get_or_create_company(session: Session, company_name: str) -> Company:
    company = session.exec(select(Company).where(Company.name == company_name)).first()
    if company is not None:
        return company

    company = Company(name=company_name)
    session.add(company)
    session.flush()
    return company


def _get_or_create_affiliation(
    session: Session,
    affiliation_name: str,
    structured_by_name: dict[str, ParsedAffiliation] | None = None,
) -> Affiliation:
    affiliation = session.exec(select(Affiliation).where(Affiliation.name == affiliation_name)).first()
    structured = (structured_by_name or {}).get(affiliation_name.casefold())

    if affiliation is not None:
        # Backfill structured fields on legacy rows when newly available.
        if structured is not None:
            _populate_affiliation_structured_fields(session, affiliation, structured)
        return affiliation

    affiliation = Affiliation(name=affiliation_name)
    if structured is not None:
        affiliation.city = structured.city
        affiliation.state_province = structured.state_province
        affiliation.country = structured.country
        if structured.company_name:
            affiliation.company = _get_or_create_company(session, structured.company_name)
    session.add(affiliation)
    session.flush()
    return affiliation


def _populate_affiliation_structured_fields(
    session: Session, affiliation: Affiliation, structured: ParsedAffiliation
) -> None:
    changed = False
    if affiliation.city is None and structured.city:
        affiliation.city = structured.city
        changed = True
    if affiliation.state_province is None and structured.state_province:
        affiliation.state_province = structured.state_province
        changed = True
    if affiliation.country is None and structured.country:
        affiliation.country = structured.country
        changed = True
    if affiliation.company_id is None and structured.company_name:
        affiliation.company = _get_or_create_company(session, structured.company_name)
        changed = True
    if changed:
        session.add(affiliation)
        session.flush()


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


def _sync_authors(
    session: Session,
    paper: Paper,
    authors: list[ParsedAuthor],
    affiliations: list[str],
    affiliations_structured: list[ParsedAffiliation] | None = None,
) -> None:
    session.exec(delete(PaperAuthor).where(PaperAuthor.paper_id == paper.id))
    session.exec(delete(AuthorAffiliation).where(AuthorAffiliation.paper_id == paper.id))
    session.flush()

    structured_by_name = {
        item.name.casefold(): item for item in (affiliations_structured or [])
    }

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
            affiliation = _get_or_create_affiliation(
                session,
                affiliation_name,
                structured_by_name=structured_by_name,
            )
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


def _sync_chunks(session: Session, paper: Paper, chunks: list[dict[str, str]]) -> list[str]:
    """Sync chunk rows + Chroma vectors for a paper.

    Returns the list of Chroma ids added this call so the caller can compensate
    (delete them from Chroma) if the SQL commit subsequently fails, keeping
    Chroma and SQLite consistent.
    """
    collection = _get_chroma_collection()
    existing_chunks = session.exec(select(Chunk).where(Chunk.paper_id == paper.id)).all()
    if existing_chunks:
        collection.delete(ids=[chunk.chroma_id for chunk in existing_chunks])
        session.exec(delete(Chunk).where(Chunk.paper_id == paper.id))

    if not chunks:
        return []

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
    return ids


def _rollback_chroma_ids(added_ids: list[str]) -> None:
    """Best-effort compensation: delete just-added Chroma vectors if the SQL
    commit failed, so the indexes don't drift out of sync. Swallows Chroma
    errors (already in a failure path) but logs them.
    """
    if not added_ids:
        return
    try:
        _get_chroma_collection().delete(ids=added_ids)
    except Exception:  # noqa: BLE001 - compensation must not mask the original error
        logger.warning("Could not roll back Chroma ids %s after a failed commit", added_ids, exc_info=True)


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
        paper.last_ingested_at = datetime.now(timezone.utc)
        paper.updated_at = datetime.now(timezone.utc)

        _sync_authors(
            session,
            paper,
            extracted.authors,
            extracted.affiliations,
            extracted.affiliations_structured,
        )
        _sync_references(session, paper, extracted.references)
        added_chroma_ids = _sync_chunks(session, paper, chunks)
        _sync_fts(session, paper)

        session.add(paper)
        try:
            session.commit()
        except Exception:
            # SQL commit failed (disk full, integrity error, lock). Chroma was
            # already mutated with the new vectors; compensate by removing them
            # so the indexes stay consistent, then re-raise so run_ingestion
            # logs and continues with the next paper.
            _rollback_chroma_ids(added_chroma_ids)
            raise
        session.refresh(paper)
        return paper


def _is_sqlite_database_locked(error: OperationalError) -> bool:
    return "database is locked" in str(error).lower()


def _derived_artifact_exists(relative_path: str | None) -> bool:
    if not relative_path:
        return False

    settings = get_settings()
    return (settings.repo_root / relative_path).exists()


def _paper_needs_ingestion(session: Session, seed: PaperSeed) -> bool:
    paper = session.exec(select(Paper).where(Paper.source_url == seed.source_url)).first()
    if paper is None:
        return True

    if paper.last_ingested_at is None:
        return True

    if not _derived_artifact_exists(paper.pdf_path):
        return True

    if not _derived_artifact_exists(paper.markdown_path):
        return True

    tracked_fields = (
        paper.pdf_url != seed.pdf_url,
        paper.slug != seed.slug,
        paper.title != seed.title,
        paper.year != seed.year,
        paper.location != seed.location,
        paper.document_type != seed.document_type,
        paper.authors_text != seed.authors_text,
        paper.pdf_path != seed.pdf_path,
    )
    return any(tracked_fields)


def run_ingestion(*, limit: int | None = None, force: bool = False, years: list[int] | None = None) -> list[Paper]:
    seeds = crawl_archive(limit=limit, force=force, years=years)
    if force:
        seeds_to_index = seeds
    else:
        with Session(engine) as session:
            seeds_to_index = [seed for seed in seeds if _paper_needs_ingestion(session, seed)]

    papers: list[Paper] = []
    for seed in seeds_to_index:
        try:
            papers.append(_index_seed_with_lock_retries(seed))
        except OperationalError:
            # A persistent DB-lock failure is infrastructure-level; re-raise so
            # the caller knows the writer is wedged rather than silently skipping.
            raise
        except Exception as error:  # noqa: BLE001 - isolate one bad paper from the batch
            # Per-paper isolation: a corrupt PDF, GROBID hiccup, embedding OOM,
            # or Chroma error must not abort the rest of the batch. Log and move on.
            logger.exception("Failed to index paper %s; continuing with the rest of the batch", seed.source_url)
            _record_indexing_error(seed, error)
    return papers


def _index_seed_with_lock_retries(seed: PaperSeed) -> Paper:
    """Index a single seed, retrying only on transient SQLite database-lock errors."""
    for attempt in range(DATABASE_LOCK_RETRY_ATTEMPTS + 1):
        try:
            return index_seed(seed)
        except OperationalError as error:
            if not _is_sqlite_database_locked(error) or attempt >= DATABASE_LOCK_RETRY_ATTEMPTS:
                raise
            time.sleep(DATABASE_LOCK_RETRY_SECONDS * (attempt + 1))
    # Unreachable: the loop either returns or raises, but keep a defensive fallback.
    raise RuntimeError(f"Exhausted retries indexing {seed.source_url}")


def _record_indexing_error(seed: PaperSeed, error: Exception) -> None:
    """Best-effort: note an indexing-stage failure in the ingest manifest.

    Download-stage errors are already recorded by `crawl_archive`; this covers
    failures that occur after a successful download (extraction/embedding/index).
    Swallows manifest-write errors since they must not mask the original failure.
    """
    try:
        settings = get_settings()
        manifest = ManifestStore(settings.manifest_path)
        manifest.update(seed.source_url, status="index_error", error=f"{type(error).__name__}: {error}")
        manifest.save()
    except Exception:  # noqa: BLE001 - manifest is best-effort, never fatal
        logger.warning("Could not record indexing error for %s in the manifest", seed.source_url, exc_info=True)


def list_papers(
    *,
    limit: int = 25,
    paper_ids: list[int] | None = None,
    year: int | None = None,
    location: str | None = None,
    conference_id: int | None = None,
) -> list[Paper]:
    with Session(engine) as session:
        query = select(Paper).order_by(Paper.year.desc(), Paper.title)
        if paper_ids:
            query = query.where(Paper.id.in_(paper_ids))
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
    paper_ids: list[int] | None = None,
    year: int | None = None,
    location: str | None = None,
) -> list[SearchHit]:
    with Session(engine) as session:
        if not query_text.strip():
            return [
                SearchHit(paper=paper, score=1.0, snippet=paper.abstract or paper.title)
                for paper in list_papers(limit=limit, paper_ids=paper_ids, year=year, location=location)
            ]

        match_query = _fts_match_query(query_text)
        if not match_query:
            return []

        statement = text(
            """
            SELECT paper_id, bm25(paper_fts) AS rank
            FROM paper_fts
            WHERE paper_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
            """
        )
        rows = session.exec(statement, params={"query": match_query, "limit": limit * 3}).all()
        matched_paper_ids = [row[0] for row in rows]
        if not matched_paper_ids:
            return []

        # `paper_ids` is the caller's selected-paper scope filter (may be None for
        # corpus-wide search). Do NOT reassign it; keep it authoritative here.
        scope_paper_ids = paper_ids
        papers = session.exec(select(Paper).where(Paper.id.in_(matched_paper_ids))).all()
        paper_map = {paper.id: paper for paper in papers}
        hits: list[SearchHit] = []
        for paper_id, rank in rows:
            paper = paper_map.get(paper_id)
            if paper is None:
                continue
            if scope_paper_ids and paper.id not in scope_paper_ids:
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
    paper_ids: list[int] | None = None,
    year: int | None = None,
    location: str | None = None,
) -> list[SearchHit]:
    keyword_hits = keyword_search(query_text, limit=limit, paper_ids=paper_ids, year=year, location=location)
    semantic_hits = semantic_search(query_text, limit=limit, paper_ids=paper_ids, year=year, location=location)
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
        paper_count = session.exec(select(func.count(Paper.id))).one()
        conference_count = session.exec(select(func.count(Conference.id))).one()
        years = session.exec(select(Paper.year).distinct()).all()
        locations = session.exec(select(Paper.location).distinct()).all()
        return {
            "paper_count": paper_count,
            "year_count": len(years),
            "conference_count": conference_count,
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
