"""Run a user's solution against LeetCode-style test cases in the sandbox."""

import json
from pathlib import Path
from typing import Any

from api.schemas.leetcode import CompareMode, LCProblem, LCTestCase, RunTestsResponse, TestResult
from core.lc_runtime import PRELUDE, PreparedTest, TestInputError, outputs_match, parse_value, prepare_test
from sandbox.executor import run_python

_JUDGE = (Path(__file__).parent.parent / "sandbox" / "judge.py").read_text()
PER_TEST_TIMEOUT_S = 2.0
MAX_TOTAL_TIMEOUT_S = 30.0


def _dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _verdict(output: Any, expected: str | None, mode: CompareMode) -> tuple[str, str | None]:
    """(status, error) for a successfully returned value."""
    if expected is None or not expected.strip():
        return "ran", None
    try:
        want = parse_value(expected, "expected output")
    except TestInputError:
        return "ran", "Expected output isn't valid JSON, so it wasn't compared."
    return ("passed", None) if outputs_match(output, want, mode) else ("failed", None)


async def run_tests(
    problem: LCProblem, code: str, tests: list[LCTestCase], compare: CompareMode | None, memory_mb: int
) -> RunTestsResponse:
    """Judge `code` on `tests`; invalid inputs are reported per test, not fatally."""
    mode = compare or problem.compare
    prepared: list[PreparedTest | TestInputError] = []
    for test in tests:
        try:
            prepared.append(prepare_test(problem, test.input))
        except TestInputError as exc:
            prepared.append(exc)
    runnable = [p for p in prepared if isinstance(p, PreparedTest)]

    raw: dict[str, Any] = {"fatal": None, "results": []}
    if runnable:
        payload = json.dumps({"code": code, "prelude": PRELUDE, "timeout": PER_TEST_TIMEOUT_S,
                              "tests": [{"setup": p.setup, "call": p.call} for p in runnable]})
        budget = min(PER_TEST_TIMEOUT_S * len(runnable) + 3, MAX_TOTAL_TIMEOUT_S)
        result = await run_python(_JUDGE, payload, budget, memory_mb)
        if result.timed_out:
            raw["fatal"] = "Time Limit Exceeded (the whole run took too long)."
        else:
            try:
                raw = json.loads(result.stdout)
            except json.JSONDecodeError:
                tail = result.stderr.strip().splitlines()[-1:] or ["sandbox crashed"]
                raw["fatal"] = f"Sandbox error: {tail[0]}"

    results: list[TestResult] = []
    outputs = iter(raw.get("results") or [])
    for test, prep in zip(tests, prepared, strict=True):
        if isinstance(prep, TestInputError):
            results.append(TestResult(status="error", error=f"Invalid test input — {prep}", expected=test.expected))
            continue
        got = next(outputs, None)
        if got is None:  # fatal error before this test ran
            results.append(TestResult(status="error", label=prep.label, expected=test.expected,
                                      error=raw.get("fatal") or "Not run"))
            continue
        base = {"label": prep.label, "expected": test.expected, "stdout": got["stdout"], "ms": got["ms"]}
        if got["error"]:
            status = "timeout" if got["error"].startswith("Time Limit") else "error"
            results.append(TestResult(status=status, error=got["error"], **base))
            continue
        status, note = _verdict(got["output"], test.expected, mode)
        results.append(TestResult(status=status, output=_dump(got["output"]), error=note, **base))  # type: ignore[arg-type]

    fatal = raw.get("fatal")
    if fatal and not problem.design and "class Solution" not in code:
        fatal += " — LeetCode solutions must define `class Solution`."
    return RunTestsResponse(
        results=results, passed=sum(r.status == "passed" for r in results), total=len(results),
        compare=mode, error=fatal,
    )
