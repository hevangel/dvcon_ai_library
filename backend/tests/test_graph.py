"""Tests for the clickable metadata graph (`services/graph.py`).

Covers:
- node payload fields (paper_id, author_name, company_name, conference year+location)
- reference-to-paper resolution via normalized title lookup
- non-matching references stay non-clickable (no paper_id)
"""

from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

import backend.services.graph as graph_mod
from backend.db.models import (
    Affiliation,
    Author,
    AuthorAffiliation,
    Conference,
    Paper,
    PaperAuthor,
    ReferenceEntry,
)


def _build_isolated_engine(tmp_path: Path):
    """Create a fresh SQLite engine + schema in an isolated tmp file.

    `build_paper_graph` imports `engine` from `backend.db.session` at module
    load, so we monkeypatch `graph_mod.engine` to point at our isolated test
    DB rather than touching the live local corpus.
    """
    db_path = tmp_path / "graph_test.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)
    return test_engine


def _seed_corpus(session: Session) -> tuple[int, int]:
    """Seed two papers in different conferences with a shared author + company,
    plus three references on paper 1 (one resolving to paper 2, two not).
    Returns (paper1_id, paper2_id).
    """
    conf1 = Conference(slug="dvcon-india-2025", name="DVCon India 2025", year=2025, location="india")
    conf2 = Conference(slug="dvcon-us-2026", name="DVCon US 2026", year=2026, location="united-states")
    session.add(conf1)
    session.add(conf2)
    session.flush()

    paper1 = Paper(
        source_url="https://example.com/doc/p1",
        pdf_url="https://example.com/p1.pdf",
        pdf_path="data/paper/2025/india/p1.pdf",
        slug="p1",
        title="A Novel Verification Method",
        year=2025,
        location="india",
        document_type="Paper",
        conference_id=conf1.id,
    )
    paper2 = Paper(
        source_url="https://example.com/doc/p2",
        pdf_url="https://example.com/p2.pdf",
        pdf_path="data/paper/2026/united-states/p2.pdf",
        slug="p2",
        title="Some Unrelated Design Paper",
        year=2026,
        location="united-states",
        document_type="Paper",
        conference_id=conf2.id,
    )
    session.add(paper1)
    session.add(paper2)
    session.flush()

    # Shared author + affiliation on paper 1.
    author = Author(name="Jane Doe")
    session.add(author)
    session.flush()
    session.add(PaperAuthor(paper_id=paper1.id, author_id=author.id, author_order=0, company_name="Acme Corp"))
    affiliation = Affiliation(name="Acme Corp", city="Bangalore", state_province=None, country="India")
    session.add(affiliation)
    session.flush()
    session.add(
        AuthorAffiliation(
            paper_id=paper1.id,
            author_id=author.id,
            affiliation_id=affiliation.id,
            author_order=0,
        )
    )

    # Three references on paper 1:
    #   - ref_match: normalized_title exactly matches paper2.title -> should resolve
    #   - ref_match_punct: normalized_title matches paper2.title up to punctuation/case -> should resolve
    #   - ref_unmatched: a title with no corpus match -> should NOT resolve
    for ref in (
        ReferenceEntry(
            paper_id=paper1.id,
            citation_text="Jane Doe. Some Unrelated Design Paper. DVCon 2026.",
            normalized_title="Some Unrelated Design Paper",
        ),
        ReferenceEntry(
            paper_id=paper1.id,
            citation_text="Jane Doe. SOME, Unrelated! Design Paper?. DVCon 2026.",
            normalized_title="SOME, Unrelated! Design Paper?",
        ),
        ReferenceEntry(
            paper_id=paper1.id,
            citation_text="External Author. A Paper Not In Corpus. IEEE 2019.",
            normalized_title="A Paper Not In Corpus",
        ),
    ):
        session.add(ref)

    session.commit()
    return paper1.id, paper2.id


def test_graph_node_payload_fields_and_reference_resolution(tmp_path, monkeypatch) -> None:
    test_engine = _build_isolated_engine(tmp_path)
    monkeypatch.setattr(graph_mod, "engine", test_engine)

    with Session(test_engine) as session:
        paper1_id, paper2_id = _seed_corpus(session)

    graph = graph_mod.build_paper_graph(paper1_id)

    nodes_by_id = {node["data"]["id"]: node["data"] for node in graph["nodes"]}

    # Active paper node carries paper_id (for consistency) and type=paper.
    paper_node = nodes_by_id[f"paper-{paper1_id}"]
    assert paper_node["type"] == "paper"
    assert paper_node["paper_id"] == paper1_id

    # Author node carries author_name.
    author_nodes = [d for d in nodes_by_id.values() if d.get("type") == "author"]
    assert len(author_nodes) == 1
    assert author_nodes[0]["author_name"] == "Jane Doe"

    # Company node carries company_name (the raw affiliation name, not the
    # display label which has " (Bangalore, India)" appended).
    company_nodes = [d for d in nodes_by_id.values() if d.get("type") == "company"]
    assert len(company_nodes) == 1
    assert company_nodes[0]["company_name"] == "Acme Corp"

    # Conference node carries year + location for precise search filtering.
    conf_nodes = [d for d in nodes_by_id.values() if d.get("type") == "conference"]
    assert len(conf_nodes) == 1
    assert conf_nodes[0]["conference_name"] == "DVCon India 2025"
    assert conf_nodes[0]["year"] == 2025
    assert conf_nodes[0]["location"] == "india"

    # References: the two matching ones resolve to paper2_id; the unmatched
    # one carries no paper_id (so the frontend renders it non-clickable).
    ref_nodes = [d for d in nodes_by_id.values() if d.get("type") == "reference"]
    assert len(ref_nodes) == 3
    resolved = [r for r in ref_nodes if "paper_id" in r]
    unresolved = [r for r in ref_nodes if "paper_id" not in r]
    assert len(resolved) == 2
    assert len(unresolved) == 1
    assert all(r["paper_id"] == paper2_id for r in resolved)
    assert "paper_id" not in unresolved[0]
    # All reference nodes carry reference_id regardless of resolution.
    assert all("reference_id" in r for r in ref_nodes)


def test_graph_for_missing_paper_returns_empty(tmp_path, monkeypatch) -> None:
    test_engine = _build_isolated_engine(tmp_path)
    monkeypatch.setattr(graph_mod, "engine", test_engine)

    graph = graph_mod.build_paper_graph(paper_id=999_999)
    assert graph == {"nodes": [], "edges": []}
