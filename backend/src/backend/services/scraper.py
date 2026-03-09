from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from slugify import slugify

from backend.core.config import get_settings


DVCON_BASE_URL = "https://dvcon-proceedings.org/"
ARCHIVE_HOME_URL = DVCON_BASE_URL
SEARCH_RESULTS_URL = urljoin(DVCON_BASE_URL, "document-search")
HTTP_RETRY_ATTEMPTS = 5
HTTP_RETRY_BACKOFF_SECONDS = 2


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


def _request_with_retries(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    request = getattr(client, method.lower())
    retryable_status_codes = {429, 500, 502, 503, 504, 521, 522, 524}

    last_error: Exception | None = None
    for attempt in range(HTTP_RETRY_ATTEMPTS):
        try:
            response = request(url, **kwargs)
            if response.status_code in retryable_status_codes:
                raise RuntimeError(f"Retryable HTTP status {response.status_code} for {url}")
            return response
        except (httpx.HTTPError, RuntimeError) as error:
            last_error = error
            if attempt >= HTTP_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(HTTP_RETRY_BACKOFF_SECONDS * (attempt + 1))

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Request failed for {url}")


def _homepage_filter_values(client: httpx.Client, select_name: str) -> list[str]:
    response = _request_with_retries(client, "GET", ARCHIVE_HOME_URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    select = soup.find("select", attrs={"name": select_name})
    if select is None:
        return []

    values: list[str] = []
    for option in select.find_all("option"):
        option_value = option.get("value", "").strip()
        if option_value and option_value not in values:
            values.append(option_value)

    return values


def _search_form_document_urls(client: httpx.Client, year_value: str, location_value: str) -> list[str]:
    response = _request_with_retries(
        client,
        "POST",
        SEARCH_RESULTS_URL,
        data={
            "ptp_filter_event_year": year_value,
            "ptp_filter_document_type": "paper",
            "ptp_filter_event_location": location_value,
            "textsearch": "",
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    document_urls: list[str] = []
    for row in soup.select("table.posts-data-table tbody tr"):
        anchor = row.select_one("td a[href]")
        if anchor is None:
            continue

        document_url = urljoin(DVCON_BASE_URL, anchor.get("href", "").strip())
        if not document_url or "/document/" not in document_url:
            continue
        if document_url in document_urls:
            continue

        document_urls.append(document_url)

    return document_urls


def fetch_document_urls(limit: int | None = None) -> list[str]:
    urls: list[str] = []
    seen_urls: set[str] = set()

    with _http_client() as client:
        year_values = _homepage_filter_values(client, "ptp_filter_event_year")
        location_values = _homepage_filter_values(client, "ptp_filter_event_location")

        for year_value in year_values:
            for location_value in location_values:
                for page_url in _search_form_document_urls(client, year_value, location_value):
                    if page_url in seen_urls:
                        continue
                    seen_urls.add(page_url)
                    urls.append(page_url)
                    if limit is not None and len(urls) >= limit:
                        return urls[:limit]

                if limit is not None and len(urls) >= limit:
                    continue

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


def _detail_page_has_downloadable_pdf(
    document_type: str,
    file_format: str,
    download_url: str,
) -> bool:
    if document_type.strip().lower() != "paper":
        return False

    normalized_format = file_format.strip().lower()
    if normalized_format == "pdf":
        return True

    normalized_download_url = download_url.strip().lower().split("?", 1)[0]
    if not normalized_format and normalized_download_url.endswith(".pdf"):
        return True

    return False


def parse_document_detail(source_url: str) -> PaperSeed | None:
    settings = get_settings()

    with _http_client() as client:
        response = _request_with_retries(client, "GET", source_url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    heading = soup.find(["h1", "title"])
    detail_map = _parse_detail_text_map(soup)

    download_anchor = soup.find("a", string=lambda value: isinstance(value, str) and "Download" in value)
    if not heading or not download_anchor:
        return None

    document_type = detail_map.get("type", "").strip()
    file_format = detail_map.get("format", "").strip().lower()
    pdf_url = urljoin(DVCON_BASE_URL, download_anchor.get("href", ""))
    if not pdf_url:
        return None

    if not _detail_page_has_downloadable_pdf(document_type, file_format, pdf_url):
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
        response = _request_with_retries(client, "GET", seed.pdf_url)
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
            try:
                seed = parse_document_detail(source_url)
                manifest.update(source_url, error=None)
            except Exception as error:
                manifest.update(source_url, status="error", error=str(error))
                manifest.save()
                continue

        if seed is None:
            manifest.update(source_url, status="skipped", error=None)
            continue

        try:
            pdf_path = download_pdf(seed, force=force)
        except Exception as error:
            manifest.update(source_url, status="error", error=str(error), seed=asdict(seed))
            manifest.save()
            continue
        manifest.update(
            source_url,
            status="downloaded",
            pdf_path=pdf_path.relative_to(settings.repo_root).as_posix(),
            seed=asdict(seed),
            error=None,
        )
        manifest.save()

        results.append(seed)
        if limit is not None and len(results) >= limit:
            break

    manifest.save()
    return results
