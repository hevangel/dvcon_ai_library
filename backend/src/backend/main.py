from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.api.router import api_router
from backend.core.config import get_settings
from backend.db.session import create_db_and_tables


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/assets/{file_path:path}", include_in_schema=False)
def read_asset(file_path: str) -> FileResponse:
    target_path = (settings.repo_root / file_path).resolve()
    repo_root = settings.repo_root.resolve()
    if not str(target_path).startswith(str(repo_root)):
        raise HTTPException(status_code=404, detail="Asset not found.")
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(target_path)


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def serve_frontend(full_path: str) -> FileResponse | JSONResponse:
    dist_dir = settings.frontend_dist_dir
    if not dist_dir.exists():
        return JSONResponse(
            {
                "message": "Frontend build not found. Run `npm run build` in the frontend directory.",
                "api_prefix": settings.api_prefix,
            }
        )

    requested_path = (dist_dir / full_path).resolve()
    if full_path and requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)

    index_path = dist_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index not found.")

    return FileResponse(index_path)


def run() -> None:
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    run()
