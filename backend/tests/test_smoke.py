from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.db.models import Paper
from backend.main import app
from backend.services.chat import _context_hits, answer_question
from backend.services.embeddings import resolve_embedding_device
from backend.services.extractor import _extract_abstract, _extract_affiliations, _extract_references
from backend.services.indexer import SearchHit
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


def test_answer_question_omits_temperature_for_chat_model(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs: object):
            captured_request.update(kwargs)
            return SimpleNamespace(output_text="Grounded summary.")

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            captured_request["api_key"] = api_key
            captured_request["base_url"] = base_url
            self.responses = FakeResponses()

    paper = Paper(
        id=7,
        source_url="https://example.com/paper",
        pdf_url="https://example.com/paper.pdf",
        slug="example-paper",
        title="Example Paper",
        year=2025,
        location="United States",
        pdf_path="data/paper/2025/united states/example-paper.pdf",
    )
    hits = [SearchHit(paper=paper, score=0.98, snippet="This is a grounded excerpt.")]

    monkeypatch.setattr(
        "backend.services.chat.get_settings",
        lambda: SimpleNamespace(
            chat_is_configured=True,
            openai_api_key="test-key",
            openai_base_url="https://example.invalid/v1",
            openai_chat_model="gpt-5-mini",
        ),
    )
    monkeypatch.setattr("backend.services.chat._context_hits", lambda question, selected_paper_ids: hits)
    monkeypatch.setattr("backend.services.chat.OpenAI", FakeOpenAI)

    answer = answer_question(
        messages=[{"role": "user", "content": "Summarize this paper."}],
        selected_paper_ids=[paper.id],
    )

    assert answer.answer == "Grounded summary."
    assert answer.scope_paper_ids == [paper.id]
    assert captured_request["api_key"] == "test-key"
    assert captured_request["base_url"] == "https://example.invalid/v1"
    assert captured_request["model"] == "gpt-5-mini"
    assert "temperature" not in captured_request
    assert "[Source 1]" in str(captured_request["input"])


def test_context_hits_preserves_selected_scope_for_generic_compare_query(monkeypatch) -> None:
    paper_one = Paper(
        id=11,
        source_url="https://example.com/paper-1",
        pdf_url="https://example.com/paper-1.pdf",
        slug="paper-1",
        title="Paper One",
        year=2024,
        location="United States",
        abstract="Paper one abstract.",
        pdf_path="data/paper/2024/united states/paper-1.pdf",
    )
    paper_two = Paper(
        id=12,
        source_url="https://example.com/paper-2",
        pdf_url="https://example.com/paper-2.pdf",
        slug="paper-2",
        title="Paper Two",
        year=2025,
        location="India",
        abstract="Paper two abstract.",
        pdf_path="data/paper/2025/india/paper-2.pdf",
    )
    paper_map = {
        paper_one.id: paper_one,
        paper_two.id: paper_two,
    }

    monkeypatch.setattr("backend.services.chat.hybrid_search", lambda *args, **kwargs: [])
    monkeypatch.setattr("backend.services.chat.get_paper", lambda paper_id: paper_map.get(paper_id))
    monkeypatch.setattr("backend.services.chat.get_paper_chunks", lambda paper_id: [])

    hits = _context_hits("Compare the two papers.", [paper_one.id, paper_two.id])

    assert [hit.paper.id for hit in hits] == [paper_one.id, paper_two.id]
    assert [hit.paper.title for hit in hits] == ["Paper One", "Paper Two"]


def test_answer_question_includes_selected_scope_in_prompt(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs: object):
            captured_request.update(kwargs)
            return SimpleNamespace(output_text="Comparison ready.")

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            self.responses = FakeResponses()

    paper_one = Paper(
        id=21,
        source_url="https://example.com/paper-21",
        pdf_url="https://example.com/paper-21.pdf",
        slug="paper-21",
        title="Selected Paper One",
        year=2024,
        location="United States",
        pdf_path="data/paper/2024/united states/paper-21.pdf",
    )
    paper_two = Paper(
        id=22,
        source_url="https://example.com/paper-22",
        pdf_url="https://example.com/paper-22.pdf",
        slug="paper-22",
        title="Selected Paper Two",
        year=2025,
        location="India",
        pdf_path="data/paper/2025/india/paper-22.pdf",
    )
    hits = [
        SearchHit(paper=paper_one, score=1.0, snippet="First selected paper excerpt."),
        SearchHit(paper=paper_two, score=1.0, snippet="Second selected paper excerpt."),
    ]

    monkeypatch.setattr(
        "backend.services.chat.get_settings",
        lambda: SimpleNamespace(
            chat_is_configured=True,
            openai_api_key="test-key",
            openai_base_url="https://example.invalid/v1",
            openai_chat_model="gpt-5-mini",
        ),
    )
    monkeypatch.setattr("backend.services.chat._context_hits", lambda question, selected_paper_ids: hits)
    monkeypatch.setattr("backend.services.chat.OpenAI", FakeOpenAI)

    answer = answer_question(
        messages=[{"role": "user", "content": "Compare the two papers."}],
        selected_paper_ids=[paper_one.id, paper_two.id],
    )

    assert answer.answer == "Comparison ready."
    assert answer.scope_paper_ids == [paper_one.id, paper_two.id]
    assert "Selected paper scope:" in str(captured_request["input"])
    assert "Selected Paper One (2024, United States)" in str(captured_request["input"])
    assert "Selected Paper Two (2025, India)" in str(captured_request["input"])
    assert "the two papers" in str(captured_request["input"])
