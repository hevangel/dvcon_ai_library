from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session

from backend.api.schemas import GraphResponse, MarkdownResponse, PaperDetailResponse
from backend.core.config import get_settings
from backend.db.models import Paper
from backend.db.session import engine
from backend.services.graph import build_paper_graph


router = APIRouter(prefix="/papers", tags=["papers"])


def _split_authors(authors_text: str) -> list[str]:
    normalized = authors_text.replace(" and ", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


@router.get("/{paper_id}", response_model=PaperDetailResponse)
def read_paper(paper_id: int) -> PaperDetailResponse:
    with Session(engine) as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found.")

        references = [reference.citation_text for reference in paper.references]
        affiliations = [line.strip() for line in paper.affiliations_text.splitlines() if line.strip()]
        conference_name = paper.conference.name if paper.conference else f"DVCon {paper.location.title()} {paper.year}"

        return PaperDetailResponse(
            paper_id=paper.id or 0,
            title=paper.title,
            authors=_split_authors(paper.authors_text),
            abstract=paper.abstract or "",
            affiliations=affiliations,
            references=references,
            year=paper.year,
            location=paper.location,
            conference_name=conference_name,
            source_url=paper.source_url,
            pdf_url=paper.pdf_url,
            pdf_path=paper.pdf_path,
            markdown_path=paper.markdown_path,
            tei_path=paper.tei_path,
        )


@router.get("/{paper_id}/pdf")
def read_paper_pdf(paper_id: int) -> FileResponse:
    settings = get_settings()
    with Session(engine) as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found.")

        file_path = settings.repo_root / paper.pdf_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found.")

        return FileResponse(file_path, media_type="application/pdf", filename=Path(file_path).name)


@router.get("/{paper_id}/markdown", response_model=MarkdownResponse)
def read_paper_markdown(paper_id: int) -> MarkdownResponse:
    settings = get_settings()
    with Session(engine) as session:
        paper = session.get(Paper, paper_id)
        if paper is None or not paper.markdown_path:
            raise HTTPException(status_code=404, detail="Markdown file not found.")

        file_path = settings.repo_root / paper.markdown_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Markdown file not found.")

        return MarkdownResponse(
            paper_id=paper.id or 0,
            title=paper.title,
            markdown=file_path.read_text(encoding="utf-8"),
            markdown_path=paper.markdown_path,
        )


@router.get("/{paper_id}/graph", response_model=GraphResponse)
def read_paper_graph(paper_id: int) -> GraphResponse:
    graph = build_paper_graph(paper_id)
    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail="Paper not found.")

    return GraphResponse(paper_id=paper_id, nodes=graph["nodes"], edges=graph["edges"])
