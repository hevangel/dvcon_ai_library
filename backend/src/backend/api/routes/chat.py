from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ChatResponse, ChatRequest
from backend.services.chat import answer_question


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_with_papers(payload: ChatRequest) -> ChatResponse:
    try:
        answer = answer_question(
            messages=[message.model_dump() for message in payload.messages],
            selected_paper_ids=payload.selected_paper_ids,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        answer=answer.answer,
        citations=answer.citations,
        scope_paper_ids=answer.scope_paper_ids,
    )
