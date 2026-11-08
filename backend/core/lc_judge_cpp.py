"""Judge C++ LeetCode solutions: compile once, run each test in its own process."""

import asyncio
import json
import signal
import time

from api.schemas.leetcode import CompareMode, LCProblem, LCTestCase, RunTestsResponse, TestResult
from core.lc_cpp import BITS_STDCPP, RESULT_MARKER, build_driver
from core.lc_judge import PER_TEST_TIMEOUT_S, verdict
from sandbox.native import compile_cpp, run_binary

_PARALLEL = 4


def _signal_name(code: int) -> str:
    try:
        return {signal.SIGSEGV: "Segmentation fault (null pointer / out-of-bounds access?)",
                signal.SIGABRT: "Aborted", signal.SIGFPE: "Floating point exception (division by zero?)",
                signal.SIGXCPU: "CPU time limit", signal.SIGKILL: "Killed (memory limit?)"}[signal.Signals(-code)]
    except (ValueError, KeyError):
        return f"exit code {code}"


async def run_cpp_tests(
    problem: LCProblem, code: str, tests: list[LCTestCase], compare: CompareMode | None, memory_mb: int
) -> RunTestsResponse:
    mode = compare or problem.compare
    source, input_errors = build_driver(problem, code, [t.input for t in tests])
    binary, diagnostics = (None, "") if all(input_errors) else await compile_cpp(source, BITS_STDCPP)
    if binary is None and diagnostics:
        results = [TestResult(status="error", expected=t.expected, error="Compile Error") for t in tests]
        return RunTestsResponse(results=results, passed=0, total=len(tests), compare=mode,
                                error=f"Compile Error\n{diagnostics}")

    gate = asyncio.Semaphore(_PARALLEL)

    async def one(index: int, test: LCTestCase) -> TestResult:
        if input_errors[index]:
            problem_text = f"Invalid test input — {input_errors[index]}"
            return TestResult(status="error", expected=test.expected, error=problem_text)
        label = ", ".join(f"{p.name} = {ln.strip()}" for p, ln in zip(problem.params, test.input, strict=False)) \
            if not problem.design else "operations / arguments"
        async with gate:
            start = time.perf_counter()
            res = await run_binary(binary, str(index), PER_TEST_TIMEOUT_S, memory_mb)  # type: ignore[arg-type]
            ms = round((time.perf_counter() - start) * 1000, 2)  # includes process start-up
        stdout, _, payload = res.stdout.partition(f"\n{RESULT_MARKER}\n")
        base = {"label": label, "expected": test.expected, "stdout": stdout[:4000], "ms": ms}
        if res.timed_out:
            return TestResult(status="timeout", error="Time Limit Exceeded", **base)
        if res.returncode != 0 or not payload:
            detail = res.stderr.strip() or (_signal_name(res.returncode) if res.returncode < 0 else
                                            f"exited with code {res.returncode}")
            return TestResult(status="error", error=f"Runtime Error: {detail}", **base)
        try:
            output = json.loads(payload.strip())
        except json.JSONDecodeError:
            return TestResult(status="error", error=f"Unreadable output: {payload[:200]}", **base)
        status, note = verdict(output, test.expected, mode)
        return TestResult(status=status, output=json.dumps(output, separators=(",", ":")), error=note, **base)  # type: ignore[arg-type]

    results = await asyncio.gather(*(one(i, t) for i, t in enumerate(tests)))
    return RunTestsResponse(results=list(results), passed=sum(r.status == "passed" for r in results),
                            total=len(results), compare=mode)
