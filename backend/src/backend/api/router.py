from __future__ import annotations

from fastapi import APIRouter

from backend.api.routes import admin, chat, health, papers, search, stats


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(stats.router)
api_router.include_router(search.router)
api_router.include_router(papers.router)
api_router.include_router(chat.router)
api_router.include_router(admin.router)
