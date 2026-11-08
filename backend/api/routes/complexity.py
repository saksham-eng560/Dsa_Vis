"""POST /api/complexity — Big-O estimate."""

from fastapi import APIRouter, Depends

from api.deps import get_service
from api.schemas.request import CodeRequest
from api.schemas.response import Complexity
from core.analysis_service import AnalysisService

router = APIRouter()


@router.post("/complexity", response_model=Complexity)
async def complexity(req: CodeRequest, service: AnalysisService = Depends(get_service)) -> Complexity:
    """Static time/space complexity estimate with reasoning."""
    return (await service.static(req)).complexity
