from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas import IngestRequest, IngestResponse
from backend.services.indexer import run_ingestion


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest", response_model=IngestResponse)
def ingest_archive(payload: IngestRequest) -> IngestResponse:
    papers = run_ingestion(limit=payload.limit, force=payload.force)
    return IngestResponse(
        indexed_count=len(papers),
        paper_ids=[paper.id or 0 for paper in papers],
    )
