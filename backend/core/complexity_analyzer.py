"""Static Big-O estimation.

Costs are modelled as `Cost(kind, poly, log)` meaning n^poly · log^log n for
kind 0, k^n for kind 1 and n! for kind 2. Language-specific extractors
(`complexity_facts.py`) reduce each function to `FuncFacts`; `estimate()`
combines them with master-theorem style rules. It is a heuristic — the LLM's
answer is preferred when available, and this acts as a cross-check/fallback.
"""

from dataclasses import dataclass, field

from api.schemas.response import Complexity, SpaceComplexity, TimeComplexity

_SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass(frozen=True, order=True)
class Cost:
    kind: int = 0  # 0 polynomial, 1 exponential, 2 factorial
    poly: int = 0
    log: int = 0
    base: int = 2  # exponential base (kind 1)

    def __mul__(self, other: "Cost") -> "Cost":
        if self.kind or other.kind:
            return max(self, other)
        return Cost(0, self.poly + other.poly, self.log + other.log)

    def notation(self) -> str:
        if self.kind == 2:
            return "O(n!)"
        if self.kind == 1:
            return f"O({self.base}ⁿ)"
        parts = []
        if self.poly:
            parts.append("n" if self.poly == 1 else "n" + str(self.poly).translate(_SUPERSCRIPT))
        if self.log:
            parts.append("log n" if self.log == 1 else f"log{str(self.log).translate(_SUPERSCRIPT)} n")
        return f"O({' '.join(parts) or '1'})"


ONE, LOG, N = Cost(), Cost(0, 0, 1), Cost(0, 1, 0)
NLOGN = Cost(0, 1, 1)


@dataclass
class FuncFacts:
    """Language-independent summary of one function (or top-level code)."""

    name: str
    loop_cost: Cost = ONE  # cost of the body ignoring recursion
    loop_depth: int = 0
    early_exit: bool = False  # return/break inside the outermost loop
    self_calls: int = 0  # recursive calls along a single path
    shrink: str | None = None  # "half" | "dec" | "split"
    memo: bool = False
    call_in_loop: bool = False
    alloc: Cost = ONE  # auxiliary memory allocated
    callees: list[tuple[str, Cost]] = field(default_factory=list)  # (helper, loop context)
    qualname: str = ""  # enclosing-function path, e.g. "permute.backtrack"
    graph: bool = False  # inner loop walks adjacency lists (amortised O(V + E))
    notes: list[str] = field(default_factory=list)


def _inline_callees(facts: list[FuncFacts]) -> None:
    """Fold the cost of called helper functions into each caller's body cost."""
    by_name = {f.name: f for f in facts}
    done: dict[str, Cost] = {}

    def total(f: FuncFacts, stack: frozenset[str]) -> Cost:
        if f.name in done:
            return done[f.name]
        cost = f.loop_cost
        for callee, ctx in f.callees:
            helper = by_name.get(callee)
            if helper and callee not in stack and callee != f.name:
                inner = total(helper, stack | {f.name})
                inner = _recursive_time(helper)[0] if helper.self_calls else inner
                if ctx * inner > cost:
                    cost = ctx * inner
                    f.notes.append(f"It calls `{callee}`, which costs {inner.notation()}.")
        done[f.name] = cost
        return cost

    for f in facts:
        f.loop_cost = total(f, frozenset())


def _recursive_time(f: FuncFacts) -> tuple[Cost, Cost, str]:
    """(worst, average, reason) for a recursive function."""
    body = f.loop_cost
    if f.graph:
        return N, N, "each vertex is visited once thanks to the visited check (graph traversal)"
    if f.shrink == "child":
        if f.self_calls >= 2:
            return N * body, N * body, "every node of the structure is visited exactly once"
        return N * body, LOG * body, "one recursive step down the tree per level (O(h): log n if balanced, n if skewed)"
    if f.call_in_loop and f.shrink == "dec":
        cost = Cost(2) if "perm" in (f.qualname or f.name).lower() else Cost(1)
        return cost, cost, "recursion inside a loop explores every combination (backtracking)"
    if f.self_calls == 1:
        if f.shrink == "half":
            cost = body if body.poly > 0 else LOG * body
            return cost, cost, "one recursive call on half the input per level"
        return N * body, N * body, "one recursive call shrinking the input by a constant"
    if f.shrink == "split":
        return N * N, NLOGN, "two recursive calls around a pivot — balanced on average, skewed in the worst case"
    if f.shrink == "half":
        if body.poly >= 1:
            cost = body * LOG if body.poly == 1 else body
        else:
            cost = N
        return cost, cost, f"{f.self_calls} recursive calls on halves (divide and conquer)"
    if f.memo:
        return N * body, N * body, "memoisation caches each sub-problem, so each state is solved once"
    cost = Cost(1, base=max(f.self_calls, 2))
    return cost, cost, f"{f.self_calls} recursive calls per invocation, each shrinking by a constant"


def estimate(facts: list[FuncFacts]) -> Complexity:
    """Combine per-function facts into an overall Complexity estimate."""
    if not facts:
        return Complexity(source="static")
    _inline_callees(facts)
    rows = []
    for f in facts:
        if f.self_calls:
            worst, avg, why = _recursive_time(f)
        else:
            worst = avg = f.loop_cost
            why = (f"{f.loop_depth} level(s) of loops over the input" if f.loop_depth
                   else "no loops over the input")
        rows.append((worst, avg, why, f))
    worst, avg, why, dom = max(rows, key=lambda r: r[0])
    if dom.graph and worst <= N:
        return _graph_complexity(dom)
    best = _best_case(dom, worst)
    space, space_why = _space(dom)
    explanation = (
        f"Dominant routine `{dom.name}`: {why}, giving {worst.notation()} in the worst case."
        + (f" An early exit allows {best.notation()} in the best case." if best < worst else "")
        + "".join(f" {n}" for n in dom.notes)
    )
    return Complexity(
        time=TimeComplexity(
            best=best.notation(), average=avg.notation(), worst=worst.notation(), explanation=explanation
        ),
        space=SpaceComplexity(complexity=space.notation(), explanation=space_why),
        source="static",
    )


def _best_case(f: FuncFacts, worst: Cost) -> Cost:
    if f.self_calls == 1 and f.shrink in ("half", "child"):
        return ONE  # e.g. binary search / BST lookup finds the target immediately
    if f.early_exit and worst.kind == 0 and worst > ONE:
        return Cost(0, worst.poly - 1, 0) if f.loop_depth >= 2 and worst.poly else ONE
    return worst


def _graph_complexity(f: FuncFacts) -> Complexity:
    """Traversals touching each vertex and edge once (BFS/DFS/topological sort)."""
    why = (f"`{f.name}` visits every vertex once and scans each adjacency list once, "
           "so the work is proportional to vertices plus edges.")
    return Complexity(
        time=TimeComplexity(best="O(V + E)", average="O(V + E)", worst="O(V + E)", explanation=why),
        space=SpaceComplexity(complexity="O(V)", explanation="visited set and frontier hold up to V vertices"),
        source="static",
    )


def _space(f: FuncFacts) -> tuple[Cost, str]:
    stack, why = ONE, "only a constant number of scalar variables"
    if f.self_calls:
        stack = LOG if f.shrink in ("half", "split") else N
        why = f"recursion depth {stack.notation()} on the call stack"
        if f.shrink == "child":
            why = "recursion depth equals the tree height h (O(n) worst case, O(log n) if balanced)"
    if f.memo and f.alloc < N:
        return max(stack, N), "memo table stores one entry per sub-problem"
    if f.alloc > stack:
        return f.alloc, f"auxiliary data structures sized {f.alloc.notation()}"
    return stack, why
