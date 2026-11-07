"""FastAPI dependency providers (overridable in tests)."""

from fastapi import Request

from core.analysis_service import AnalysisService


def get_service(request: Request) -> AnalysisService:
    """The process-wide AnalysisService created in the app lifespan."""
    return request.app.state.service
