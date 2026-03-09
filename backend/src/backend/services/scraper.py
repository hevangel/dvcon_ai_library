from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from slugify import slugify

from backend.core.config import get_settings


DVCON_BASE_URL = "https://dvcon-proceedings.org/"
ARCHIVE_HOME_URL = DVCON_BASE_URL


@dataclass(slots=True)
class PaperSeed:
    source_url: str
    pdf_url: str
    slug: str
    title: str
    authors_text: str
    year: int
    location: str
    document_type: str
    conference_name: str
    conference_slug: str
    pdf_path: str


class ManifestStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._load()

    def _normalize_pdf_path(self, pdf_path: str) -> str:
        if not pdf_path.startswith("paper/"):
            return pdf_path

        settings = get_settings()
        paper_root = settings.paper_dir.relative_to(settings.repo_root).as_posix()
        return f"{paper_root}/{pdf_path.removeprefix('paper/')}"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"documents": {}}

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"documents": {}}

        documents = data.setdefault("documents", {})
        for record in documents.values():
            pdf_path = record.get("pdf_path")
            if isinstance(pdf_path, str):
                record["pdf_path"] = self._normalize_pdf_path(pdf_path)

            seed = record.get("seed")
            if isinstance(seed, dict):
                seed_pdf_path = seed.get("pdf_path")
                if isinstance(seed_pdf_path, str):
                    seed["pdf_path"] = self._normalize_pdf_path(seed_pdf_path)

        return data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def get(self, source_url: str) -> dict[str, Any]:
        return self.data.setdefault("documents", {}).setdefault(source_url, {})

    def update(self, source_url: str, **fields: Any) -> None:
        record = self.get(source_url)
        record.update(fields)


def _http_client() -> httpx.Client:
    return httpx.Client(
        timeout=60.0,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            )
        },
    )


def _archive_document_urls(client: httpx.Client, archive_url: str) -> list[str]:
    document_urls: list[str] = []
    seen_urls: set[str] = set()

    for page in range(1, 100):
        page_url = archive_url if page == 1 else urljoin(archive_url.rstrip("/") + "/", f"page/{page}/")
        response = client.get(page_url)
        if response.status_code == 404:
            break

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page_document_urls = [
            urljoin(DVCON_BASE_URL, anchor.get("href", ""))
            for anchor in soup.find_all("a", href=True)
            if "/document/" in anchor.get("href", "")
        ]

        new_urls = [url for url in page_document_urls if url not in seen_urls]
        if not new_urls:
            break

        document_urls.extend(new_urls)
        seen_urls.update(new_urls)

    return document_urls


def _homepage_archive_urls(client: httpx.Client) -> list[str]:
    response = client.get(ARCHIVE_HOME_URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    archive_urls: list[str] = []

    filter_specs = (
        ("select", {"name": "ptp_filter_event_year"}, "event_year"),
        ("select", {"name": "ptp_filter_event_location"}, "event_location"),
    )
    for tag_name, attrs, path_prefix in filter_specs:
        select = soup.find(tag_name, attrs=attrs)
        if select is None:
            continue

        for option in select.find_all("option"):
            option_value = option.get("value", "").strip()
            if not option_value:
                continue
            archive_url = urljoin(DVCON_BASE_URL, f"{path_prefix}/{option_value}/")
            if archive_url not in archive_urls:
                archive_urls.append(archive_url)

    return archive_urls


def fetch_document_urls(limit: int | None = None) -> list[str]:
    urls: list[str] = []
    seen_urls: set[str] = set()

    with _http_client() as client:
        for archive_url in _homepage_archive_urls(client):
            for page_url in _archive_document_urls(client, archive_url):
                if page_url in seen_urls:
                    continue
                seen_urls.add(page_url)
                urls.append(page_url)
                if limit is not None and len(urls) >= limit:
                    return urls[:limit]

    return urls


def _parse_detail_text_map(soup: BeautifulSoup) -> dict[str, str]:
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    data: dict[str, str] = {}
    labels = {"Author(s)": "authors", "Location": "location", "Year": "year", "Type": "type", "Format": "format"}

    for index, line in enumerate(lines[:-1]):
        key = line.rstrip(":")
        field = labels.get(key)
        if field:
            data[field] = lines[index + 1]

    return data


def parse_document_detail(source_url: str) -> PaperSeed | None:
    settings = get_settings()

    with _http_client() as client:
        response = client.get(source_url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    heading = soup.find(["h1", "title"])
    detail_map = _parse_detail_text_map(soup)

    download_anchor = soup.find("a", string=lambda value: isinstance(value, str) and "Download" in value)
    if not heading or not download_anchor:
        return None

    document_type = detail_map.get("type", "").strip()
    file_format = detail_map.get("format", "").strip().lower()
    if document_type.lower() != "paper" or file_format != "pdf":
        return None

    try:
        year = int(detail_map.get("year", "0"))
    except ValueError:
        return None

    location = detail_map.get("location", "unknown").strip().lower()
    title = heading.get_text(strip=True).replace("– DVCon Proceedings Archive", "").strip()
    slug = slugify(source_url.rstrip("/").split("/")[-1])
    paper_root = settings.paper_dir.relative_to(settings.repo_root)
    pdf_relative_path = paper_root / str(year) / location / f"{slug}.pdf"
    conference_name = f"DVCon {location.title()} {year}"

    pdf_url = urljoin(DVCON_BASE_URL, download_anchor.get("href", ""))
    if not pdf_url:
        return None

    return PaperSeed(
        source_url=source_url,
        pdf_url=pdf_url,
        slug=slug,
        title=title,
        authors_text=detail_map.get("authors", ""),
        year=year,
        location=location,
        document_type=document_type,
        conference_name=conference_name,
        conference_slug=slugify(conference_name),
        pdf_path=pdf_relative_path.as_posix(),
    )


def download_pdf(seed: PaperSeed, *, force: bool = False) -> Path:
    settings = get_settings()
    target_path = settings.repo_root / seed.pdf_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and not force:
        return target_path

    with _http_client() as client:
        response = client.get(seed.pdf_url)
        response.raise_for_status()
        target_path.write_bytes(response.content)

    return target_path


def crawl_archive(*, limit: int | None = None, force: bool = False) -> list[PaperSeed]:
    settings = get_settings()
    manifest = ManifestStore(settings.manifest_path)
    discovered_urls = fetch_document_urls()
    results: list[PaperSeed] = []

    for source_url in discovered_urls:
        record = manifest.get(source_url)
        target_exists = bool(record.get("pdf_path")) and (settings.repo_root / record["pdf_path"]).exists()

        seed: PaperSeed | None = None
        if record.get("seed") and target_exists and not force:
            seed = PaperSeed(**record["seed"])
        else:
            seed = parse_document_detail(source_url)
            manifest.update(source_url)

        if seed is None:
            manifest.update(source_url, status="skipped")
            continue

        pdf_path = download_pdf(seed, force=force)
        manifest.update(
            source_url,
            status="downloaded",
            pdf_path=pdf_path.relative_to(settings.repo_root).as_posix(),
            seed=asdict(seed),
        )
        manifest.save()

        results.append(seed)
        if limit is not None and len(results) >= limit:
            break

    manifest.save()
    return results
