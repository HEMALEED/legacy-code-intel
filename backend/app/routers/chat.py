"""
Chat router — POST /api/chat
Simple single-turn LLM call for the AI Assistant panel.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Send a message to the LLM and return the reply."""
    from app.agent.doc_agent import get_llm
    from langchain_core.messages import HumanMessage

    llm = get_llm()
    response = llm.invoke([HumanMessage(content=req.message)])
    reply = response.content if hasattr(response, "content") else str(response)
    return ChatResponse(reply=reply.strip())
