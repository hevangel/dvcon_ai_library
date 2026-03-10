from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.db.models import Paper
from backend.main import app
from backend.services.chat import _context_hits, answer_question
from backend.services.embeddings import resolve_embedding_device
from backend.services.extractor import _extract_abstract, _extract_affiliations, _extract_references
from backend.services.indexer import SearchHit
from backend.services.indexer import _chunk_markdown, _dedupe_authors
from backend.services.scraper import _detail_page_has_downloadable_pdf, _parse_detail_text_map, fetch_document_urls
from backend.services.tei_parser import ParsedAuthor


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_forwards_previous_response_id(monkeypatch) -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_answer_question(**kwargs: object) -> SimpleNamespace:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            answer="Scoped reply.",
            citations=[{"index": "1", "paper_id": "7", "title": "Example Paper", "year": "2025"}],
            scope_paper_ids=[7],
            response_id="resp_123",
        )

    monkeypatch.setattr("backend.api.routes.chat.answer_question", fake_answer_question)

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={
            "selected_paper_ids": [7],
            "messages": [{"role": "user", "content": "Summarize this paper."}],
            "previous_response_id": "resp_prev",
        },
    )

    assert response.status_code == 200
    assert captured_kwargs["selected_paper_ids"] == [7]
    assert captured_kwargs["previous_response_id"] == "resp_prev"
    assert response.json() == {
        "answer": "Scoped reply.",
        "citations": [{"index": "1", "paper_id": "7", "title": "Example Paper", "year": "2025"}],
        "scope_paper_ids": [7],
        "response_id": "resp_123",
    }


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


def test_detail_page_has_downloadable_pdf_accepts_missing_format_for_direct_pdf_link() -> None:
    assert _detail_page_has_downloadable_pdf(
        "Paper",
        "",
        "https://dvcon-proceedings.org/wp-content/uploads/example-paper.pdf",
    )


def test_detail_page_has_downloadable_pdf_rejects_missing_format_for_non_pdf_link() -> None:
    assert not _detail_page_has_downloadable_pdf(
        "Paper",
        "",
        "https://ieeexplore.ieee.org/document/10461371/",
    )


def test_fetch_document_urls_uses_homepage_archive_filters(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, text: str, status_code: int = 200) -> None:
            self.text = text
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str) -> FakeResponse:
            responses = {
                "https://dvcon-proceedings.org/": FakeResponse(
                    """
                    <html>
                        <body>
                            <select name="ptp_filter_event_year">
                                <option value="">Year</option>
                                <option value="y2024">2024</option>
                            </select>
                            <select name="ptp_filter_event_location">
                                <option value="">Location</option>
                                <option value="united-states">United States</option>
                            </select>
                        </body>
                    </html>
                    """
                ),
            }
            response = responses.get(url)
            if response is None:
                raise AssertionError(f"Unexpected URL fetched: {url}")
            return response

        def post(self, url: str, data: dict[str, str]) -> FakeResponse:
            if url != "https://dvcon-proceedings.org/document-search":
                raise AssertionError(f"Unexpected URL posted: {url}")
            if data != {
                "ptp_filter_event_year": "y2024",
                "ptp_filter_document_type": "paper",
                "ptp_filter_event_location": "united-states",
                "textsearch": "",
            }:
                raise AssertionError(f"Unexpected form payload: {data}")

            return FakeResponse(
                """
                <html>
                    <body>
                        <table class="posts-data-table">
                            <tbody>
                                <tr><td><a href="https://dvcon-proceedings.org/document/legacy-paper/">Legacy</a></td></tr>
                                <tr><td><a href="https://dvcon-proceedings.org/document/recent-us-paper/">Recent US</a></td></tr>
                                <tr><td><a href="https://dvcon-proceedings.org/document/recent-us-paper/">Recent US Duplicate</a></td></tr>
                            </tbody>
                        </table>
                    </body>
                </html>
                """
            )

    monkeypatch.setattr("backend.services.scraper._http_client", lambda: FakeClient())

    urls = fetch_document_urls()

    assert urls == [
        "https://dvcon-proceedings.org/document/legacy-paper/",
        "https://dvcon-proceedings.org/document/recent-us-paper/",
    ]


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
            return SimpleNamespace(output_text="Grounded summary.", id="resp_grounded")

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
    assert answer.response_id == "resp_grounded"
    assert "[1]" in str(captured_request["input"])


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


def test_answer_question_uses_previous_response_id_for_continuation(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs: object):
            captured_request.update(kwargs)
            return SimpleNamespace(output_text="Continuation ready.", id="resp_next")

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            self.responses = FakeResponses()

    paper = Paper(
        id=23,
        source_url="https://example.com/paper-23",
        pdf_url="https://example.com/paper-23.pdf",
        slug="paper-23",
        title="Continuation Paper",
        year=2025,
        location="United States",
        pdf_path="data/paper/2025/united states/paper-23.pdf",
    )
    hits = [SearchHit(paper=paper, score=1.0, snippet="Continuation excerpt.")]

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
        messages=[
            {"role": "user", "content": "Summarize this paper."},
            {"role": "assistant", "content": "Initial reply."},
            {"role": "user", "content": "Go deeper on the methodology."},
        ],
        selected_paper_ids=[paper.id],
        previous_response_id="resp_prev",
    )

    assert answer.answer == "Continuation ready."
    assert answer.response_id == "resp_next"
    assert captured_request["previous_response_id"] == "resp_prev"
    assert "Conversation so far:" not in str(captured_request["input"])
    assert "Current user question:" in str(captured_request["input"])
    assert "Go deeper on the methodology." in str(captured_request["input"])
    assert "Selected paper scope:" in str(captured_request["input"])
    assert "[1] Continuation Paper (2025, United States)" in str(captured_request["input"])


def test_answer_question_uses_full_selected_paper_context_when_it_fits(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs: object):
            captured_request.update(kwargs)
            return SimpleNamespace(output_text="Full paper comparison ready.")

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            self.responses = FakeResponses()

    paper = Paper(
        id=31,
        source_url="https://example.com/paper-31",
        pdf_url="https://example.com/paper-31.pdf",
        slug="paper-31",
        title="Full Context Paper",
        year=2025,
        location="United States",
        abstract="A compact abstract.",
        pdf_path="data/paper/2025/united states/paper-31.pdf",
    )
    hits = [SearchHit(paper=paper, score=1.0, snippet="Fallback snippet.")]
    chunks = [
        SimpleNamespace(chunk_index=0, heading="Introduction", text="Intro text.", chroma_id="chunk-0"),
        SimpleNamespace(chunk_index=1, heading="Results", text="Results text.", chroma_id="chunk-1"),
    ]

    monkeypatch.setattr(
        "backend.services.chat.get_settings",
        lambda: SimpleNamespace(
            chat_is_configured=True,
            openai_api_key="test-key",
            openai_base_url="https://example.invalid/v1",
            openai_chat_model="gpt-5-mini",
            openai_chat_model_context_window=4096,
            chat_context_output_reserve_tokens=256,
            chunk_overlap=200,
        ),
    )
    monkeypatch.setattr("backend.services.chat._context_hits", lambda question, selected_paper_ids: hits)
    monkeypatch.setattr("backend.services.chat.get_paper_chunks", lambda paper_id: chunks)
    monkeypatch.setattr("backend.services.chat.OpenAI", FakeOpenAI)

    answer = answer_question(
        messages=[{"role": "user", "content": "Compare the selected paper to itself."}],
        selected_paper_ids=[paper.id],
    )

    assert answer.answer == "Full paper comparison ready."
    assert "Full selected paper content:" in str(captured_request["input"])
    assert "Introduction:" in str(captured_request["input"])
    assert "Results:" in str(captured_request["input"])


def test_answer_question_falls_back_to_selected_sections_when_full_text_does_not_fit(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs: object):
            captured_request.update(kwargs)
            return SimpleNamespace(output_text="Section-only comparison ready.")

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            self.responses = FakeResponses()

    paper = Paper(
        id=32,
        source_url="https://example.com/paper-32",
        pdf_url="https://example.com/paper-32.pdf",
        slug="paper-32",
        title="Large Context Paper",
        year=2025,
        location="India",
        abstract="A compact abstract.",
        pdf_path="data/paper/2025/india/paper-32.pdf",
    )
    hits = [SearchHit(paper=paper, score=1.0, snippet="Fallback snippet.")]
    large_chunk = "Large section text. " * 400
    chunks = [
        SimpleNamespace(chunk_index=0, heading="Introduction", text=large_chunk, chroma_id="chunk-0"),
        SimpleNamespace(chunk_index=1, heading="Results", text=large_chunk, chroma_id="chunk-1"),
    ]

    monkeypatch.setattr(
        "backend.services.chat.get_settings",
        lambda: SimpleNamespace(
            chat_is_configured=True,
            openai_api_key="test-key",
            openai_base_url="https://example.invalid/v1",
            openai_chat_model="gpt-5-mini",
            openai_chat_model_context_window=512,
            chat_context_output_reserve_tokens=256,
            chunk_overlap=200,
        ),
    )
    monkeypatch.setattr("backend.services.chat._context_hits", lambda question, selected_paper_ids: hits)
    monkeypatch.setattr("backend.services.chat.get_paper_chunks", lambda paper_id: chunks)
    monkeypatch.setattr("backend.services.chat.OpenAI", FakeOpenAI)

    answer = answer_question(
        messages=[{"role": "user", "content": "Compare the selected paper to itself."}],
        selected_paper_ids=[paper.id],
    )

    assert answer.answer == "Section-only comparison ready."
    assert "Selected paper sections:" in str(captured_request["input"])
    assert "Full selected paper content:" not in str(captured_request["input"])
