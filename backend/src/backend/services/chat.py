from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from backend.core.config import get_settings
from backend.services.indexer import SearchHit, hybrid_search, semantic_search


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


def _context_hits(question: str, selected_paper_ids: list[int]) -> list[SearchHit]:
    if selected_paper_ids:
        hits = semantic_search(question, limit=8, paper_ids=selected_paper_ids)
        if hits:
            return hits

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
    prompt = "\n\n".join(
        [
            "You are a research assistant for DVCon conference papers.",
            "Answer only from the supplied paper context.",
            "If the context is insufficient, say so clearly.",
            "Cite the paper title inline when you make a claim.",
            "Conversation:",
            transcript,
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
