from __future__ import annotations

import threading

from fastapi import APIRouter, Header, HTTPException

from backend.api.schemas import IngestRequest, IngestResponse
from backend.core.config import get_settings
from backend.services.indexer import run_ingestion


router = APIRouter(prefix="/admin", tags=["admin"])

# Ingest crawls the DVCon archive, downloads PDFs, runs GROBID, embeds on the
# GPU, and mutates both Chroma and SQLite. Two concurrent ingests corrupt the
# Chroma collection and race on the manifest, so serialize them process-wide.
# (Ingest handlers run sync, in FastAPI's threadpool — a threading.Lock is the
# right primitive, not asyncio.)
_ingest_lock = threading.Lock()


def _verify_admin_token(x_admin_token: str | None) -> None:
    """Optional token guard for the ingest endpoint.

    When `INGEST_ADMIN_TOKEN` is unset the endpoint stays open (local-dev mode).
    When set, callers must send a matching `X-Admin-Token` header.
    """
    expected = get_settings().ingest_admin_token
    if not expected:
        return
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid admin token.")


@router.post("/ingest", response_model=IngestResponse)
def ingest_archive(
    payload: IngestRequest,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> IngestResponse:
    _verify_admin_token(x_admin_token)

    # Non-blocking: a second ingest while one is running returns 409 rather
    # than queuing (ingest can take hours; queuing would pin threadpool workers
    # and still serialize eventually — better to fail fast).
    if not _ingest_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="An ingest is already running.")

    try:
        papers = run_ingestion(limit=payload.limit, force=payload.force)
    finally:
        _ingest_lock.release()

    return IngestResponse(
        indexed_count=len(papers),
        paper_ids=[paper.id or 0 for paper in papers],
    )
