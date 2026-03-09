from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import re

from openai import OpenAI

from backend.core.config import get_settings
from backend.services.indexer import SearchHit, get_paper, get_paper_chunks, hybrid_search


DEFAULT_CHAT_MODEL_CONTEXT_WINDOW = 128000
KNOWN_CHAT_MODEL_CONTEXT_WINDOWS = {
    "gpt-5-mini": 400000,
}
DEFAULT_CHAT_CONTEXT_OUTPUT_RESERVE_TOKENS = 12000
MAX_SELECTED_PAPER_CHUNKS = 5
MAX_SELECTED_CHUNK_CHARS = 1400
MAX_RETRIEVAL_EXCERPT_CHARS = 600
QUESTION_TERM_PATTERN = re.compile(r"[a-z0-9]+")
COMPARE_TERMS = {
    "compare",
    "comparison",
    "contrast",
    "contrasts",
    "different",
    "difference",
    "differences",
    "similar",
    "similarity",
    "similarities",
    "versus",
    "vs",
}
SECTION_HEADING_KEYWORDS = {
    "abstract",
    "introduction",
    "overview",
    "background",
    "approach",
    "method",
    "methods",
    "methodology",
    "architecture",
    "implementation",
    "evaluation",
    "experiment",
    "experiments",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "of",
    "on",
    "or",
    "paper",
    "papers",
    "please",
    "show",
    "summarize",
    "tell",
    "than",
    "that",
    "the",
    "their",
    "them",
    "these",
    "this",
    "those",
    "to",
    "two",
    "what",
    "which",
    "with",
}


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


def _estimate_token_count(text: str) -> int:
    normalized_text = text.strip()
    if not normalized_text:
        return 0
    return max(1, ceil(len(normalized_text) / 4))


def _chat_model_context_window(settings: object) -> int:
    configured_window = getattr(settings, "openai_chat_model_context_window", None)
    if isinstance(configured_window, int) and configured_window > 0:
        return configured_window

    model_name = str(getattr(settings, "openai_chat_model", "")).strip().lower()
    return KNOWN_CHAT_MODEL_CONTEXT_WINDOWS.get(model_name, DEFAULT_CHAT_MODEL_CONTEXT_WINDOW)


def _chat_output_reserve_tokens(settings: object) -> int:
    configured_reserve = getattr(settings, "chat_context_output_reserve_tokens", None)
    if isinstance(configured_reserve, int) and configured_reserve > 0:
        return configured_reserve
    return DEFAULT_CHAT_CONTEXT_OUTPUT_RESERVE_TOKENS


def _merge_overlapping_chunk_text(existing_text: str, incoming_text: str, max_overlap: int) -> str:
    if not existing_text:
        return incoming_text
    if not incoming_text:
        return existing_text
    if incoming_text in existing_text:
        return existing_text

    overlap_limit = min(max_overlap, len(existing_text), len(incoming_text))
    for overlap_length in range(overlap_limit, 0, -1):
        if existing_text[-overlap_length:] == incoming_text[:overlap_length]:
            return existing_text + incoming_text[overlap_length:]

    return f"{existing_text} {incoming_text}".strip()


def _paper_full_text(paper_id: int, chunk_overlap: int) -> str:
    paper_chunks = get_paper_chunks(paper_id)
    if not paper_chunks:
        return ""

    section_blocks: list[str] = []
    current_heading: str | None = None
    merged_section_text = ""

    for chunk in paper_chunks:
        chunk_text = chunk.text.strip()
        if not chunk_text:
            continue

        chunk_heading = (chunk.heading or "Content").strip()
        if current_heading is None:
            current_heading = chunk_heading

        if chunk_heading != current_heading:
            if merged_section_text:
                section_blocks.append(f"{current_heading}:\n{merged_section_text}")
            current_heading = chunk_heading
            merged_section_text = chunk_text
            continue

        merged_section_text = _merge_overlapping_chunk_text(
            merged_section_text,
            chunk_text,
            max_overlap=max(chunk_overlap * 2, 200),
        )

    if current_heading and merged_section_text:
        section_blocks.append(f"{current_heading}:\n{merged_section_text}")

    return "\n\n".join(section_blocks)


def _question_terms(question: str) -> list[str]:
    return [
        term
        for term in QUESTION_TERM_PATTERN.findall(question.lower())
        if len(term) >= 3 and term not in STOPWORDS
    ]


def _is_compare_question(question: str) -> bool:
    question_terms = set(_question_terms(question))
    return any(term in COMPARE_TERMS for term in question_terms)


def _chunk_match_score(chunk_heading: str, chunk_text: str, question_terms: list[str]) -> int:
    if not question_terms:
        return 0

    heading_text = chunk_heading.lower()
    body_text = chunk_text.lower()
    score = 0
    for term in question_terms:
        if term in heading_text:
            score += 5
        score += body_text.count(term)
    return score


def _select_selected_paper_chunks(hit: SearchHit, question: str) -> list[tuple[str, str]]:
    paper_chunks = get_paper_chunks(hit.paper.id or 0)
    if not paper_chunks:
        return []

    question_terms = _question_terms(question)
    is_compare_question = _is_compare_question(question)
    ranked_chunks: list[tuple[int, int, str, str]] = []

    for chunk in paper_chunks:
        chunk_text = chunk.text.strip()
        if not chunk_text:
            continue

        chunk_heading = (chunk.heading or "Content").strip()
        heading_tokens = set(QUESTION_TERM_PATTERN.findall(chunk_heading.lower()))
        score = _chunk_match_score(chunk_heading, chunk_text, question_terms)

        if any(token in SECTION_HEADING_KEYWORDS for token in heading_tokens):
            score += 2

        if is_compare_question and any(
            token in {"approach", "method", "methods", "results", "discussion", "conclusion", "conclusions"}
            for token in heading_tokens
        ):
            score += 4

        ranked_chunks.append((score, chunk.chunk_index, chunk_heading, chunk_text))

    if not ranked_chunks:
        return []

    selected_indexes: set[int] = set()
    chosen_chunks: list[tuple[int, str, str]] = []

    # Always anchor each selected paper with its earliest non-empty chunk for basic paper framing.
    first_score, first_index, first_heading, first_text = min(
        ranked_chunks,
        key=lambda item: item[1],
    )
    selected_indexes.add(first_index)
    chosen_chunks.append((first_index, first_heading, first_text))

    for score, chunk_index, chunk_heading, chunk_text in sorted(
        ranked_chunks,
        key=lambda item: (-item[0], item[1]),
    ):
        if len(chosen_chunks) >= MAX_SELECTED_PAPER_CHUNKS:
            break
        if chunk_index in selected_indexes:
            continue
        if score <= 0 and len(chosen_chunks) >= 2:
            continue
        selected_indexes.add(chunk_index)
        chosen_chunks.append((chunk_index, chunk_heading, chunk_text))

    if is_compare_question:
        for score, chunk_index, chunk_heading, chunk_text in sorted(
            ranked_chunks,
            key=lambda item: item[1],
        ):
            if len(chosen_chunks) >= MAX_SELECTED_PAPER_CHUNKS:
                break
            if chunk_index in selected_indexes:
                continue
            heading_tokens = set(QUESTION_TERM_PATTERN.findall(chunk_heading.lower()))
            if heading_tokens.isdisjoint({"results", "discussion", "conclusion", "conclusions"}):
                continue
            selected_indexes.add(chunk_index)
            chosen_chunks.append((chunk_index, chunk_heading, chunk_text))

    return [
        (chunk_heading, chunk_text[:MAX_SELECTED_CHUNK_CHARS])
        for _, chunk_heading, chunk_text in sorted(chosen_chunks, key=lambda item: item[0])
    ]


def _selected_paper_context_block(hit: SearchHit, question: str) -> str:
    block_lines = [
        f"Title: {hit.paper.title}",
        f"Year: {hit.paper.year}",
        f"Location: {hit.paper.location}",
    ]

    if hit.paper.abstract:
        block_lines.extend(
            [
                "Abstract:",
                hit.paper.abstract.strip(),
            ]
        )

    chunk_lines: list[str] = []
    for chunk_heading, chunk_text in _select_selected_paper_chunks(hit, question):
        chunk_lines.extend(
            [
                f"{chunk_heading}:",
                chunk_text,
            ]
        )

    if chunk_lines:
        block_lines.extend(["Selected paper sections:", *chunk_lines])
    elif hit.snippet:
        block_lines.extend(["Selected paper excerpt:", hit.snippet[:MAX_RETRIEVAL_EXCERPT_CHARS]])

    return "\n".join(block_lines)


def _full_selected_paper_context_block(hit: SearchHit, chunk_overlap: int) -> str:
    block_lines = [
        f"Title: {hit.paper.title}",
        f"Year: {hit.paper.year}",
        f"Location: {hit.paper.location}",
    ]

    if hit.paper.abstract:
        block_lines.extend(
            [
                "Abstract:",
                hit.paper.abstract.strip(),
            ]
        )

    full_paper_text = _paper_full_text(hit.paper.id or 0, chunk_overlap)
    if full_paper_text:
        block_lines.extend(
            [
                "Full selected paper content:",
                full_paper_text,
            ]
        )
    elif hit.snippet:
        block_lines.extend(["Selected paper excerpt:", hit.snippet[:MAX_RETRIEVAL_EXCERPT_CHARS]])

    return "\n".join(block_lines)


def _retrieval_context_block(hit: SearchHit) -> str:
    return "\n".join(
        [
            f"Title: {hit.paper.title}",
            f"Year: {hit.paper.year}",
            f"Location: {hit.paper.location}",
            f"Excerpt: {hit.snippet[:MAX_RETRIEVAL_EXCERPT_CHARS]}",
        ]
    )


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


def _build_prompt(
    transcript: str,
    selected_scope_block: str,
    context_blocks: list[str],
    selected_paper_ids: list[int],
    use_full_selected_papers: bool,
) -> str:
    prompt_lines = [
        "You are a research assistant for DVCon conference papers.",
        "Answer only from the supplied paper context.",
        "If the context is insufficient, say so clearly.",
        "Cite the paper title inline when you make a claim.",
    ]

    if selected_paper_ids:
        prompt_lines.extend(
            [
                "If a selected paper scope is provided, treat references such as 'the selected papers', 'these papers', or 'the two papers' as that scope.",
                "For selected papers, use the richer paper content supplied for each selected paper before falling back to narrower excerpts.",
                "Do not describe the selected-paper context as excerpt-only unless the prompt explicitly labels it as an excerpt.",
            ]
        )
        if use_full_selected_papers:
            prompt_lines.append(
                "When full selected paper content is supplied for a paper, treat it as the authoritative paper text for that paper."
            )

    prompt_lines.extend(
        [
            "Conversation:",
            transcript,
            selected_scope_block,
            "Paper context:",
            "\n\n".join(context_blocks),
        ]
    )
    return "\n\n".join(prompt_lines)


def _selected_papers_fit_model_context(
    transcript: str,
    selected_scope_block: str,
    full_context_blocks: list[str],
    selected_paper_ids: list[int],
    settings: object,
) -> bool:
    prompt = _build_prompt(
        transcript=transcript,
        selected_scope_block=selected_scope_block,
        context_blocks=full_context_blocks,
        selected_paper_ids=selected_paper_ids,
        use_full_selected_papers=True,
    )
    available_input_tokens = _chat_model_context_window(settings) - _chat_output_reserve_tokens(settings)
    return _estimate_token_count(prompt) <= max(0, available_input_tokens)


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

    citations = [{"title": hit.paper.title, "year": str(hit.paper.year)} for hit in hits]
    use_full_selected_papers = False

    if selected_paper_ids:
        chunk_overlap = getattr(settings, "chunk_overlap", 200)
        full_context_blocks = [
            "\n".join(
                [
                    f"[Source {index}]",
                    _full_selected_paper_context_block(hit, chunk_overlap),
                ]
            )
            for index, hit in enumerate(hits, start=1)
        ]
        use_full_selected_papers = _selected_papers_fit_model_context(
            transcript=transcript,
            selected_scope_block=selected_scope_block,
            full_context_blocks=full_context_blocks,
            selected_paper_ids=selected_paper_ids,
            settings=settings,
        )

        context_blocks = (
            full_context_blocks
            if use_full_selected_papers
            else [
                "\n".join(
                    [
                        f"[Source {index}]",
                        _selected_paper_context_block(hit, question),
                    ]
                )
                for index, hit in enumerate(hits, start=1)
            ]
        )
    else:
        context_blocks = [
            "\n".join(
                [
                    f"[Source {index}]",
                    _retrieval_context_block(hit),
                ]
            )
            for index, hit in enumerate(hits, start=1)
        ]

    prompt = _build_prompt(
        transcript=transcript,
        selected_scope_block=selected_scope_block,
        context_blocks=context_blocks,
        selected_paper_ids=selected_paper_ids,
        use_full_selected_papers=use_full_selected_papers,
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
