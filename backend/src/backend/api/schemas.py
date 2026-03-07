from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class StatsResponse(BaseModel):
    paper_count: int
    year_count: int
    conference_count: int
    years: list[int]
    locations: list[str]


class SearchResultItem(BaseModel):
    paper_id: int
    title: str
    abstract: str
    authors: list[str]
    affiliations: list[str]
    year: int
    location: str
    conference_name: str | None = None
    score: float
    snippet: str


class SearchResponse(BaseModel):
    mode: Literal["keyword", "semantic", "hybrid"]
    items: list[SearchResultItem]


class PaperDetailResponse(BaseModel):
    paper_id: int
    title: str
    authors: list[str]
    abstract: str
    affiliations: list[str]
    references: list[str]
    year: int
    location: str
    conference_name: str | None = None
    source_url: str
    pdf_url: str
    pdf_path: str
    markdown_path: str | None = None
    tei_path: str | None = None


class MarkdownResponse(BaseModel):
    paper_id: int
    title: str
    markdown: str
    markdown_path: str


class GraphResponse(BaseModel):
    paper_id: int
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    selected_paper_ids: list[int] = []
    messages: list[ChatMessage]


class ChatCitation(BaseModel):
    title: str
    year: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation]
    scope_paper_ids: list[int]


class IngestRequest(BaseModel):
    limit: int | None = None
    force: bool = False


class IngestResponse(BaseModel):
    indexed_count: int
    paper_ids: list[int]
