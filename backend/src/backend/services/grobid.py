from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from backend.core.config import get_settings
from backend.services.tei_parser import ParsedTeiDocument, parse_tei_document


@dataclass(slots=True)
class GrobidResult:
    tei_xml: str
    document: ParsedTeiDocument


def process_fulltext_document(pdf_path: Path) -> GrobidResult | None:
    settings = get_settings()
    if not settings.grobid_enabled:
        return None

    endpoint = f"{settings.grobid_url.rstrip('/')}/api/processFulltextDocument"
    with pdf_path.open("rb") as pdf_file:
        files = {"input": (pdf_path.name, pdf_file, "application/pdf")}
        data = {
            "consolidateHeader": "0",
            "consolidateCitations": "0",
            "includeRawAffiliations": "1",
            "includeRawCitations": "1",
        }
        try:
            with httpx.Client(timeout=settings.grobid_timeout_seconds) as client:
                response = client.post(endpoint, data=data, files=files)
                response.raise_for_status()
        except httpx.HTTPError:
            return None

    tei_xml = response.text.strip()
    if not tei_xml:
        return None

    try:
        document = parse_tei_document(tei_xml)
    except Exception:
        return None

    return GrobidResult(tei_xml=tei_xml, document=document)
