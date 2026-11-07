"""LeetCode problem mode: browse/fetch problems and judge solutions on test cases."""

from fastapi import APIRouter, Depends

from api.deps import get_service
from api.schemas.leetcode import LCProblem, LCSummary, RunTestsRequest, RunTestsResponse
from core.analysis_service import AnalysisService
from core.lc_judge import run_tests
from core.lc_problem import catalog_summaries

router = APIRouter(prefix="/leetcode")


@router.get("/problems", response_model=list[LCSummary])
async def list_problems() -> list[LCSummary]:
    """Problems bundled for offline use (any other problem is fetched on demand)."""
    return catalog_summaries()


@router.get("/problems/{ref}", response_model=LCProblem)
async def get_problem(ref: str, service: AnalysisService = Depends(get_service)) -> LCProblem:
    """Problem by number, slug or title: statement, signature, starter code, examples."""
    return await service.leetcode.get(ref)


@router.post("/run", response_model=RunTestsResponse)
async def run(req: RunTestsRequest, service: AnalysisService = Depends(get_service)) -> RunTestsResponse:
    """Run the solution on each test case and judge it against the expected output."""
    problem = await service.leetcode.get(req.problem)
    return await run_tests(problem, req.code, req.tests, req.compare, service.settings.sandbox_memory_mb)
