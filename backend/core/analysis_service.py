"""Orchestrates the full analysis pipeline. Injected into routes via FastAPI deps.

    code ─► static pipeline (parse, flowchart, complexity, trace) ─► partial result
                                  │
                                  └─► LLM (streamed) ─► JSON repair ─► per-field merge ─► final result
"""

from collections.abc import AsyncIterator
from typing import Any

import httpx

from api.schemas.request import AnalyzeRequest, CodeRequest, ExplainRequest
from api.schemas.response import AnalysisResult, Explanation
from core.cache import LRUCache, cache_key
from core.config import Settings
from core.json_utils import extract_json
from core.lc_problem import LeetCodeClient
from core.lc_runtime import PRELUDE, prepare_test
from core.llm_engine import LLMClient, LLMUnavailableError, complete
from core.llm_merge import merge_analysis, merge_explanation
from core.static_pipeline import ProblemContext, run_static
from models.knowledge import enrich_offline
from models.prompts import SYSTEM_PROMPT, analysis_prompt, explain_prompt

Event = dict[str, Any]


class CodeTooLargeError(ValueError):
    """Input exceeds the configured size limit."""


class AnalysisService:
    def __init__(self, settings: Settings, llm: LLMClient, leetcode: LeetCodeClient) -> None:
        self.settings = settings
        self.llm = llm
        self.leetcode = leetcode
        self.cache: LRUCache[AnalysisResult] = LRUCache(settings.cache_size)
        self.explain_cache: LRUCache[Explanation] = LRUCache(settings.cache_size)

    def _check(self, req: CodeRequest) -> None:
        if len(req.code) > self.settings.max_code_chars:
            raise CodeTooLargeError(f"Code exceeds {self.settings.max_code_chars} characters.")

    async def static(self, req: CodeRequest) -> AnalysisResult:
        """Deterministic analysis only (used by the focused endpoints)."""
        self._check(req)
        if isinstance(req, AnalyzeRequest) and req.problem and req.language not in ("auto", "python"):
            return await self._static_native_problem(req)
        context = await self._problem_context(req) if isinstance(req, AnalyzeRequest) else None
        result = await run_static(req.code, req.language, req.entry_call, self.settings, context)
        return enrich_offline(result)

    async def _static_native_problem(self, req: AnalyzeRequest) -> AnalysisResult:
        """LeetCode mode in C++: static analysis now, AI dry run on the chosen test input."""
        problem = await self.leetcode.get(req.problem or "")
        lines = req.test_input or (problem.examples[0].input if problem.examples else [])
        names = ["operations", "arguments"] if problem.design else [p.name for p in problem.params]
        label = ", ".join(f"{n} = {v.strip()}" for n, v in zip(names, lines, strict=False))
        result = await run_static(req.code, req.language, None, self.settings)
        return result.model_copy(update={
            "algorithm_name": f"{problem.id}. {problem.title}",
            "dry_run": result.dry_run.model_copy(update={"input_example": label}),
        })

    async def _problem_context(self, req: AnalyzeRequest) -> ProblemContext | None:
        """Resolve LeetCode mode: which problem and which test case drives the dry run."""
        if not req.problem:
            return None
        problem = await self.leetcode.get(req.problem)
        lines = req.test_input or (problem.examples[0].input if problem.examples else [])
        test = prepare_test(problem, lines)
        return ProblemContext(f"{problem.id}. {problem.title}", PRELUDE, test.setup, test.call, test.label)

    async def analyze(self, req: AnalyzeRequest) -> AnalysisResult:
        """Full analysis; returns the final event of `analyze_stream`."""
        final: AnalysisResult | None = None
        async for event in self.analyze_stream(req):
            if event["event"] == "result":
                final = event["data"]
        assert final is not None
        return final

    async def analyze_stream(self, req: AnalyzeRequest) -> AsyncIterator[Event]:
        """Yield progress events: stage → partial → token* → result."""
        self._check(req)
        key = cache_key("analyze", req.code, req.language, req.entry_call, req.use_llm, req.problem, req.test_input)
        if cached := self.cache.get(key):
            yield {"event": "result", "data": cached}
            return

        yield {"event": "stage", "data": {"stage": "static", "message": "Parsing and tracing code"}}
        static = await self.static(req)
        yield {"event": "partial", "data": static}

        result = static
        if req.use_llm and await self.llm.available():
            yield {"event": "stage", "data": {"stage": "llm", "message": f"Asking {self.llm.model}"}}
            prompt = analysis_prompt(
                req.code, static.language, _hints(static), need_dry_run=static.dry_run.source != "trace"
            )
            chunks: list[str] = []
            try:
                async for chunk in self.llm.stream(SYSTEM_PROMPT, prompt):
                    chunks.append(chunk)
                    if len(chunks) % 8 == 0:
                        yield {"event": "token", "data": {"chars": sum(map(len, chunks))}}
                data = extract_json("".join(chunks))
                if data is None:
                    result = _warn(static, "The AI response was not valid JSON; showing static analysis.")
                else:
                    result = merge_analysis(static, data)
            except (LLMUnavailableError, httpx.HTTPError, OSError, ValueError) as exc:
                result = _warn(static, f"AI model unavailable ({exc}); showing static analysis.")
        elif req.use_llm:
            result = _warn(static, "No AI model reachable — showing static analysis only.")

        self.cache.set(key, result)
        yield {"event": "result", "data": result}

    async def explain(self, req: ExplainRequest) -> Explanation:
        """Explanation (optionally ELI5); static fallback when no LLM."""
        self._check(req)
        key = cache_key("explain", req.code, req.language, req.eli5)
        if cached := self.explain_cache.get(key):
            return cached
        static = await self.static(req)
        fallback = Explanation(
            summary=static.summary, algorithm_name=static.algorithm_name,
            key_concepts=static.key_concepts, edge_cases=static.edge_cases,
            optimizations=static.optimizations, related_algorithms=static.related_algorithms, eli5=req.eli5,
        )
        result = fallback
        if await self.llm.available():
            try:
                raw = await complete(self.llm, SYSTEM_PROMPT, explain_prompt(req.code, static.language, req.eli5))
                if data := extract_json(raw):
                    result = merge_explanation(fallback, data, req.eli5)
            except (LLMUnavailableError, httpx.HTTPError, OSError, ValueError):
                pass
        self.explain_cache.set(key, result)
        return result


def _warn(result: AnalysisResult, message: str) -> AnalysisResult:
    return result.model_copy(update={"warnings": [*result.warnings, message]})


def _hints(static: AnalysisResult) -> str:
    """Compact static facts handed to the LLM as grounding."""
    cx = static.complexity.time
    lines = [
        f"- Recognised pattern / problem: {static.algorithm_name}",
        f"- Estimated time: best {cx.best}, average {cx.average}, worst {cx.worst}",
        f"- Estimated space: {static.complexity.space.complexity}",
    ]
    if static.dry_run.steps:
        lines.append(f"- Executed {len(static.dry_run.steps)} traced steps; output: "
                     f"{static.dry_run.steps[-1].output_so_far[-200:]!r}")
    if static.dry_run.source != "trace" and static.dry_run.input_example:
        lines.append(f"- For dry_run, trace exactly this input: {static.dry_run.input_example}")
    if static.dry_run.error:
        lines.append(f"- Runtime error when executed: {static.dry_run.error}")
    return "\n".join(lines)
