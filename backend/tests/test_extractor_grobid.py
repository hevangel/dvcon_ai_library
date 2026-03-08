from pathlib import Path
from types import SimpleNamespace

import fitz

from backend.services.extractor import _rewrite_image_links, extract_pdf
from backend.services.grobid import GrobidResult
from backend.services.scraper import PaperSeed
from backend.services.tei_parser import ParsedAuthor, ParsedReference, ParsedTeiDocument


def _seed() -> PaperSeed:
    return PaperSeed(
        source_url="https://example.com/paper",
        pdf_url="https://example.com/paper.pdf",
        slug="sample-paper",
        title="Seed Title",
        authors_text="Seed Author",
        year=2025,
        location="us",
        document_type="Paper",
        conference_name="DVCon U.S. 2025",
        conference_slug="dvcon-us-2025",
        pdf_path="data/paper/2025/us/sample-paper.pdf",
    )


def _settings(repo_root: Path) -> SimpleNamespace:
    data_dir = repo_root / "data"
    return SimpleNamespace(
        repo_root=repo_root,
        markdown_dir=data_dir / "markdown",
        tei_dir=data_dir / "tei",
    )


def _write_pdf(pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Seed Title\nAbstract\nFallback abstract line one.")
    document.save(pdf_path)
    document.close()


def test_extract_pdf_uses_grobid_metadata_when_available(monkeypatch, tmp_path) -> None:
    repo_root = tmp_path / "repo"
    settings = _settings(repo_root)
    settings.markdown_dir.mkdir(parents=True, exist_ok=True)
    settings.tei_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = repo_root / _seed().pdf_path
    _write_pdf(pdf_path)

    grobid_document = ParsedTeiDocument(
        title="GROBID Title",
        abstract="GROBID abstract",
        authors=[ParsedAuthor(full_name="Seed Author", affiliations=["Example Semiconductor"])],
        affiliations=["Example Semiconductor"],
        references=[
            ParsedReference(
                citation_text="Alice Example. Better Reference.",
                normalized_title="Better Reference",
                doi="10.1000/better",
            )
        ],
    )
    grobid_result = GrobidResult(tei_xml="<TEI/>", document=grobid_document)

    monkeypatch.setattr("backend.services.extractor.get_settings", lambda: settings)
    monkeypatch.setattr(
        "backend.services.extractor.pymupdf4llm.to_markdown",
        lambda *args, **kwargs: "# Seed Title\n\n## Abstract\nFallback abstract",
    )
    monkeypatch.setattr("backend.services.extractor.process_fulltext_document", lambda pdf: grobid_result)

    extracted = extract_pdf(_seed())

    assert extracted.title == "GROBID Title"
    assert extracted.authors_text == "Seed Author"
    assert extracted.authors[0].affiliations == ["Example Semiconductor"]
    assert extracted.abstract == "GROBID abstract"
    assert extracted.affiliations == ["Example Semiconductor"]
    assert extracted.tei_path == "data/tei/2025/us/sample-paper.tei.xml"
    assert extracted.references[0].doi == "10.1000/better"


def test_extract_pdf_falls_back_when_grobid_is_unavailable(monkeypatch, tmp_path) -> None:
    repo_root = tmp_path / "repo"
    settings = _settings(repo_root)
    settings.markdown_dir.mkdir(parents=True, exist_ok=True)
    settings.tei_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = repo_root / _seed().pdf_path
    _write_pdf(pdf_path)

    markdown = """
    # Seed Title

    ## Abstract
    Fallback abstract line one.
    Fallback abstract line two.

    ## References
    [1] Example Reference Entry.
    """

    monkeypatch.setattr("backend.services.extractor.get_settings", lambda: settings)
    monkeypatch.setattr("backend.services.extractor.pymupdf4llm.to_markdown", lambda *args, **kwargs: markdown)
    monkeypatch.setattr("backend.services.extractor.process_fulltext_document", lambda pdf: None)

    extracted = extract_pdf(_seed())

    assert extracted.title == "Seed Title"
    assert extracted.authors_text == "Seed Author"
    assert "fallback abstract line one" in extracted.abstract.lower()
    assert extracted.tei_path is None
    assert extracted.references[0].citation_text == "Example Reference Entry."


def test_rewrite_image_links_uses_markdown_relative_paths(tmp_path) -> None:
    markdown_dir = tmp_path / "data" / "markdown" / "2025" / "us"
    image_dir = markdown_dir / "images" / "sample-paper"
    image_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / "sample-paper.pdf-0-0.png").write_bytes(b"png")

    rewritten = _rewrite_image_links(
        "![](sample-paper.pdf-0-0.png)",
        image_dir=image_dir,
        markdown_dir=markdown_dir,
    )

    assert rewritten == "![](images/sample-paper/sample-paper.pdf-0-0.png)"
