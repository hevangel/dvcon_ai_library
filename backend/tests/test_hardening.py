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
from backend.services.scraper import (
    ManifestStore,
    _retry_delay_seconds,
    _search_form_document_urls,
    _validate_pdf_response,
)


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
    monkeypatch.setattr(indexer_mod, "crawl_archive", lambda *, limit, force, years=None: [seed_a, seed_b, seed_c])
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
# Document Library Pro AJAX-based discovery (serverSide table)
# --------------------------------------------------------------------------- #
def test_search_form_document_urls_uses_ajax_path(monkeypatch) -> None:
    """The live site renders results via admin-ajax.php keyed by table_id.

    Verify the new discovery path:
      1. POSTs the search form to obtain a fresh table_id bound to the filters.
      2. POSTs action=dlp_load_posts with that table_id and pages through rows.
      3. Parses /document/ links from the row HTML.
    """
    # First call: the search-form POST returns HTML containing the table id.
    # Subsequent calls: AJAX pages returning DataTables JSON.
    search_html = '<table id="dlp_deadbeef_1" class="posts-data-table"></table>'

    def row(title_slug: str) -> dict:
        return {
            "title": f'<a href="https://dvcon-proceedings.org/document/{title_slug}/">{title_slug}</a>',
            "tax:event_year": "2026",
        }

    ajax_pages = [
        SimpleNamespace(
            status_code=200,
            text=json.dumps(
                {
                    "draw": None,
                    "recordsTotal": 3,
                    "recordsFiltered": 3,
                    "data": [row("paper-one"), row("paper-two")],
                }
            ),
            raise_for_status=lambda: None,
        ),
        SimpleNamespace(
            status_code=200,
            text=json.dumps(
                {
                    "draw": None,
                    "recordsTotal": 3,
                    "recordsFiltered": 3,
                    "data": [row("paper-three")],
                }
            ),
            raise_for_status=lambda: None,
        ),
    ]
    call_log: list[tuple[str, str, dict]] = []

    def fake_request(client, method, url, **kwargs):
        data = kwargs.get("data", {})
        call_log.append((method, url, dict(data)))
        if url.endswith("document-search"):
            return SimpleNamespace(status_code=200, text=search_html, raise_for_status=lambda: None)
        if url.endswith("admin-ajax.php"):
            return ajax_pages.pop(0)
        raise AssertionError(f"unexpected url {url!r}")

    monkeypatch.setattr("backend.services.scraper._request_with_retries", fake_request)
    monkeypatch.setattr("backend.services.scraper.ADMIN_AJAX_URL", "https://x/admin-ajax.php")
    monkeypatch.setattr("backend.services.scraper.SEARCH_RESULTS_URL", "https://x/document-search")
    monkeypatch.setattr("backend.services.scraper.AJAX_PAGE_SIZE", 2)  # force pagination

    urls = _search_form_document_urls(client=object(), year_value="y2026", location_value="india")

    assert urls == [
        "https://dvcon-proceedings.org/document/paper-one",
        "https://dvcon-proceedings.org/document/paper-two",
        "https://dvcon-proceedings.org/document/paper-three",
    ]
    # First call posts the search form with the right filters.
    assert call_log[0] == (
        "POST",
        "https://x/document-search",
        {
            "ptp_filter_event_year": "y2026",
            "ptp_filter_document_type": "paper",
            "ptp_filter_event_location": "india",
            "textsearch": "",
        },
    )
    # Subsequent calls hit the AJAX endpoint with the table_id and DO NOT resend filters.
    assert all(entry[1] == "https://x/admin-ajax.php" for entry in call_log[1:])
    assert all(entry[2]["action"] == "dlp_load_posts" for entry in call_log[1:])
    assert all(entry[2]["table_id"] == "dlp_deadbeef_1" for entry in call_log[1:])
    # No tax_* or filter fields should leak into the AJAX payload.
    for entry in call_log[1:]:
        assert not any(k.startswith("tax_") or k.startswith("ptp_filter") for k in entry[2]), entry


def test_search_form_document_urls_falls_back_when_no_table_id(monkeypatch) -> None:
    """If the page shape changed and no table_id is present, fall back to the
    legacy server-rendered table parse so a partial site change doesn't wipe
    already-discovered URLs from the manifest.
    """
    legacy_html = """
    <table class="posts-data-table"><tbody>
      <tr><td><a href="/document/legacy-paper/">Legacy</a></td></tr>
    </tbody></table>
    """

    def fake_request(client, method, url, **kwargs):
        return SimpleNamespace(status_code=200, text=legacy_html, raise_for_status=lambda: None)

    monkeypatch.setattr("backend.services.scraper._request_with_retries", fake_request)
    monkeypatch.setattr("backend.services.scraper.SEARCH_RESULTS_URL", "https://x/document-search")

    urls = _search_form_document_urls(client=object(), year_value="y2026", location_value="india")
    assert urls == ["https://dvcon-proceedings.org/document/legacy-paper/"]


# --------------------------------------------------------------------------- #
# fetch_document_urls --years filter
# --------------------------------------------------------------------------- #
def test_fetch_document_urls_years_filter_skips_other_years(monkeypatch) -> None:
    """--years must skip year filters outside the requested set so an
    incremental ingest doesn't re-walk 2010-2024 it already has.
    """
    import backend.services.scraper as scraper_mod

    # The homepage exposes y2010..y2026; --years 2025,2026 must only walk those.
    monkeypatch.setattr(
        scraper_mod,
        "_homepage_filter_values",
        lambda client, name: ["y2010", "y2024", "y2025", "y2026"] if name == "ptp_filter_event_year" else ["india", "united-states"],
    )
    seen_combos: list[tuple[str, str]] = []

    def fake_search(client, year_value, location_value):
        seen_combos.append((year_value, location_value))
        return [f"https://dvcon-proceedings.org/document/{year_value}-{location_value}-1"]

    monkeypatch.setattr(scraper_mod, "_search_form_document_urls", fake_search)

    urls = scraper_mod.fetch_document_urls(years=[2025, 2026])

    # Only y2025/y2026 combos walked, each against both locations.
    assert sorted(seen_combos) == [
        ("y2025", "india"), ("y2025", "united-states"),
        ("y2026", "india"), ("y2026", "united-states"),
    ]
    assert len(urls) == 4


# --------------------------------------------------------------------------- #
# Health endpoint still works (regression guard after route-layer changes)
# --------------------------------------------------------------------------- #
def test_health_still_ok() -> None:
    from backend.main import app

    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
