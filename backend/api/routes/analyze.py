"""POST /api/analyze (JSON) and POST /api/analyze/stream (Server-Sent Events)."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import get_service
from api.schemas.request import AnalyzeRequest
from api.schemas.response import AnalysisResult
from core.analysis_service import AnalysisService

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(req: AnalyzeRequest, service: AnalysisService = Depends(get_service)) -> AnalysisResult:
    """Run the whole pipeline and return the merged result."""
    return await service.analyze(req)


@router.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest, service: AnalysisService = Depends(get_service)) -> StreamingResponse:
    """Stream pipeline progress as SSE: `stage`, `partial`, `token`, `result`, `error`, `done`."""
    service._check(req)  # fail fast with 413 before the stream starts

    async def events() -> AsyncIterator[str]:
        try:
            async for event in service.analyze_stream(req):
                data = event["data"]
                payload = data.model_dump() if isinstance(data, BaseModel) else data
                yield f"event: {event['event']}\ndata: {json.dumps(payload)}\n\n"
        except Exception as exc:  # surface failures to the client instead of a dead stream
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
