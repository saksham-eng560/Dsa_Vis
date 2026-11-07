"""The LLM-free half of the pipeline: detection → parsing → flowchart →
complexity → (Python) real execution trace. Always runs, so the app is useful
even with no model available, and gives the LLM grounded facts to explain.
"""

import re
from dataclasses import dataclass

from api.schemas.response import AnalysisResult, DryRun, Flowchart
from core.c_complexity_facts import c_facts
from core.c_flowchart import c_flowchart
from core.code_parser import detect_language, parse_python
from core.complexity_analyzer import estimate
from core.complexity_facts import python_facts
from core.config import Settings
from core.diagram_generator import python_flowchart
from core.entry_synth import synthesize_entry_call
from core.tracer import trace_python

_KNOWN = [
    (r"bubble", "Bubble Sort"), (r"insertion", "Insertion Sort"), (r"selection", "Selection Sort"),
    (r"merge_?sort|mergesort", "Merge Sort"), (r"quick_?sort|quicksort|partition", "Quick Sort"),
    (r"heap_?sort|heapify", "Heap Sort"), (r"counting_?sort", "Counting Sort"),
    (r"binary_?search|bsearch", "Binary Search"), (r"linear_?search", "Linear Search"),
    (r"\bbfs\b|breadth", "Breadth-First Search"), (r"\bdfs\b|depth_?first", "Depth-First Search"),
    (r"dijkstra", "Dijkstra's Algorithm"), (r"topo", "Topological Sort"),
    (r"fib", "Fibonacci"), (r"factorial", "Factorial (Recursion)"), (r"two_?sum|twosum", "Two Sum (Hash Map)"),
    (r"permut", "Permutations (Backtracking)"), (r"subset", "Subsets (Backtracking)"),
    (r"knapsack", "0/1 Knapsack (DP)"), (r"lcs|longest_?common", "Longest Common Subsequence (DP)"),
    (r"kadane|max_?subarray", "Kadane's Algorithm"), (r"reverse.*list|reverse_?linked", "Reverse Linked List"),
    (r"inorder|preorder|postorder|traversal", "Tree Traversal"), (r"palindrome", "Palindrome Check"),
    (r"gcd|euclid", "Euclidean GCD"), (r"prime|sieve", "Prime Sieve"), (r"hanoi", "Tower of Hanoi"),
]
_DS_HINTS = [
    (r"\bdeque\b|queue", "queue"), (r"\bstack\b|\.pop\(\)", "stack"), (r"heapq|priority", "heap"),
    (r"\{\}|dict\(|HashMap|unordered_map|new Map|map\[", "hash map"), (r"\.next\b|->next", "linked list"),
    (r"\.left\b|\.right\b|->left", "tree"), (r"graph|adj", "graph"), (r"\[\]|\blist\b|vector|Array", "array"),
]


def guess_algorithm(code: str) -> str:
    """Name a well-known algorithm from identifiers, else 'Custom Logic'."""
    lowered = code.lower()
    for pattern, name in _KNOWN:
        if re.search(r"(def|function|fn|func|void|int|static)\s+\w*" + pattern, lowered):
            return name
    return "Custom Logic"


def guess_structures(code: str, dry_run: DryRun) -> list[str]:
    found = [name for pattern, name in _DS_HINTS if re.search(pattern, code)]
    traced = {s.data_structure_state.type.replace("_", " ") for s in dry_run.steps if s.data_structure_state}
    return list(dict.fromkeys([*traced, *found]))[:6]


@dataclass(frozen=True)
class ProblemContext:
    """Run the code like a LeetCode judge: untraced prelude/setup, then `call`."""

    title: str
    prelude: str
    setup: str
    call: str
    label: str


async def run_static(
    code: str, language: str, entry_call: str | None, settings: Settings, problem: ProblemContext | None = None
) -> AnalysisResult:
    """Run every deterministic analysis and return a complete (LLM-free) result."""
    lang = "python" if problem else detect_language(code) if language == "auto" else language
    warnings: list[str] = []
    dry_run = DryRun()
    if lang == "python":
        tree = parse_python(code)
        if tree is None:
            try:
                compile(code, "<code>", "exec")
            except SyntaxError as exc:
                warnings.append(f"Python syntax error on line {exc.lineno}: {exc.msg}")
            flowchart, complexity = Flowchart(), estimate([])
        else:
            flowchart = python_flowchart(tree, code)
            complexity = estimate(python_facts(tree))
            if problem:
                entry_call = problem.call
            elif not entry_call:
                entry_call, warn = synthesize_entry_call(tree)
                if warn:
                    warnings.append(warn)
            dry_run = await trace_python(
                code, entry_call, max_steps=settings.trace_max_steps,
                timeout_s=settings.sandbox_timeout_s, memory_mb=settings.sandbox_memory_mb,
                prelude=problem.prelude if problem else "", setup=problem.setup if problem else "",
                input_label=problem.label if problem else None,
            )
            if dry_run.truncated:
                warnings.append(f"Dry run stopped after {settings.trace_max_steps} steps.")
    else:
        flowchart = c_flowchart(code)
        complexity = estimate(c_facts(code))
        warnings.append(f"Only Python is traced live — the {lang} dry run comes from the AI model (needs AI model).")

    algorithm = problem.title if problem else guess_algorithm(code)
    summary = (
        f"{algorithm if algorithm != 'Custom Logic' else 'This code'} — static analysis estimates "
        f"{complexity.time.worst} worst-case time and {complexity.space.complexity} extra space."
    )
    return AnalysisResult(
        language=lang,
        summary=summary,
        algorithm_name=algorithm,
        data_structures_used=guess_structures(code, dry_run),
        complexity=complexity,
        flowchart=flowchart,
        dry_run=dry_run,
        warnings=warnings,
    )
