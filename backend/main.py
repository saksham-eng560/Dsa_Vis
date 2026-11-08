"""CodeLens FastAPI application entry point.

Run: `uvicorn main:app --reload` from the `backend/` directory.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import analyze, chat, complexity, dryrun, explain, health, leetcode, visualize
from core.analysis_service import AnalysisService, CodeTooLargeError
from core.config import Settings, get_settings
from core.lc_problem import LeetCodeClient, ProblemNotFoundError
from core.lc_runtime import TestInputError
from core.llm_engine import LLMClient, build_llm
from core.rate_limit import RateLimitMiddleware


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    """App factory — tests inject settings and a fake LLM."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient() as http:
            lc = LeetCodeClient(http, Path(settings.leetcode_cache_dir))
            app.state.service = AnalysisService(settings, llm or build_llm(settings, http), lc)
            yield

    app = FastAPI(title="CodeLens API", version=health.VERSION, lifespan=lifespan)
    app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_minute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(CodeTooLargeError)
    async def too_large(_: Request, exc: CodeTooLargeError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=413)

    @app.exception_handler(ProblemNotFoundError)
    async def not_found(_: Request, exc: ProblemNotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(TestInputError)
    async def bad_test(_: Request, exc: TestInputError) -> JSONResponse:
        return JSONResponse({"detail": f"Invalid test input — {exc}"}, status_code=422)

    for module in (health, analyze, visualize, dryrun, complexity, explain, leetcode, chat):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    cfg = get_settings()
    uvicorn.run("main:app", host=cfg.app_host, port=cfg.app_port, reload=cfg.debug)
