"""Unit tests for the production-hardening changes.

Covers:
- PDF download integrity validation (magic bytes, content-length, parse check)
- run_ingestion per-paper error isolation (one bad paper doesn't abort the batch)
- Chroma no-silent-wipe (model mismatch raises unless ALLOW_CHROMA_WIPE=1)
- retry backoff honors Retry-After on 429
- atomic manifest save
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import backend.services.indexer as indexer_mod
from backend.db.models import Paper
from backend.services.scraper import ManifestStore, _retry_delay_seconds, _validate_pdf_response


# --------------------------------------------------------------------------- #
# download_pdf integrity validation
# --------------------------------------------------------------------------- #
def test_validate_pdf_response_rejects_html_body() -> None:
    class FakeResponse:
        content = b"<html><body>Cloudflare challenge</body></html>"
        headers: dict[str, str] = {}

    try:
        _validate_pdf_response("https://example.com/x.pdf", FakeResponse())
    except ValueError as error:
        assert "magic bytes" in str(error)
    else:  # pragma: no cover - sanity guard
        raise AssertionError("expected ValueError for non-PDF body")


def test_validate_pdf_response_rejects_truncated_download() -> None:
    class FakeResponse:
        content = b"%PDF-1.5 short"
        headers = {"Content-Length": "1000"}

    try:
        _validate_pdf_response("https://example.com/x.pdf", FakeResponse())
    except ValueError as error:
        assert "truncated" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for truncated download")


def test_validate_pdf_response_accepts_valid_pdf() -> None:
    content = b"%PDF-1.5\n...rest of pdf..."

    class FakeResponse:
        pass

    fake = FakeResponse()
    fake.content = content
    fake.headers = {"Content-Length": str(len(content))}

    # Should not raise.
    _validate_pdf_response("https://example.com/x.pdf", fake)


# --------------------------------------------------------------------------- #
# run_ingestion per-paper error isolation
# --------------------------------------------------------------------------- #
def test_run_ingestion_continues_past_a_failing_paper(monkeypatch) -> None:
    good_paper = Paper(
        id=1,
        source_url="https://example.com/good",
        pdf_url="https://example.com/good.pdf",
        slug="good",
        title="Good",
        year=2025,
        location="us",
        pdf_path="data/paper/2025/us/good.pdf",
    )

    seed_a = SimpleNamespace(source_url="https://example.com/a")
    seed_b = SimpleNamespace(source_url="https://example.com/b")
    seed_c = SimpleNamespace(source_url="https://example.com/c")

    call_log: list[str] = []

    def fake_index_seed_with_retries(seed):
        call_log.append(seed.source_url)
        if seed.source_url == "https://example.com/b":
            raise RuntimeError("corrupt PDF mid-batch")
        return good_paper

    # crawl_archive returns three seeds; force indexing all of them.
    monkeypatch.setattr(indexer_mod, "crawl_archive", lambda *, limit, force: [seed_a, seed_b, seed_c])
    monkeypatch.setattr(indexer_mod, "_paper_needs_ingestion", lambda session, seed: True)
    monkeypatch.setattr(indexer_mod, "_index_seed_with_lock_retries", fake_index_seed_with_retries)
    # Recording errors should be best-effort and not raise.
    monkeypatch.setattr(indexer_mod, "_record_indexing_error", lambda seed, error: None)
    # Avoid opening a real Session for the _paper_needs_ingestion scan.
    monkeypatch.setattr(indexer_mod, "Session", MagicMock())

    papers = indexer_mod.run_ingestion(limit=None, force=True)

    # The failing seed (b) is skipped; a and c still get indexed.
    assert call_log == ["https://example.com/a", "https://example.com/b", "https://example.com/c"]
    assert len(papers) == 2


# --------------------------------------------------------------------------- #
# Chroma no-silent-wipe
# --------------------------------------------------------------------------- #
def test_chroma_raises_on_embedding_model_mismatch(monkeypatch) -> None:
    fake_collection = SimpleNamespace(metadata={"embedding_model": "old-model"})
    monkeypatch.setattr(indexer_mod, "_cached_chroma_collection", lambda: fake_collection)
    monkeypatch.setattr(indexer_mod, "_desired_embedding_model", lambda: "new-model")
    monkeypatch.setattr(
        indexer_mod,
        "get_settings",
        lambda: SimpleNamespace(allow_chroma_wipe=False),
    )

    try:
        indexer_mod._get_chroma_collection()
    except RuntimeError as error:
        assert "ingest --limit 1 --force" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError on embedding-model mismatch")


# --------------------------------------------------------------------------- #
# retry backoff honors Retry-After on 429
# --------------------------------------------------------------------------- #
def test_retry_delay_honors_retry_after_header() -> None:
    class FakeResponse:
        status_code = 429
        headers = {"Retry-After": "7"}

    assert _retry_delay_seconds(0, FakeResponse()) == 7.0


def test_retry_delay_grows_exponentially_without_retry_after() -> None:
    class FakeResponse:
        status_code = 503
        headers: dict[str, str] = {}

    # base * 2**attempt + jitter (0 <= jitter <= base*0.5); base is 2s.
    for attempt in range(4):
        delay = _retry_delay_seconds(attempt, FakeResponse())
        assert 2 * (2**attempt) <= delay <= 2 * (2**attempt) + 1.0


# --------------------------------------------------------------------------- #
# Atomic manifest save
# --------------------------------------------------------------------------- #
def test_manifest_save_is_atomic(tmp_path: Path) -> None:
    manifest_path = tmp_path / "ingest_manifest.json"
    store = ManifestStore(manifest_path)
    store.update("https://example.com/a", status="downloaded")
    store.save()

    # The .tmp sibling must not linger after save; the real file must parse.
    assert not (manifest_path.with_suffix(".json.tmp")).exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["documents"]["https://example.com/a"]["status"] == "downloaded"


# --------------------------------------------------------------------------- #
# Health endpoint still works (regression guard after route-layer changes)
# --------------------------------------------------------------------------- #
def test_health_still_ok() -> None:
    from backend.main import app

    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
