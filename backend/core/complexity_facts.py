"""Extract `FuncFacts` from Python ASTs for complexity estimation (C-family: `c_complexity_facts.py`)."""

import ast
import re

from core.complexity_analyzer import LOG, NLOGN, ONE, Cost, FuncFacts, N

HALVING_RX = re.compile(r"//\s*2|/\s*2\b|>>\s*1|\*=\s*2|/=\s*2|<<=\s*1|>>=\s*1|\bmid\b")
_LINEAR_CALLS = {"sum", "min", "max", "list", "set", "dict", "reversed", "count", "index", "join"}
_SORT_CALLS = {"sorted", "sort"}
_GRAPH_RX = re.compile(r"graph|adj|neighbo", re.I)
MEMO_RX = re.compile(r"lru_cache|\bcache\b|\bmemo\w*\b|\bdp\b")


def python_facts(tree: ast.Module) -> list[FuncFacts]:
    facts: list[FuncFacts] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fact = _py_function(child)
                fact.qualname = f"{prefix}{child.name}"
                facts.append(fact)
                visit(child, f"{fact.qualname}.")
            else:
                visit(child, prefix)

    visit(tree, "")
    top = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    if top:
        facts.append(_py_body("<module>", top, set()))
    return facts


def _py_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> FuncFacts:
    names = {fn.name}
    facts = _py_body(fn.name, fn.body, names)
    src = ast.unparse(fn)
    facts.memo = bool(MEMO_RX.search(src))
    if facts.loop_depth and _grows_map_in_loop(fn, src):
        facts.alloc = max(facts.alloc, N)
    calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and _recursive_name(c) == fn.name]
    if calls:
        facts.self_calls = max(1, _calls_on_path(fn.body, fn.name))
        arg_src = " ".join(ast.unparse(a) for c in calls for a in c.args)
        params = {a.arg for a in fn.args.args}
        facts.shrink = shrink_kind(arg_src, params, len(calls))
    return facts


_MAP_INIT_RX = re.compile(r"(\w+)\s*=\s*(?:\{\}|dict\(|defaultdict\(|Counter\(|set\(\))")


def _grows_map_in_loop(fn: ast.AST, src: str) -> bool:
    """`seen[x] = …` inside a loop where `seen` started as an empty dict."""
    maps = set(_MAP_INIT_RX.findall(src))
    for loop in (n for n in ast.walk(fn) if isinstance(n, (ast.For, ast.While))):
        for node in ast.walk(loop):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id in maps
                    for t in node.targets):
                return True
    return False


def shrink_kind(arg_src: str, params: set[str], n_calls: int) -> str:
    if re.search(r"(\.|->)(left|right|children|child|next)\b|\[\s*['\"](left|right)['\"]\s*\]", arg_src):
        return "child"  # recursion over tree children / list nodes
    if HALVING_RX.search(arg_src):
        return "half"
    pivots = set(re.findall(r"\b(\w+)\s*[-+]\s*1\b", arg_src)) - params
    if n_calls >= 2 and pivots:
        return "split"
    return "dec"


def _recursive_name(call: ast.Call) -> str:
    """Name if `call` could be self-recursion: `f(...)` or `self.f(...)` — not `stack.pop()`."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("self", "cls"):
        return f.attr
    return ""


def _call_name(call: ast.Call) -> str:
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""


def _calls_on_path(stmts: list[ast.stmt], name: str) -> int:
    """Recursive calls along one execution path (if/else branches are exclusive)."""
    total = 0
    for s in stmts:
        if isinstance(s, ast.If):
            total += max(_calls_on_path(s.body, name), _calls_on_path(s.orelse, name)) + sum(
                1 for c in ast.walk(s.test) if isinstance(c, ast.Call) and _recursive_name(c) == name)
        elif isinstance(s, (ast.For, ast.While, ast.With, ast.Try)):
            total += _calls_on_path(getattr(s, "body", []), name)
        else:
            total += sum(1 for c in ast.walk(s) if isinstance(c, ast.Call) and _recursive_name(c) == name)
    return total


def _py_body(name: str, body: list[ast.stmt], self_names: set[str]) -> FuncFacts:
    facts = FuncFacts(name=name)
    facts.loop_cost, facts.loop_depth = _py_cost(body, ONE, 0, facts, self_names)
    return facts


def _loop_factor(loop: ast.For | ast.AsyncFor | ast.While, facts: FuncFacts) -> Cost:
    if isinstance(loop, ast.While):
        text = ast.unparse(loop)
        return LOG if HALVING_RX.search(text) else N
    it = loop.iter
    if isinstance(it, ast.Subscript) and _GRAPH_RX.search(ast.unparse(it.value)):
        facts.graph = True
        return ONE  # amortised: each adjacency list is scanned once overall
    if isinstance(it, ast.Call) and _call_name(it) == "range" and all(
            isinstance(a, ast.Constant) for a in it.args):
        return ONE
    return N


def _py_cost(stmts: list[ast.stmt], ctx: Cost, depth: int, facts: FuncFacts,
             self_names: set[str]) -> tuple[Cost, int]:
    """Worst cost of `stmts` executed `ctx` times; tracks max loop depth."""
    best, max_depth = ctx, depth
    for s in stmts:
        if isinstance(s, (ast.For, ast.AsyncFor, ast.While)):
            inner_ctx = ctx * _loop_factor(s, facts)
            if depth == 0 and any(isinstance(n, (ast.Return, ast.Break)) for n in ast.walk(s)):
                facts.early_exit = True
            if any(isinstance(c, ast.Call) and _recursive_name(c) in self_names for c in ast.walk(s)):
                facts.call_in_loop = True
            cost, d = _py_cost(s.body, inner_ctx, depth + 1, facts, self_names)
            best, max_depth = max(best, cost), max(max_depth, d)
            continue
        nested = [b for f in ("body", "orelse", "finalbody") for b in [getattr(s, f, None)] if b]
        nested += [h.body for h in getattr(s, "handlers", [])]
        for block in nested:
            cost, d = _py_cost(block, ctx, depth, facts, self_names)
            best, max_depth = max(best, cost), max(max_depth, d)
        best = max(best, ctx * _expr_cost(s, facts, ctx, self_names))
    return best, max_depth


def _expr_cost(s: ast.stmt, facts: FuncFacts, ctx: Cost, self_names: set[str]) -> Cost:
    """Cost of built-in operations in a simple statement (sorting, slicing …)."""
    if isinstance(s, (ast.For, ast.While, ast.If, ast.With, ast.Try, ast.FunctionDef)):
        return ONE
    cost = ONE
    for node in ast.walk(s):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in _SORT_CALLS:
                cost = max(cost, NLOGN)
            elif name in _LINEAR_CALLS and node.args and (name not in ("min", "max") or len(node.args) == 1):
                cost = max(cost, N)
            elif name and name not in self_names:
                facts.callees.append((name, ctx))
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            cost = max(cost, N)
            facts.alloc = max(facts.alloc, N)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            cost = max(cost, N)
            nested = isinstance(node.elt if hasattr(node, "elt") else None, ast.ListComp)
            facts.alloc = max(facts.alloc, N * N if nested else N)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) and isinstance(node.left, ast.List):
            facts.alloc = max(facts.alloc, N)
    if ctx > ONE and isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and _call_name(s.value) in (
            "append", "add", "appendleft", "heappush"):
        facts.alloc = max(facts.alloc, ctx if ctx.poly <= 2 else N)
    return cost
