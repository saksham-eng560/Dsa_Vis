"""Native C++ dry runs: instrument → compile → run in the sandbox → build steps.

The runtime (`sandbox/cpp_trace_runtime.hpp`) emits the same raw step format
as the Python harness, so `tracer.build_steps` turns both into identical
visualisations (arrays, maps, stacks, queues, linked lists, trees, graphs).
"""

import json
import re
from pathlib import Path

from api.schemas.leetcode import LCProblem
from api.schemas.response import DryRun
from core.call_tree import build_call_tree
from core.cpp_instrument import instrument
from core.lc_cpp import BITS_STDCPP, PRELUDE, RESULT_MARKER, build_driver
from core.lc_runtime import TestInputError
from core.tracer import build_steps
from sandbox.native import compile_cpp, find_compiler, run_binary

_RUNTIME = (Path(__file__).parent.parent / "sandbox" / "cpp_trace_runtime.hpp").read_text()
_TRACE_RX = re.compile(r"\n@@CODELENS_TRACE@@\n(.*?)\n@@CODELENS_TRACE_END@@\n", re.S)
_HEAP_RX = re.compile(r"priority_queue\s*<[^;]*>\s+(\w+)")
TRACE_TIMEOUT_S = 6.0


class NativeTraceUnavailable(RuntimeError):
    """Native tracing isn't possible (no compiler / unsupported code) — fall back to the AI trace."""


def _max_steps_line(max_steps: int) -> str:
    return f"\nstatic int codelens_cfg_ = (codelens_rt::ctx().max_steps = {max_steps}, 0);\n"


async def _compile_or_explain(source: str, plain_source: str) -> Path:
    binary, diagnostics = await compile_cpp(source, BITS_STDCPP, "-O0")
    if binary is not None:
        return binary
    # Did the user's code itself fail, or only our instrumentation?
    plain, plain_diag = await compile_cpp(plain_source, BITS_STDCPP, "-O0")
    if plain is None:
        raise CompileError(plain_diag or diagnostics)
    raise NativeTraceUnavailable("instrumentation not supported for this code")


class CompileError(RuntimeError):
    pass


async def _run(source: str, plain: str, code: str, label: str, memory_mb: int) -> DryRun:
    if find_compiler() is None:
        raise NativeTraceUnavailable("no C++ compiler")
    try:
        binary = await _compile_or_explain(source, plain)
    except CompileError as exc:
        return DryRun(source="trace", input_example=label, error=f"Compile Error\n{exc}")
    res = await run_binary(binary, "0", TRACE_TIMEOUT_S, memory_mb)
    m = _TRACE_RX.search(res.stderr)
    if res.timed_out or not m:
        user_err = res.stderr.split("\n@@CODELENS_TRACE@@", 1)[0].strip()  # never show raw trace data
        why = ("Execution timed out (possible infinite loop)." if res.timed_out
               else user_err[:300] or "The program stopped before the trace could be recorded.")
        return DryRun(source="trace", input_example=label, error=why)
    doc = json.loads(m.group(1))
    stdout, _, result = res.stdout.partition(f"\n{RESULT_MARKER}\n")
    steps = build_steps(doc["steps"], stdout, code, frozenset(_HEAP_RX.findall(code)))
    error = doc.get("error") or (res.stderr[: m.start()].strip() or None)
    if result.strip() and steps:
        steps[-1].output_so_far += f"\n→ result = {result.strip()}"
    return DryRun(input_example=label, steps=steps, source="trace", truncated=bool(doc.get("truncated")),
                  error=error, call_tree=build_call_tree(doc["steps"], null="null"))


async def trace_cpp_program(code: str, *, max_steps: int, memory_mb: int) -> DryRun:
    """Trace a full C++ program (with its own `main`)."""
    if not re.search(r"\bint\s+main\s*\(", code):
        raise NativeTraceUnavailable("no main() to run")
    inst = instrument(code)
    if inst is None:
        raise NativeTraceUnavailable("nothing to instrument")
    head = _RUNTIME + _max_steps_line(max_steps)
    traced = f'{head}#line 1 "solution.cpp"\n{inst}\n'
    plain = f'#include <bits/stdc++.h>\n#line 1 "solution.cpp"\n{code}\n'
    return await _run(traced, plain, code, "", memory_mb)


async def trace_cpp_problem(
    problem: LCProblem, code: str, lines: list[str], label: str, *, max_steps: int, memory_mb: int
) -> DryRun:
    """Trace a LeetCode C++ solution on one test case."""
    inst = instrument(code)
    if inst is None:
        raise NativeTraceUnavailable("nothing to instrument")
    source, errors = build_driver(problem, inst, [lines])
    if errors[0]:
        raise TestInputError(errors[0])
    plain, _ = build_driver(problem, code, [lines])
    source = source.replace(PRELUDE, PRELUDE + "\n" + _RUNTIME + _max_steps_line(max_steps), 1)
    return await _run(source, plain, code, label, memory_mb)
