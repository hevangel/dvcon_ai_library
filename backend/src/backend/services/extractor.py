from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import fitz
import pymupdf4llm

from backend.core.config import get_settings
from backend.services.grobid import process_fulltext_document
from backend.services.scraper import PaperSeed
from backend.services.tei_parser import ParsedAuthor, ParsedReference


ABSTRACT_PATTERN = re.compile(
    r"(?:^|\n)(?:#+\s*)?abstract\b[:\s]*(.+?)(?=\n(?:#+\s*[A-Z]|\n[A-Z][^\n]{0,80}\n|\Z))",
    re.IGNORECASE | re.DOTALL,
)
REFERENCE_SPLIT_PATTERN = re.compile(r"(?:^\s*\[\d+\]|\n\s*\[\d+\]|\n\s*\d+\.\s+)", re.MULTILINE)
IMAGE_PATTERN = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")
NAME_TOKEN_PATTERN = re.compile(r"[A-Za-z]+")
ORGANIZATION_KEYWORDS = (
    "inc",
    "corp",
    "corporation",
    "ltd",
    "llc",
    "gmbh",
    "technologies",
    "technology",
    "systems",
    "university",
    "institute",
    "labs",
    "laboratories",
    "semiconductor",
    "cadence",
    "synopsys",
    "siemens",
    "intel",
    "nvidia",
    "qualcomm",
    "google",
    "microsoft",
    "samsung",
    "apple",
    "arm",
    "amd",
)


@dataclass(slots=True)
class ExtractedPaper:
    title: str
    authors_text: str
    authors: list[ParsedAuthor]
    markdown_path: str
    tei_path: str | None
    abstract: str
    affiliations: list[str]
    references: list[ParsedReference]
    metadata_json: str


def _front_matter_text(document: fitz.Document, pages: int = 2) -> str:
    page_text: list[str] = []
    for index in range(min(pages, document.page_count)):
        page_text.append(document.load_page(index).get_text("text"))
    return "\n".join(page_text)


def _extract_abstract(markdown_text: str, front_matter_text: str) -> str:
    lines = markdown_text.splitlines()
    abstract_lines: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if collecting and abstract_lines:
                break
            continue

        if stripped.lstrip("#").strip().lower() == "abstract":
            collecting = True
            continue

        if collecting and stripped.startswith("#"):
            break

        if collecting:
            abstract_lines.append(stripped)

    if abstract_lines:
        return " ".join(abstract_lines)

    markdown_match = ABSTRACT_PATTERN.search(markdown_text)
    if markdown_match:
        return " ".join(markdown_match.group(1).split())

    lower_text = front_matter_text.lower()
    abstract_index = lower_text.find("abstract")
    if abstract_index == -1:
        return ""

    snippet = front_matter_text[abstract_index : abstract_index + 2200]
    lines = [line.strip() for line in snippet.splitlines() if line.strip()]
    if not lines:
        return ""

    abstract_lines = lines[1:8] if lines[0].lower().startswith("abstract") else lines[:7]
    return " ".join(abstract_lines).strip()


def _extract_affiliations(front_matter_text: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in front_matter_text.splitlines():
        line = " ".join(raw_line.split()).strip(" ,;")
        if len(line) < 4:
            continue

        lowered = line.lower()
        if any(keyword in lowered for keyword in ORGANIZATION_KEYWORDS):
            candidates.append(line)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    return deduped[:20]


def _extract_references(markdown_text: str) -> list[str]:
    lines = markdown_text.splitlines()
    reference_lines: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        normalized = stripped.lstrip("#").strip().lower()
        if normalized == "references":
            collecting = True
            continue

        if collecting and stripped.startswith("#"):
            break

        if collecting:
            reference_lines.append(stripped)

    if not reference_lines:
        return []

    reference_text = "\n".join(reference_lines)
    parts = [part.strip() for part in REFERENCE_SPLIT_PATTERN.split(reference_text) if part.strip()]

    references: list[str] = []
    for part in parts:
        line = " ".join(part.split())
        if len(line) >= 20:
            references.append(line)

    return references[:100]


def _parse_seed_authors(authors_text: str) -> list[ParsedAuthor]:
    normalized = authors_text.replace(" and ", ",")
    return [
        ParsedAuthor(full_name=part.strip())
        for part in normalized.split(",")
        if part.strip()
    ]


def _authors_text(authors: list[ParsedAuthor], fallback: str) -> str:
    author_names = [author.full_name for author in authors if author.full_name]
    return ", ".join(author_names) if author_names else fallback


def _reference_objects(references: list[str]) -> list[ParsedReference]:
    return [ParsedReference(citation_text=reference) for reference in references]


def _reference_payloads(references: list[ParsedReference]) -> list[dict[str, object | None]]:
    return [
        {
            "citation_text": reference.citation_text,
            "normalized_title": reference.normalized_title,
            "authors_text": reference.authors_text,
            "journal_or_book": reference.journal_or_book,
            "publication_year": reference.publication_year,
            "doi": reference.doi,
        }
        for reference in references
    ]


def _dedupe_text_values(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def _name_tokens(value: str) -> list[str]:
    return [token.casefold() for token in NAME_TOKEN_PATTERN.findall(value)]


def _given_names_compatible(seed_tokens: list[str], grobid_tokens: list[str]) -> bool:
    if not seed_tokens or not grobid_tokens:
        return True

    if set(seed_tokens) & set(grobid_tokens):
        return True

    return any(
        seed_token[0] == grobid_token[0] and (len(seed_token) == 1 or len(grobid_token) == 1)
        for seed_token in seed_tokens
        for grobid_token in grobid_tokens
    )


def _author_names_compatible(seed_name: str, grobid_name: str) -> bool:
    seed_tokens = _name_tokens(seed_name)
    grobid_tokens = _name_tokens(grobid_name)
    if not seed_tokens or not grobid_tokens:
        return False

    if seed_tokens == grobid_tokens:
        return True

    if len(seed_tokens) == 1 or len(grobid_tokens) == 1:
        return seed_tokens[-1] == grobid_tokens[-1]

    seed_surname = seed_tokens[-1]
    grobid_surname = grobid_tokens[-1]
    if seed_surname != grobid_surname:
        return False

    return _given_names_compatible(seed_tokens[:-1], grobid_tokens[:-1])


def _merge_seed_and_grobid_authors(
    seed_authors: list[ParsedAuthor], grobid_authors: list[ParsedAuthor]
) -> list[ParsedAuthor] | None:
    if not grobid_authors:
        return None

    if not seed_authors:
        return [
            ParsedAuthor(
                full_name=author.full_name.strip(),
                given_name=author.given_name,
                surname=author.surname,
                affiliations=_dedupe_text_values(author.affiliations),
                email=author.email,
            )
            for author in grobid_authors
            if author.full_name.strip()
        ]

    if len(seed_authors) != len(grobid_authors):
        return None

    merged_authors: list[ParsedAuthor] = []
    for seed_author, grobid_author in zip(seed_authors, grobid_authors, strict=False):
        seed_name = seed_author.full_name.strip()
        grobid_name = grobid_author.full_name.strip()
        if not seed_name or not grobid_name:
            return None

        if not _author_names_compatible(seed_name, grobid_name):
            return None

        merged_authors.append(
            ParsedAuthor(
                full_name=seed_name,
                given_name=grobid_author.given_name or seed_author.given_name,
                surname=grobid_author.surname or seed_author.surname,
                affiliations=_dedupe_text_values([*seed_author.affiliations, *grobid_author.affiliations]),
                email=grobid_author.email or seed_author.email,
            )
        )

    return merged_authors


def _rewrite_image_links(markdown_text: str, image_dir: Path, markdown_dir: Path) -> str:
    def replacer(match: re.Match[str]) -> str:
        original_path = match.group("path").strip()
        filename = Path(original_path).name
        absolute_path = image_dir / filename
        if not absolute_path.exists():
            return match.group(0)

        relative_path = absolute_path.relative_to(markdown_dir).as_posix()
        return f"![{match.group('alt')}]({relative_path})"

    return IMAGE_PATTERN.sub(replacer, markdown_text)


def _markdown_image_dir(seed: PaperSeed, settings) -> Path:
    return settings.markdown_dir / str(seed.year) / seed.location / "images" / seed.slug


def _tei_output_path(seed: PaperSeed, settings) -> Path:
    return settings.tei_dir / str(seed.year) / seed.location / f"{seed.slug}.tei.xml"


def extract_pdf(seed: PaperSeed) -> ExtractedPaper:
    settings = get_settings()
    pdf_path = settings.repo_root / seed.pdf_path
    markdown_relative_path = Path("data") / "markdown" / str(seed.year) / seed.location / f"{seed.slug}.md"
    markdown_path = settings.repo_root / markdown_relative_path
    image_dir = _markdown_image_dir(seed, settings)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as document:
        front_matter_text = _front_matter_text(document)
        markdown_text = pymupdf4llm.to_markdown(
            document,
            write_images=True,
            image_path=image_dir.as_posix(),
            page_chunks=False,
            show_progress=False,
        )

    rewritten_markdown = _rewrite_image_links(markdown_text, image_dir, markdown_path.parent)
    markdown_path.write_text(rewritten_markdown, encoding="utf-8")

    heuristic_abstract = _extract_abstract(rewritten_markdown, front_matter_text)
    heuristic_affiliations = _extract_affiliations(front_matter_text)
    heuristic_references = _reference_objects(_extract_references(rewritten_markdown))
    seed_authors = _parse_seed_authors(seed.authors_text)

    grobid_result = process_fulltext_document(pdf_path)
    tei_relative_path: str | None = None
    title = seed.title
    authors = seed_authors
    authors_text = seed.authors_text
    abstract = heuristic_abstract
    affiliations = heuristic_affiliations
    references = heuristic_references
    metadata_source = "heuristic"

    if grobid_result is not None:
        tei_path = _tei_output_path(seed, settings)
        tei_path.parent.mkdir(parents=True, exist_ok=True)
        tei_path.write_text(grobid_result.tei_xml, encoding="utf-8")
        tei_relative_path = tei_path.relative_to(settings.repo_root).as_posix()

        document = grobid_result.document
        if document.title:
            title = document.title
        if document.authors:
            merged_authors = _merge_seed_and_grobid_authors(seed_authors, document.authors)
            if merged_authors is not None:
                authors = merged_authors
                authors_text = seed.authors_text.strip() or _authors_text(merged_authors, seed.authors_text)
        if document.abstract:
            abstract = document.abstract
        if document.affiliations:
            affiliations = document.affiliations
        if document.references:
            references = document.references
        metadata_source = "grobid_hybrid"

    metadata_json = json.dumps(
        {
            "title": title,
            "authors_text": authors_text,
            "year": seed.year,
            "location": seed.location,
            "conference_name": seed.conference_name,
            "metadata_source": metadata_source,
            "tei_path": tei_relative_path,
            "authors": [
                {
                    "full_name": author.full_name,
                    "given_name": author.given_name,
                    "surname": author.surname,
                    "affiliations": author.affiliations,
                    "email": author.email,
                }
                for author in authors
            ],
            "affiliations": affiliations,
            "reference_count": len(references),
            "references": _reference_payloads(references),
        },
        indent=2,
    )

    return ExtractedPaper(
        title=title,
        authors_text=authors_text,
        authors=authors,
        markdown_path=markdown_relative_path.as_posix(),
        tei_path=tei_relative_path,
        abstract=abstract,
        affiliations=affiliations,
        references=references,
        metadata_json=metadata_json,
    )
