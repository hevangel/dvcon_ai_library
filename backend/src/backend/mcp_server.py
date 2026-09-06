"""Model Context Protocol (MCP) server for the DVCon paper corpus.

Exposes the same paper search, detail, markdown, graph, stats, and grounded
chat capabilities as the FastAPI HTTP API, but over MCP stdio transport so
that MCP-compatible agent clients (Claude Code, ZCode, Cursor, etc.) can call
them as tools.

The server reuses the existing service layer in `backend.services.*`; it does
not duplicate business logic. It is a FastMCP 4 stdio server (`from fastmcp
import FastMCP`). Run it with the `dvcon-mcp` console script:

    uv run --project backend dvcon-mcp

Configure the target corpus via the same `.env` settings used by the HTTP
backend (`DATA_DIR`, embedding model, GROBID, OpenAI chat keys, etc.). Only
the chat tool requires `OPENAI_BASE_URL` / `OPENAI_API_KEY`; the read tools
work without GROBID or OpenAI configured.
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from backend.db.session import create_db_and_tables
from backend.services.chat import answer_question
from backend.services.graph import build_paper_graph
from backend.services.indexer import (
    get_paper,
    get_stats,
    hybrid_search,
    keyword_search,
    semantic_search,
)
from backend.core.config import get_settings


mcp = FastMCP("dvcon-papers")


def _hit_to_dict(hit: Any) -> dict[str, Any]:
    paper = hit.paper
    return {
        "paper_id": paper.id,
        "title": paper.title,
        "abstract": paper.abstract or "",
        "authors": [part.strip() for part in paper.authors_text.replace(" and ", ",").split(",") if part.strip()],
        "affiliations": [line.strip() for line in paper.affiliations_text.splitlines() if line.strip()],
        "year": paper.year,
        "location": paper.location,
        "conference_name": f"DVCon {paper.location.title()} {paper.year}",
        "score": hit.score,
        "snippet": hit.snippet,
    }


@mcp.tool()
def search_papers(
    query: str = "",
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid",
    year: int | None = None,
    location: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search the DVCon paper corpus.

    Modes:
      - keyword: SQLite FTS5 full-text match (fast, exact-ish).
      - semantic: local bge-m3 embeddings via ChromaDB (concept matches).
      - hybrid (default): merge keyword + semantic results.

    Leave `query` empty to list papers. `year` and `location` are optional
    filters (location is case-insensitive e.g. "united states").
    """
    if mode == "keyword":
        hits = keyword_search(query, limit=limit, year=year, location=location)
    elif mode == "semantic":
        hits = semantic_search(query, limit=limit, year=year, location=location)
    else:
        hits = hybrid_search(query, limit=limit, year=year, location=location)

    return {"mode": mode, "count": len(hits), "items": [_hit_to_dict(hit) for hit in hits]}


@mcp.tool()
def get_paper_detail(paper_id: int) -> dict[str, Any]:
    """Full metadata for one paper: title, abstract, authors, affiliations,
    references, year, location, source URLs, and on-disk paths."""
    paper = get_paper(paper_id)
    if paper is None:
        return {"error": f"Paper {paper_id} not found."}

    references = [reference.citation_text for reference in paper.references]
    affiliations = [line.strip() for line in paper.affiliations_text.splitlines() if line.strip()]
    conference_name = (
        paper.conference.name
        if paper.conference
        else f"DVCon {paper.location.title()} {paper.year}"
    )

    return {
        "paper_id": paper.id,
        "title": paper.title,
        "authors": [part.strip() for part in paper.authors_text.replace(" and ", ",").split(",") if part.strip()],
        "abstract": paper.abstract or "",
        "affiliations": affiliations,
        "reference_count": len(references),
        "references": references,
        "year": paper.year,
        "location": paper.location,
        "conference_name": conference_name,
        "source_url": paper.source_url,
        "pdf_url": paper.pdf_url,
        "pdf_path": paper.pdf_path,
        "markdown_path": paper.markdown_path,
        "tei_path": paper.tei_path,
    }


@mcp.tool()
def get_paper_markdown(paper_id: int) -> dict[str, Any]:
    """Return the extracted markdown body for a paper, with its on-disk path.

    Image references inside the markdown are markdown-relative (`images/...`).
    """
    settings = get_settings()
    paper = get_paper(paper_id)
    if paper is None or not paper.markdown_path:
        return {"error": f"Markdown for paper {paper_id} is not available."}

    file_path = settings.repo_root / paper.markdown_path
    if not file_path.exists():
        return {"error": f"Markdown file for paper {paper_id} is missing on disk."}

    return {
        "paper_id": paper.id,
        "title": paper.title,
        "markdown_path": paper.markdown_path,
        "markdown": file_path.read_text(encoding="utf-8"),
    }


@mcp.tool()
def get_paper_graph(paper_id: int) -> dict[str, Any]:
    """Metadata graph for a paper: paper / conference / author / company /
    reference nodes and their edges, suitable for graph visualization."""
    graph = build_paper_graph(paper_id)
    if not graph["nodes"]:
        return {"error": f"Paper {paper_id} not found."}

    return {
        "paper_id": paper_id,
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"]),
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }


@mcp.tool()
def corpus_stats() -> dict[str, Any]:
    """Corpus summary: paper count, distinct years and locations, and
    conference collection count."""
    return get_stats()


@mcp.tool()
def chat_with_papers(
    question: str,
    selected_paper_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Ask a grounded question against the corpus.

    When `selected_paper_ids` is provided, the answer is constrained to those
    papers (full paper text when it fits the model context, else curated
    sections). Without a selection, retrieval runs across the whole corpus.

    Requires OPENAI_BASE_URL and OPENAI_API_KEY in the environment. Returns the
    answer plus numbered citations referencing the scoped/retrieved papers.
    """
    messages = [{"role": "user", "content": question}]
    try:
        result = answer_question(
            messages=messages,
            selected_paper_ids=selected_paper_ids or [],
        )
    except RuntimeError as exc:
        return {"error": str(exc)}

    return {
        "answer": result.answer,
        "citations": result.citations,
        "scope_paper_ids": result.scope_paper_ids,
    }


def main() -> None:
    """Entry point for the `dvcon-mcp` console script.

    Ensures the SQLite tables exist, then runs the MCP server over stdio.
    """
    create_db_and_tables()
    mcp.run()


if __name__ == "__main__":
    main()
