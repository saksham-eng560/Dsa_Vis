"""Synthesise a sample call for Python code that only *defines* functions.

Users often paste just `def bubble_sort(arr): ...`. Executing that traces
nothing, so we pick the entry function (one not called by any other) and build
arguments from parameter names / annotations.
"""

import ast

_SORTED = [1, 3, 5, 7, 9, 11, 13]
_UNSORTED = [5, 2, 8, 1, 9, 3]
_GRAPH = {0: [1, 2], 1: [3], 2: [3, 4], 3: [5], 4: [5], 5: []}
_GRID = [[1, 3, 1], [1, 5, 1], [4, 2, 1]]


def _guess(param: str, annotation: str, func: str, params: list[str]) -> object:
    """Plausible argument for one parameter."""
    p, f = param.lower(), func.lower()
    searching = "search" in f or "find" in f or "target" in params
    if p in ("graph", "adj", "adjacency", "g", "edges_map"):
        return _GRAPH
    if p in ("matrix", "grid", "board", "mat"):
        return _GRID
    if p in ("start", "source", "src", "s_node") and any(x in params for x in ("graph", "adj", "g")):
        return 0
    if p in ("lo", "low", "left", "l", "start", "begin"):
        return 0
    if p in ("hi", "high", "right", "r", "end"):
        return len(_SORTED if searching else _UNSORTED) - 1
    if p in ("target", "key", "x", "val", "value", "k_val") and searching:
        return 7
    if p in ("target", "total", "amount", "goal"):
        return 10
    if any(t in p for t in ("arr", "nums", "list", "lst", "items", "values", "array", "data", "seq",
                            "numbers", "heights", "prices", "coins", "weights")) or p in ("a", "xs"):
        return list(_SORTED if searching else _UNSORTED)
    if p in ("s", "string", "text", "word", "str1", "t", "pattern", "str2"):
        return "racecar" if "palin" in f else "abcab"
    if p in ("n", "num", "k", "count", "size", "m", "number", "steps", "depth", "limit"):
        return 6
    if annotation.startswith(("list", "List")):
        return list(_UNSORTED)
    if annotation in ("str",):
        return "hello"
    if annotation in ("int", "float"):
        return 6
    if annotation.startswith(("dict", "Dict")):
        return dict(_GRAPH)
    return None


def synthesize_entry_call(tree: ast.Module) -> tuple[str | None, str | None]:
    """Return (entry_call, warning). entry_call is None when code runs on its own."""
    has_toplevel_work = any(
        isinstance(n, (ast.Expr, ast.Assign, ast.For, ast.While, ast.If, ast.AugAssign))
        for n in tree.body
    )
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if has_toplevel_work or not funcs:
        return None, None
    called = {
        c.func.id for f in funcs for c in ast.walk(f)
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id != f.name
    }
    roots = [f for f in funcs if f.name not in called and not f.name.startswith("_")]
    entry = (roots or funcs)[-1]
    params = [a.arg for a in entry.args.args if a.arg not in ("self", "cls")]
    args = []
    for a in entry.args.args:
        if a.arg in ("self", "cls"):
            continue
        ann = ast.unparse(a.annotation) if a.annotation else ""
        value = _guess(a.arg, ann, entry.name, params)
        if value is None:
            return None, (f"Couldn't guess an input for `{entry.name}({', '.join(params)})` — "
                          "provide an entry call such as "
                          f"`{entry.name}(...)` to see the dry run.")
        args.append(repr(value))
    return f"{entry.name}({', '.join(args)})", None
