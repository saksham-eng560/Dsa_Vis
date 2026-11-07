"""POST /api/chat/stream — ask the tutor questions about your code (streamed text)."""

import json
from collections.abc import AsyncIterator
from typing import Literal

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.deps import get_service
from core.analysis_service import AnalysisService
from core.llm_engine import LLMUnavailableError
from models.prompts import CHAT_SYSTEM, chat_prompt

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    code: str = Field(default="", max_length=50_000)
    language: str = Field(default="", max_length=20)
    problem: str | None = Field(default=None, max_length=200)
    context: str = Field(default="", max_length=6000)  # current step, complexity, test result…


async def _context(req: ChatRequest, service: AnalysisService) -> str:
    parts = []
    if req.problem:
        try:
            p = await service.leetcode.get(req.problem)
            parts.append(f"LeetCode {p.id}. {p.title} ({p.difficulty})\n{p.description[:2500]}")
        except Exception:  # noqa: BLE001 - context is best effort
            parts.append(f"LeetCode problem: {req.problem}")
    if req.code.strip():
        numbered = "\n".join(f"{i + 1:>3} | {ln}" for i, ln in enumerate(req.code.splitlines()[:300]))
        parts.append(f"Student's {req.language or 'code'}:\n{numbered}")
    if req.context.strip():
        parts.append(req.context.strip())
    return "\n\n".join(parts) or "(no code yet)"


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, service: AnalysisService = Depends(get_service)) -> StreamingResponse:
    """Stream the tutor's answer as SSE `token` events, then `done` (or `error`)."""

    async def events() -> AsyncIterator[str]:
        if not await service.llm.available():
            yield "event: error\ndata: " + json.dumps({"detail": "The AI model isn't running. Start Ollama "
                                                       "(./start.sh does it) to chat about your code."}) + "\n\n"
            yield "event: done\ndata: {}\n\n"
            return
        history = [(m.role, m.content) for m in req.messages[:-1]]
        prompt = chat_prompt(await _context(req, service), history, req.messages[-1].content)
        try:
            async for chunk in service.llm.stream(CHAT_SYSTEM, prompt, json_mode=False):
                yield "event: token\ndata: " + json.dumps({"text": chunk}) + "\n\n"
        except (LLMUnavailableError, httpx.HTTPError, OSError) as exc:
            yield "event: error\ndata: " + json.dumps({"detail": f"The AI model stopped responding ({exc})."}) + "\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
