from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas import StatsResponse
from backend.services.indexer import get_stats


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def read_stats() -> StatsResponse:
    return StatsResponse.model_validate(get_stats())
