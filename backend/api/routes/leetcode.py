"""LeetCode problem mode: browse/search/fetch problems and judge solutions."""

from fastapi import APIRouter, Depends, Query

from api.deps import get_service
from api.schemas.leetcode import LCProblem, LCSummary, RunTestsRequest, RunTestsResponse
from core.analysis_service import AnalysisService
from core.lc_judge import run_tests
from core.lc_judge_cpp import run_cpp_tests
from core.lc_problem import ProblemNotFoundError, catalog_summaries, search_catalog

router = APIRouter(prefix="/leetcode")


@router.get("/problems", response_model=list[LCSummary])
async def list_problems() -> list[LCSummary]:
    """Problems bundled for offline use (any other problem is fetched on demand)."""
    return catalog_summaries()


@router.get("/search", response_model=list[LCSummary])
async def search(
    q: str = Query(min_length=1, max_length=100), service: AnalysisService = Depends(get_service)
) -> list[LCSummary]:
    """Search suggestions: bundled matches first, then leetcode.com (best effort, works offline)."""
    found = {s.slug: s for s in search_catalog(q)}
    try:
        for s in await service.leetcode.search(q):
            found.setdefault(s.slug, s)
    except ProblemNotFoundError:
        pass  # offline: bundled results only
    return list(found.values())[:10]


@router.get("/problems/{ref}", response_model=LCProblem)
async def get_problem(ref: str, service: AnalysisService = Depends(get_service)) -> LCProblem:
    """Problem by number, slug or title: statement, signature, starter code, examples."""
    return await service.leetcode.get(ref)


@router.post("/run", response_model=RunTestsResponse)
async def run(req: RunTestsRequest, service: AnalysisService = Depends(get_service)) -> RunTestsResponse:
    """Run the solution (Python or C++) on each test case and judge it."""
    problem = await service.leetcode.get(req.problem)
    judge = run_cpp_tests if req.language == "cpp" else run_tests
    return await judge(problem, req.code, req.tests, req.compare, service.settings.sandbox_memory_mb)
