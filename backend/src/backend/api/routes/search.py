from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from backend.api.schemas import SearchResponse, SearchResultItem
from backend.services.indexer import hybrid_search, keyword_search, semantic_search


router = APIRouter(prefix="/search", tags=["search"])


def _authors_list(authors_text: str) -> list[str]:
    normalized = authors_text.replace(" and ", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _affiliation_list(affiliations_text: str) -> list[str]:
    return [line.strip() for line in affiliations_text.splitlines() if line.strip()]


@router.get("", response_model=SearchResponse)
def search_papers(
    query: str = Query(default=""),
    mode: Literal["keyword", "semantic", "hybrid"] = Query(default="hybrid"),
    year: int | None = Query(default=None),
    location: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
) -> SearchResponse:
    if mode == "keyword":
        hits = keyword_search(query, limit=limit, year=year, location=location)
    elif mode == "semantic":
        hits = semantic_search(query, limit=limit, year=year, location=location)
    else:
        hits = hybrid_search(query, limit=limit, year=year, location=location)

    items = [
        SearchResultItem(
            paper_id=hit.paper.id or 0,
            title=hit.paper.title,
            abstract=hit.paper.abstract or "",
            authors=_authors_list(hit.paper.authors_text),
            affiliations=_affiliation_list(hit.paper.affiliations_text),
            year=hit.paper.year,
            location=hit.paper.location,
            conference_name=f"DVCon {hit.paper.location.title()} {hit.paper.year}",
            score=hit.score,
            snippet=hit.snippet,
        )
        for hit in hits
    ]
    return SearchResponse(mode=mode, items=items)
