from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from backend.core.config import get_settings
from backend.services.indexer import SearchHit, get_paper, get_paper_chunks, hybrid_search


@dataclass(slots=True)
class ChatAnswer:
    answer: str
    citations: list[dict[str, str]]
    scope_paper_ids: list[int]


def _latest_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "").strip()
    return ""


def _paper_scope_hits(selected_paper_ids: list[int]) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for paper_id in selected_paper_ids:
        paper = get_paper(paper_id)
        if paper is None:
            continue

        paper_chunks = get_paper_chunks(paper_id)
        snippet = (paper.abstract or "").strip()
        if not snippet:
            snippet = next((chunk.text.strip() for chunk in paper_chunks if chunk.text.strip()), "")
        if not snippet:
            snippet = (paper.searchable_text or paper.title).strip()

        hits.append(
            SearchHit(
                paper=paper,
                score=1.0,
                snippet=snippet[:400],
            )
        )

    return hits


def _context_hits(question: str, selected_paper_ids: list[int]) -> list[SearchHit]:
    if selected_paper_ids:
        retrieved_hits = {
            hit.paper.id: hit
            for hit in hybrid_search(
                question,
                limit=max(8, len(selected_paper_ids)),
                paper_ids=selected_paper_ids,
            )
        }
        scoped_hits = {hit.paper.id: hit for hit in _paper_scope_hits(selected_paper_ids)}
        return [
            retrieved_hits.get(paper_id) or scoped_hits.get(paper_id)
            for paper_id in selected_paper_ids
            if retrieved_hits.get(paper_id) or scoped_hits.get(paper_id)
        ]

    return hybrid_search(question, limit=8)


def answer_question(messages: list[dict[str, str]], selected_paper_ids: list[int]) -> ChatAnswer:
    settings = get_settings()
    if not settings.chat_is_configured:
        raise RuntimeError("OpenAI chat is not configured. Set OPENAI_BASE_URL and OPENAI_API_KEY.")

    question = _latest_user_message(messages)
    if not question:
        raise RuntimeError("A user message is required to chat with the papers.")

    hits = _context_hits(question, selected_paper_ids)
    if not hits:
        return ChatAnswer(
            answer="No relevant paper context was found for that question.",
            citations=[],
            scope_paper_ids=selected_paper_ids,
        )

    context_blocks = []
    citations: list[dict[str, str]] = []
    for index, hit in enumerate(hits, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"Title: {hit.paper.title}",
                    f"Year: {hit.paper.year}",
                    f"Location: {hit.paper.location}",
                    f"Excerpt: {hit.snippet}",
                ]
            )
        )
        citations.append({"title": hit.paper.title, "year": str(hit.paper.year)})

    transcript = "\n".join(f"{item['role']}: {item['content']}" for item in messages[-8:])
    selected_scope_block = ""
    if selected_paper_ids:
        selected_scope_lines = [
            f"- {hit.paper.title} ({hit.paper.year}, {hit.paper.location})"
            for hit in hits
        ]
        selected_scope_block = "\n".join(
            [
                "Selected paper scope:",
                *selected_scope_lines,
            ]
        )

    prompt = "\n\n".join(
        [
            "You are a research assistant for DVCon conference papers.",
            "Answer only from the supplied paper context.",
            "If the context is insufficient, say so clearly.",
            "Cite the paper title inline when you make a claim.",
            "If a selected paper scope is provided, treat references such as 'the selected papers', 'these papers', or 'the two papers' as that scope.",
            "Conversation:",
            transcript,
            selected_scope_block,
            "Paper context:",
            "\n\n".join(context_blocks),
        ]
    )

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    response = client.responses.create(
        model=settings.openai_chat_model,
        input=prompt,
    )

    answer = getattr(response, "output_text", "").strip() or "No response generated."
    return ChatAnswer(
        answer=answer,
        citations=citations,
        scope_paper_ids=selected_paper_ids or [hit.paper.id for hit in hits],
    )
