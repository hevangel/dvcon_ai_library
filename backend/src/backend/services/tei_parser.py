from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


@dataclass(slots=True)
class ParsedAuthor:
    full_name: str
    given_name: str = ""
    surname: str = ""
    affiliations: list[str] = field(default_factory=list)
    email: str | None = None


@dataclass(slots=True)
class ParsedReference:
    citation_text: str
    normalized_title: str | None = None
    authors_text: str | None = None
    journal_or_book: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    raw_tei_json: str | None = None


@dataclass(slots=True)
class ParsedTeiDocument:
    title: str | None = None
    abstract: str | None = None
    authors: list[ParsedAuthor] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    references: list[ParsedReference] = field(default_factory=list)


def _clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return _clean_text("".join(node.itertext()))


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def _author_name(author_node: ET.Element) -> tuple[str, str, str]:
    pers_name = author_node.find(".//tei:persName", TEI_NS)
    if pers_name is None:
        full_name = _node_text(author_node)
        return full_name, "", ""

    given_names = [
        _node_text(forename)
        for forename in pers_name.findall("./tei:forename", TEI_NS)
        if _node_text(forename)
    ]
    surname = _node_text(pers_name.find("./tei:surname", TEI_NS))
    full_name = _clean_text(" ".join([*given_names, surname]))
    return full_name, " ".join(given_names).strip(), surname


def _affiliation_texts(author_node: ET.Element) -> list[str]:
    values: list[str] = []
    for affiliation in author_node.findall(".//tei:affiliation", TEI_NS):
        organization_names = [
            _node_text(node) for node in affiliation.findall(".//tei:orgName", TEI_NS) if _node_text(node)
        ]
        address_parts = [
            _node_text(node)
            for node in affiliation.findall(".//tei:address/*", TEI_NS)
            if _node_text(node)
        ]
        combined = organization_names + address_parts
        if combined:
            values.append(", ".join(combined))
            continue

        raw_text = _node_text(affiliation)
        if raw_text:
            values.append(raw_text)

    return _dedupe_preserve_order(values)


def _parse_authors(root: ET.Element) -> list[ParsedAuthor]:
    author_nodes = root.findall(".//tei:teiHeader//tei:fileDesc//tei:sourceDesc//tei:analytic//tei:author", TEI_NS)
    if not author_nodes:
        author_nodes = root.findall(".//tei:teiHeader//tei:fileDesc//tei:titleStmt//tei:author", TEI_NS)

    authors: list[ParsedAuthor] = []
    for author_node in author_nodes:
        full_name, given_name, surname = _author_name(author_node)
        if not full_name:
            continue

        email = _node_text(author_node.find(".//tei:email", TEI_NS)) or None
        authors.append(
            ParsedAuthor(
                full_name=full_name,
                given_name=given_name,
                surname=surname,
                affiliations=_affiliation_texts(author_node),
                email=email,
            )
        )

    return authors


def _parse_references(root: ET.Element) -> list[ParsedReference]:
    references: list[ParsedReference] = []
    for bibl_struct in root.findall(".//tei:listBibl//tei:biblStruct", TEI_NS):
        analytic_title = _node_text(bibl_struct.find("./tei:analytic/tei:title", TEI_NS))
        monograph_title = _node_text(bibl_struct.find("./tei:monogr/tei:title", TEI_NS))
        normalized_title = analytic_title or monograph_title or None

        author_names: list[str] = []
        for author_node in bibl_struct.findall(".//tei:analytic/tei:author", TEI_NS):
            full_name, _, _ = _author_name(author_node)
            if full_name:
                author_names.append(full_name)
        authors_text = ", ".join(author_names) if author_names else None

        journal_or_book = monograph_title or None
        date_node = bibl_struct.find(".//tei:imprint/tei:date", TEI_NS)
        year_text = ""
        if date_node is not None:
            year_text = date_node.attrib.get("when", "") or _node_text(date_node)
        year_match = YEAR_PATTERN.search(year_text)
        publication_year = int(year_match.group(0)) if year_match else None

        doi = None
        for idno in bibl_struct.findall(".//tei:idno", TEI_NS):
            id_type = (idno.attrib.get("type", "") or "").strip().lower()
            if id_type == "doi":
                doi = _node_text(idno) or None
                break

        citation_text = _node_text(bibl_struct)
        if not citation_text:
            continue

        raw_payload = {
            "title": normalized_title,
            "authors_text": authors_text,
            "journal_or_book": journal_or_book,
            "publication_year": publication_year,
            "doi": doi,
        }
        references.append(
            ParsedReference(
                citation_text=citation_text,
                normalized_title=normalized_title,
                authors_text=authors_text,
                journal_or_book=journal_or_book,
                publication_year=publication_year,
                doi=doi,
                raw_tei_json=json.dumps(raw_payload, ensure_ascii=True),
            )
        )

    return references


def parse_tei_document(tei_xml: str) -> ParsedTeiDocument:
    root = ET.fromstring(tei_xml)
    title = _node_text(root.find(".//tei:teiHeader//tei:fileDesc//tei:titleStmt//tei:title", TEI_NS)) or None
    abstract = _node_text(root.find(".//tei:teiHeader//tei:profileDesc//tei:abstract", TEI_NS)) or None
    authors = _parse_authors(root)

    affiliations: list[str] = []
    for author in authors:
        affiliations.extend(author.affiliations)

    return ParsedTeiDocument(
        title=title,
        abstract=abstract,
        authors=authors,
        affiliations=_dedupe_preserve_order(affiliations),
        references=_parse_references(root),
    )
