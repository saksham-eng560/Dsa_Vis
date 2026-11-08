"""POST /api/dryrun — step-by-step execution trace."""

from fastapi import APIRouter, Depends

from api.deps import get_service
from api.schemas.request import CodeRequest
from api.schemas.response import DryRun
from core.analysis_service import AnalysisService

router = APIRouter()


@router.post("/dryrun", response_model=DryRun)
async def dryrun(req: CodeRequest, service: AnalysisService = Depends(get_service)) -> DryRun:
    """Trace Python execution in the sandbox (other languages need /api/analyze + LLM)."""
    return (await service.static(req)).dry_run
