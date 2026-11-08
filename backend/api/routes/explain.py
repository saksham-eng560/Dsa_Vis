"""POST /api/explain — plain-English (or ELI5) explanation."""

from fastapi import APIRouter, Depends

from api.deps import get_service
from api.schemas.request import ExplainRequest
from api.schemas.response import Explanation
from core.analysis_service import AnalysisService

router = APIRouter()


@router.post("/explain", response_model=Explanation)
async def explain(req: ExplainRequest, service: AnalysisService = Depends(get_service)) -> Explanation:
    """Explain the code; `eli5=true` asks for a child-friendly version."""
    return await service.explain(req)
