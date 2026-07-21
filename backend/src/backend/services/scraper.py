from __future__ import annotations

import json
import os
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any
from urllib.parse import urljoin

import fitz
import httpx
from bs4 import BeautifulSoup
from slugify import slugify

from backend.core.config import get_settings


DVCON_BASE_URL = "https://dvcon-proceedings.org/"
ARCHIVE_HOME_URL = DVCON_BASE_URL
SEARCH_RESULTS_URL = urljoin(DVCON_BASE_URL, "document-search")
ADMIN_AJAX_URL = urljoin(DVCON_BASE_URL, "wp-admin/admin-ajax.php")
HTTP_RETRY_ATTEMPTS = 5
HTTP_RETRY_BACKOFF_SECONDS = 2
AJAX_PAGE_SIZE = 100
_TABLE_ID_PATTERN = re.compile(r"dlp_[a-f0-9]+_\d+")


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
        """Atomically persist the manifest.

        Writes to a sibling temp file then `os.replace`s it into place, so a
        crash mid-write cannot leave a half-written ingest_manifest.json.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        os.replace(tmp_path, self.path)

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


def _retry_delay_seconds(attempt: int, response: httpx.Response | None) -> float:
    """Exponential backoff with jitter; honors Retry-After on 429.

    `attempt` is 0-indexed. Without Retry-After, delay grows as
    base * 2**attempt with up to half-base jitter, so concurrent callers don't
    retry in lockstep.
    """
    if response is not None and response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return float(retry_after)
    base = HTTP_RETRY_BACKOFF_SECONDS
    return base * (2**attempt) + random.uniform(0, base * 0.5)


def _request_with_retries(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    request = getattr(client, method.lower())
    retryable_status_codes = {429, 500, 502, 503, 504, 521, 522, 524}

    last_error: Exception | None = None
    response: httpx.Response | None = None
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
            time.sleep(_retry_delay_seconds(attempt, response))

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
    """Return document detail-page URLs for a Year x Location x Type=paper filter.

    The DVCon site renders its results table client-side via the Document
    Library Pro WordPress plugin (DataTables `serverSide: true`). The HTML
    table returned by the search form is just a header skeleton; the rows are
    fetched separately via an AJAX call to `admin-ajax.php` keyed by a
    page-bound `table_id` (a WordPress transient). Filters are bound into the
    `table_id` server-side by the search-form POST, so the AJAX call itself
    must NOT resend them.

    Flow per (year, location):
      1. POST the search form -> the response HTML contains a fresh
         `<table id="dlp_<hex>_<n>">` whose id is bound to the filter combo.
      2. POST `action=dlp_load_posts` with that `table_id`, paging
         `start` by `AJAX_PAGE_SIZE` until `start >= recordsTotal`.
      3. Parse `<a href=".../document/.../">` from each returned row.
    """
    search_response = _request_with_retries(
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
    search_response.raise_for_status()

    table_id_match = _TABLE_ID_PATTERN.search(search_response.text)
    if table_id_match is None:
        # Plugin not present or page shape changed; fall back to the legacy
        # server-rendered table parse so a partial site change doesn't wipe
        # already-discovered URLs from the manifest.
        return _legacy_table_document_urls(search_response.text)

    table_id = table_id_match.group(0)
    document_urls: list[str] = []

    start = 0
    while True:
        ajax_response = _request_with_retries(
            client,
            "POST",
            ADMIN_AJAX_URL,
            data={
                "action": "dlp_load_posts",
                "table_id": table_id,
                "start": str(start),
                "length": str(AJAX_PAGE_SIZE),
                "search[value]": "",
                "order[0][column]": "0",
                "order[0][dir]": "asc",
            },
        )
        ajax_response.raise_for_status()

        payload = json.loads(ajax_response.text)
        rows = payload.get("data") or []
        if not rows:
            break

        for row in rows:
            # Each row is a dict whose values are already JSON-decoded HTML
            # strings; document links live in the "title" value. Don't
            # re-serialize (that would re-escape "/" to "\/" and break the regex).
            row_values = row.values() if isinstance(row, dict) else [row]
            for value in row_values:
                if not isinstance(value, str):
                    continue
                for href in re.findall(r'href="(https?://[^"]*?/document/[^"]+)"', value):
                    document_url = urljoin(DVCON_BASE_URL, href).rstrip("/")
                    if not document_url or "/document/" not in document_url:
                        continue
                    if document_url in document_urls:
                        continue
                    document_urls.append(document_url)

        start += AJAX_PAGE_SIZE
        total = payload.get("recordsTotal") or 0
        if start >= total:
            break

    return document_urls


def _legacy_table_document_urls(html: str) -> list[str]:
    """Parse the old server-rendered `<table class="posts-data-table">` shape.

    Kept as a defensive fallback for older site snapshots; the live site
    switched to client-side row loading in 2025 and the table is now empty
    in the initial HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
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


def fetch_document_urls(limit: int | None = None, years: list[int] | None = None) -> list[str]:
    """Crawl the DVCon document-search form for `/document/` detail-page URLs.

    `years` (4-digit ints, e.g. `[2025, 2026]`) restricts the crawl to those
    year filters; when None, every year filter exposed on the homepage is
    walked. Scoping is strongly recommended for incremental ingests because
    re-walking years you already have is the slow part of a full crawl.
    """
    urls: list[str] = []
    seen_urls: set[str] = set()

    if years:
        wanted_year_values = {f"y{int(year)}" for year in years}
    else:
        wanted_year_values = None

    with _http_client() as client:
        year_values = _homepage_filter_values(client, "ptp_filter_event_year")
        location_values = _homepage_filter_values(client, "ptp_filter_event_location")

        for year_value in year_values:
            if wanted_year_values is not None and year_value not in wanted_year_values:
                continue
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
        _validate_pdf_response(seed.pdf_url, response)
        target_path.write_bytes(response.content)

    _validate_pdf_file(target_path)
    return target_path


def _validate_pdf_response(url: str, response: httpx.Response) -> None:
    """Reject HTML error pages / Cloudflare interstitials / truncated bodies.

    A 200 with an HTML body (WAF challenge, "session expired") or a truncated
    download would otherwise be persisted as a .pdf and then crash extraction.
    Raises ValueError on failure so `crawl_archive` records it in the manifest.
    """
    content = response.content
    if not content.startswith(b"%PDF-"):
        raise ValueError(
            f"PDF download from {url} did not start with %PDF- magic bytes "
            f"(got {content[:16]!r}); likely an HTML error page or interstitial."
        )

    declared_length = response.headers.get("Content-Length")
    if declared_length and declared_length.isdigit() and int(declared_length) != len(content):
        raise ValueError(
            f"PDF download from {url} truncated: Content-Length={declared_length} "
            f"but received {len(content)} bytes."
        )


def _validate_pdf_file(path: Path) -> None:
    """Open the saved PDF and assert it has at least one page.

    Cheap integrity check that catches corrupt/truncated files that passed the
    magic-byte check but are still unparseable. Deletes the bad file so the
    next run re-downloads instead of trusting the broken local copy.
    """
    try:
        with fitz.open(path) as document:
            if document.page_count <= 0:
                raise ValueError("PDF has zero pages.")
    except Exception as error:
        try:
            path.unlink()
        except OSError:
            pass
        raise ValueError(f"Saved PDF at {path} is not a valid PDF: {error}") from error


def crawl_archive(*, limit: int | None = None, force: bool = False, years: list[int] | None = None) -> list[PaperSeed]:
    settings = get_settings()
    manifest = ManifestStore(settings.manifest_path)
    discovered_urls = fetch_document_urls(years=years)
    results: list[PaperSeed] = []
    # Save on every error (so failures aren't lost), and every N successful
    # downloads (avoids O(n^2) full-manifest rewrites over a large archive),
    # plus once at the end.
    save_every = 25
    processed_since_save = 0

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

        results.append(seed)
        processed_since_save += 1
        if processed_since_save >= save_every:
            manifest.save()
            processed_since_save = 0

        if limit is not None and len(results) >= limit:
            break

    manifest.save()
    return results
