from fastapi.testclient import TestClient

from backend.main import app
from backend.services.embeddings import resolve_embedding_device
from backend.services.extractor import _extract_abstract, _extract_affiliations, _extract_references
from backend.services.indexer import _chunk_markdown, _dedupe_authors
from backend.services.scraper import _parse_detail_text_map
from backend.services.tei_parser import ParsedAuthor


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_detail_text_map_extracts_expected_fields() -> None:
    html = """
    <html>
        <body>
            <h1>Example Paper</h1>
            <div>Author(s):</div>
            <div>Alice Example, Bob Example</div>
            <div>Location:</div>
            <div>Europe</div>
            <div>Year:</div>
            <div>2025</div>
            <div>Type:</div>
            <div>Paper</div>
            <div>Format:</div>
            <div>pdf</div>
        </body>
    </html>
    """

    from bs4 import BeautifulSoup

    parsed = _parse_detail_text_map(BeautifulSoup(html, "html.parser"))
    assert parsed["authors"] == "Alice Example, Bob Example"
    assert parsed["location"] == "Europe"
    assert parsed["year"] == "2025"
    assert parsed["type"] == "Paper"
    assert parsed["format"] == "pdf"


def test_extractor_helpers_parse_metadata_sections() -> None:
    markdown = """
    # Title

    ## Abstract
    This paper introduces a verification acceleration workflow.
    It reduces debug turnaround while preserving traceability.

    ## Method
    Details about the methodology.

    ## References
    [1] A. Author, Example Reference One.
    [2] B. Author, Example Reference Two.
    """
    front_matter = """
    Alice Example
    Example Semiconductor Inc.
    Bob Example
    Verification Labs GmbH
    """

    abstract = _extract_abstract(markdown, front_matter)
    affiliations = _extract_affiliations(front_matter)
    references = _extract_references(markdown)

    assert "verification acceleration workflow" in abstract.lower()
    assert "Example Semiconductor Inc." in affiliations
    assert len(references) == 2


def test_chunking_and_device_resolution_are_stable(monkeypatch) -> None:
    markdown = """
    # Introduction
    This is a short introduction.

    # Results
    This is a longer results section with enough text to create at least one chunk.
    """

    chunks = _chunk_markdown(markdown)
    monkeypatch.setattr("backend.services.embeddings.torch.cuda.is_available", lambda: False)
    device = resolve_embedding_device()

    assert chunks
    assert chunks[0]["heading"] == "Introduction"
    assert device == "cpu"


def test_dedupe_authors_merges_duplicate_grobid_entries() -> None:
    authors = [
        ParsedAuthor(full_name="Alice Example", affiliations=["Company A"]),
        ParsedAuthor(full_name="Bob Example", affiliations=["Company B"]),
        ParsedAuthor(full_name="alice example", affiliations=["Company C"], email="alice@example.com"),
    ]

    deduped = _dedupe_authors(authors)

    assert [author.full_name for author in deduped] == ["Alice Example", "Bob Example"]
    assert deduped[0].affiliations == ["Company A", "Company C"]
    assert deduped[0].email == "alice@example.com"
