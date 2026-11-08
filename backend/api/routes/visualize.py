"""POST /api/visualize — flowchart (visualisation script) for the code."""

from fastapi import APIRouter, Depends

from api.deps import get_service
from api.schemas.request import CodeRequest
from api.schemas.response import Flowchart
from core.analysis_service import AnalysisService

router = APIRouter()


@router.post("/visualize", response_model=Flowchart)
async def visualize(req: CodeRequest, service: AnalysisService = Depends(get_service)) -> Flowchart:
    """Return the control-flow diagram (nodes + edges, grouped by function)."""
    return (await service.static(req)).flowchart
