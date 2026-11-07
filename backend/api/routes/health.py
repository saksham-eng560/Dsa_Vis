"""GET /api/health — liveness plus LLM availability."""

from fastapi import APIRouter, Depends

from api.deps import get_service
from api.schemas.response import HealthStatus
from core.analysis_service import AnalysisService

router = APIRouter()
VERSION = "1.0.0"


@router.get("/health", response_model=HealthStatus)
async def health(service: AnalysisService = Depends(get_service)) -> HealthStatus:
    """Report service status and whether an LLM backend is reachable."""
    available = await service.llm.available()
    return HealthStatus(
        version=VERSION,
        llm_provider=service.llm.name,
        llm_model=service.llm.model,
        llm_available=available,
    )
