"""Route-layer tests for the FastAPI API.

These exercise each endpoint through TestClient, monkeypatching the service
functions the routes import (matching the established style in test_smoke.py).
The papers routes talk directly to the DB via Session(engine), so for those we
swap in a fake Session whose __enter__ returns a fake session object.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from backend.db.models import Paper, ReferenceEntry
from backend.main import app
from backend.services.indexer import SearchHit


# --------------------------------------------------------------------------- #
# /api/stats
# --------------------------------------------------------------------------- #
def test_stats_endpoint_returns_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.api.routes.stats.get_stats",
        lambda: {
            "paper_count": 18,
            "year_count": 4,
            "conference_count": 4,
            "years": [2025, 2024, 2022, 2021],
            "locations": ["india", "united states"],
        },
    )

    response = TestClient(app).get("/api/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["paper_count"] == 18
    assert body["year_count"] == 4
    assert body["years"] == [2025, 2024, 2022, 2021]
    assert body["locations"] == ["india", "united states"]


# --------------------------------------------------------------------------- #
# /api/search — mode dispatch + serialization
# --------------------------------------------------------------------------- #
def _sample_hit(paper_id: int, title: str, year: int, location: str) -> SearchHit:
    paper = Paper(
        id=paper_id,
        source_url=f"https://example.com/p{paper_id}",
        pdf_url=f"https://example.com/p{paper_id}.pdf",
        slug=f"p{paper_id}",
        title=title,
        year=year,
        location=location,
        authors_text="Alice Example and Bob Example",
        affiliations_text="Example Semiconductor\nVerification Labs",
        abstract="A grounded abstract.",
        pdf_path=f"data/paper/{year}/{location}/p{paper_id}.pdf",
    )
    return SearchHit(paper=paper, score=0.82, snippet="snippet text")


def test_search_endpoint_dispatches_hybrid_and_serializes(monkeypatch) -> None:
    calls: dict[str, Any] = {}

    def fake_hybrid(query, *, limit, year, location):
        calls["hybrid"] = (query, limit, year, location)
        return [_sample_hit(7, "Hybrid Paper", 2024, "united states")]

    monkeypatch.setattr("backend.api.routes.search.hybrid_search", fake_hybrid)
    monkeypatch.setattr("backend.api.routes.search.keyword_search", lambda *a, **k: [])
    monkeypatch.setattr("backend.api.routes.search.semantic_search", lambda *a, **k: [])

    response = TestClient(app).get(
        "/api/search",
        params={"query": "uvm", "mode": "hybrid", "year": 2024, "location": "united states", "limit": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hybrid"
    assert calls["hybrid"] == ("uvm", 10, 2024, "united states")
    item = body["items"][0]
    assert item["paper_id"] == 7
    assert item["authors"] == ["Alice Example", "Bob Example"]
    assert item["affiliations"] == ["Example Semiconductor", "Verification Labs"]
    assert item["conference_name"] == "DVCon United States 2024"
    assert item["score"] == 0.82


def test_search_endpoint_dispatches_keyword_mode(monkeypatch) -> None:
    calls: dict[str, int] = {"keyword": 0}

    def fake_keyword(*args, **kwargs):
        calls["keyword"] += 1
        return [_sample_hit(1, "Keyword Paper", 2025, "india")]

    monkeypatch.setattr("backend.api.routes.search.keyword_search", fake_keyword)
    monkeypatch.setattr("backend.api.routes.search.hybrid_search", lambda *a, **k: [])
    monkeypatch.setattr("backend.api.routes.search.semantic_search", lambda *a, **k: [])

    body = TestClient(app).get("/api/search", params={"mode": "keyword"}).json()
    assert calls["keyword"] == 1
    assert body["items"][0]["title"] == "Keyword Paper"


# --------------------------------------------------------------------------- #
# /api/papers/* — fake Session pattern
# --------------------------------------------------------------------------- #
class _FakeSession:
    """Minimal Session stand-in for the papers routes.

    The routes use `with Session(engine) as session: session.get(Paper, id)`
    and read `paper.references`, `paper.affiliations_text`, `paper.conference`.
    """

    def __init__(self, paper: Paper | None) -> None:
        self._paper = paper

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, model, paper_id):  # noqa: ANN001 - matches Session.get signature shape
        return self._paper


def _seeded_paper() -> Paper:
    paper = Paper(
        id=5,
        source_url="https://example.com/p5",
        pdf_url="https://example.com/p5.pdf",
        slug="p5",
        title="Seeded Paper",
        year=2023,
        location="united states",
        authors_text="Carol Writer",
        affiliations_text="Example Semiconductor",
        abstract="Abstract.",
        pdf_path="data/paper/2023/united states/p5.pdf",
        markdown_path="data/markdown/2023/united states/p5.md",
        tei_path="data/tei/2023/united states/p5.tei.xml",
    )
    paper.references = [ReferenceEntry(citation_text="A reference entry.")]
    return paper


def test_paper_detail_endpoint_returns_200(monkeypatch) -> None:
    paper = _seeded_paper()
    monkeypatch.setattr("backend.api.routes.papers.Session", lambda engine: _FakeSession(paper))

    response = TestClient(app).get("/api/papers/5")
    assert response.status_code == 200
    body = response.json()
    assert body["paper_id"] == 5
    assert body["title"] == "Seeded Paper"
    assert body["authors"] == ["Carol Writer"]
    assert body["affiliations"] == ["Example Semiconductor"]
    assert body["references"] == ["A reference entry."]
    assert body["tei_path"] == "data/tei/2023/united states/p5.tei.xml"


def test_paper_detail_endpoint_returns_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.routes.papers.Session", lambda engine: _FakeSession(None))
    assert TestClient(app).get("/api/papers/999").status_code == 404


# --------------------------------------------------------------------------- #
# /api/chat — error path (RuntimeError -> 503)
# --------------------------------------------------------------------------- #
def test_chat_endpoint_returns_503_on_runtime_error(monkeypatch) -> None:
    def raise_error(**kwargs):
        raise RuntimeError("The chat provider is currently unreachable.")

    monkeypatch.setattr("backend.api.routes.chat.answer_question", raise_error)

    response = TestClient(app).post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# /api/admin/ingest — happy path, concurrency 409, token guard
# --------------------------------------------------------------------------- #
def test_ingest_endpoint_returns_indexed_count(monkeypatch) -> None:
    paper = _seeded_paper()
    monkeypatch.setattr(
        "backend.api.routes.admin.run_ingestion",
        lambda *, limit, force: [paper],
    )

    response = TestClient(app).post("/api/admin/ingest", json={"limit": 1, "force": False})
    assert response.status_code == 200
    body = response.json()
    assert body["indexed_count"] == 1
    assert body["paper_ids"] == [5]


def test_ingest_endpoint_rejects_concurrent_call(monkeypatch) -> None:
    import threading

    from backend.api.routes import admin

    # Hold the lock as if another ingest is mid-flight; release in cleanup.
    assert admin._ingest_lock.acquire(blocking=False)
    try:
        monkeypatch.setattr("backend.api.routes.admin.run_ingestion", lambda *, limit, force: [])
        response = TestClient(app).post("/api/admin/ingest", json={})
        assert response.status_code == 409
        assert "already running" in response.json()["detail"]
    finally:
        admin._ingest_lock.release()


def test_ingest_endpoint_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.routes.admin.get_settings", lambda: SimpleNamespace(ingest_admin_token="secret"))
    monkeypatch.setattr("backend.api.routes.admin.run_ingestion", lambda *, limit, force: [])

    # No header -> 401
    no_header = TestClient(app).post("/api/admin/ingest", json={})
    assert no_header.status_code == 401

    # Wrong header -> 401
    wrong = TestClient(app).post("/api/admin/ingest", json={}, headers={"X-Admin-Token": "wrong"})
    assert wrong.status_code == 401

    # Correct header -> 200
    ok = TestClient(app).post("/api/admin/ingest", json={}, headers={"X-Admin-Token": "secret"})
    assert ok.status_code == 200


def test_ingest_endpoint_open_when_no_token_configured(monkeypatch) -> None:
    # Default settings have ingest_admin_token=None, so the endpoint is open.
    monkeypatch.setattr("backend.api.routes.admin.run_ingestion", lambda *, limit, force: [])
    response = TestClient(app).post("/api/admin/ingest", json={})
    assert response.status_code == 200
