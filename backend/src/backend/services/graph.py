from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, select

from backend.db.models import Affiliation, AuthorAffiliation, Paper, PaperAuthor, ReferenceEntry
from backend.db.session import engine


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
                company_id = f"company-{abs(hash(affiliation.name))}"
                nodes.append(
                    {
                        "data": {
                            "id": company_id,
                            "label": affiliation.name,
                            "type": "company",
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

        if paper.metadata_json:
            metadata = json.loads(paper.metadata_json)
            for affiliation in metadata.get("affiliations", []):
                company_id = f"company-{abs(hash(affiliation))}"
                nodes.append(
                    {
                        "data": {
                            "id": company_id,
                            "label": affiliation,
                            "type": "company",
                        }
                    }
                )

        references = session.exec(select(ReferenceEntry).where(ReferenceEntry.paper_id == paper_id)).all()
        for reference in references[:25]:
            reference_id = f"reference-{reference.id}"
            nodes.append(
                {
                    "data": {
                        "id": reference_id,
                        "label": reference.citation_text[:90],
                        "type": "reference",
                    }
                }
            )
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
