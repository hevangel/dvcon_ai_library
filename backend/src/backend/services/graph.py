from __future__ import annotations

import re
from typing import Any

from slugify import slugify
from sqlmodel import Session, select

from backend.db.models import Affiliation, AuthorAffiliation, Paper, PaperAuthor, ReferenceEntry
from backend.db.session import engine


def _company_node_id(name: str) -> str:
    """Stable, deterministic node id for a company/affiliation label.

    Uses a slug of the name rather than Python's randomized hash(), so node ids
    stay consistent across processes/restarts.
    """
    return f"company-{slugify(name) or 'unknown'}"


def _affiliation_node_label(affiliation: Affiliation) -> str:
    """Display label for an affiliation node, enriched with location when known."""
    location_parts = [
        part
        for part in (affiliation.city, affiliation.state_province, affiliation.country)
        if part
    ]
    if not location_parts:
        return affiliation.name
    return f"{affiliation.name} ({', '.join(location_parts)})"


def _normalize_title_for_match(text: str | None) -> str:
    """Normalize a title for cross-source matching.

    Whitespace-collapse (mirroring tei_parser._clean_text), casefold, and strip
    punctuation so that "A New, Fast Method!" matches "A new fast method".
    """
    if not text:
        return ""
    text = " ".join(text.split()).strip().casefold()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _build_paper_title_index(session: Session) -> dict[str, int]:
    """Return {normalized_title -> paper_id} for the whole corpus.

    First-match wins on title collisions (rare; acceptable for graph
    reference-resolution UX). Built once per graph build (~1852 rows, cheap).
    """
    index: dict[str, int] = {}
    for row in session.exec(select(Paper.id, Paper.title)).all():
        paper_id, title = row
        normalized = _normalize_title_for_match(title)
        if normalized and normalized not in index:
            index[normalized] = paper_id
    return index


def build_paper_graph(paper_id: int) -> dict[str, list[dict[str, Any]]]:
    with Session(engine) as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            return {"nodes": [], "edges": []}

        nodes: list[dict[str, Any]] = [
            {
                "data": {
                    "id": f"paper-{paper.id}",
                    "label": paper.title,
                    "type": "paper",
                    "paper_id": paper.id,
                }
            }
        ]
        edges: list[dict[str, Any]] = []

        if paper.conference is not None:
            nodes.append(
                {
                    "data": {
                        "id": f"conference-{paper.conference.id}",
                        "label": paper.conference.name,
                        "type": "conference",
                        "conference_name": paper.conference.name,
                        "year": paper.conference.year,
                        "location": paper.conference.location,
                    }
                }
            )
            edges.append(
                {
                    "data": {
                        "id": f"paper-{paper.id}-conference-{paper.conference.id}",
                        "source": f"paper-{paper.id}",
                        "target": f"conference-{paper.conference.id}",
                        "label": "presented_at",
                    }
                }
            )

        author_links = session.exec(
            select(PaperAuthor).where(PaperAuthor.paper_id == paper_id).order_by(PaperAuthor.author_order)
        ).all()
        affiliation_links = session.exec(
            select(AuthorAffiliation).where(AuthorAffiliation.paper_id == paper_id)
        ).all()
        affiliation_map = {
            affiliation.id: affiliation
            for affiliation in session.exec(
                select(Affiliation).where(
                    Affiliation.id.in_([link.affiliation_id for link in affiliation_links if link.affiliation_id])
                )
            ).all()
        }
        for link in author_links:
            author = next((item for item in paper.authors if item.id == link.author_id), None)
            if author is None:
                continue

            nodes.append(
                {
                    "data": {
                        "id": f"author-{author.id}",
                        "label": author.name,
                        "type": "author",
                        "author_name": author.name,
                    }
                }
            )
            edges.append(
                {
                    "data": {
                        "id": f"paper-{paper.id}-author-{author.id}",
                        "source": f"author-{author.id}",
                        "target": f"paper-{paper.id}",
                        "label": "authored",
                    }
                }
            )

            author_affiliations = [
                affiliation_map[affiliation_link.affiliation_id]
                for affiliation_link in affiliation_links
                if affiliation_link.author_id == author.id and affiliation_link.affiliation_id in affiliation_map
            ]
            if not author_affiliations and link.company_name:
                author_affiliations = [Affiliation(id=None, name=link.company_name)]

            for affiliation in author_affiliations:
                company_id = _company_node_id(affiliation.name)
                nodes.append(
                    {
                        "data": {
                            "id": company_id,
                            "label": _affiliation_node_label(affiliation),
                            "type": "company",
                            "company_name": affiliation.name,
                        }
                    }
                )
                edges.append(
                    {
                        "data": {
                            "id": f"author-{author.id}-{company_id}",
                            "source": f"author-{author.id}",
                            "target": company_id,
                            "label": "affiliated_with",
                        }
                    }
                )

        references = session.exec(select(ReferenceEntry).where(ReferenceEntry.paper_id == paper_id)).all()
        paper_title_index = _build_paper_title_index(session)
        for reference in references[:25]:
            reference_id = f"reference-{reference.id}"
            reference_node_data: dict[str, Any] = {
                "id": reference_id,
                "label": reference.citation_text[:90],
                "type": "reference",
                "reference_id": reference.id,
            }
            # Resolve to an in-corpus paper when the normalized reference title
            # exactly matches a corpus paper title. Only references that resolve
            # get a `paper_id` payload, which the frontend uses to mark them
            # clickable.
            resolved_paper_id = paper_title_index.get(_normalize_title_for_match(reference.normalized_title))
            if resolved_paper_id is not None:
                reference_node_data["paper_id"] = resolved_paper_id
            nodes.append({"data": reference_node_data})
            edges.append(
                {
                    "data": {
                        "id": f"paper-{paper.id}-reference-{reference.id}",
                        "source": f"paper-{paper.id}",
                        "target": reference_id,
                        "label": "references",
                    }
                }
            )

        deduped_nodes = {node["data"]["id"]: node for node in nodes}
        deduped_edges = {edge["data"]["id"]: edge for edge in edges}
        return {
            "nodes": list(deduped_nodes.values()),
            "edges": list(deduped_edges.values()),
        }
