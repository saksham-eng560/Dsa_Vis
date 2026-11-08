"""Recursion tree from raw trace events (Python harness and C++ runtime alike).

Every `call` opens a node under the currently running call; the matching
`return` closes it with its value. Calls with the same function + arguments
as an earlier one are counted as repeated subproblems — exactly what
memoisation / a DP table eliminates.
"""

from api.schemas.response import CallNode, CallTree
from core.value_model import Value, fmt, node_value, tag

MAX_NODES = 600


_SHARED_NAMES = {"memo", "cache", "dp", "visited", "seen", "graph", "adj", "res", "result", "ans", "out", "path"}


def _is_scalar(v: Value) -> bool:
    return v is None or isinstance(v, (bool, int, float, str))


def _short(v: Value, null: str) -> str:
    """Compact argument text: tree/list nodes as `node 5`, null pointers as `null`/`None`."""
    if v is None:
        return null
    if tag(v) == "obj":
        return f"node {node_value(v['f'])}"
    if tag(v) == "ref":
        return f"node#{v['id']}"
    return fmt(v)


def _args(locals_: dict[str, Value], null: str = "None") -> tuple[str, str]:
    """(label shown on the node, key identifying the subproblem).

    Containers (memo tables, adjacency lists, result lists) are shared state,
    not the subproblem: they're abbreviated in the label and left out of the key.
    """
    shown, key = [], []
    for k, v in locals_.items():
        if k == "self" or k.startswith("self."):
            continue
        if (_is_scalar(v) or tag(v) in ("obj", "ref")) and k not in _SHARED_NAMES:
            text = _short(v, null)
            shown.append(text)
            key.append(f"{k}={v.get('id') if isinstance(v, dict) else text}")  # nodes keyed by identity
        elif k not in _SHARED_NAMES:
            text = fmt(v)
            shown.append(text if len(text) <= 14 else text[:12] + "…")
            key.append(f"{k}={text}")
    return ", ".join(shown)[:80], "|".join(key)


def build_call_tree(raw_steps: list[dict], null: str = "None") -> CallTree | None:
    nodes: list[CallNode] = []
    stack: list[int] = []
    seen: dict[tuple[str, str], int] = {}
    first_of: dict[tuple[str, str], int] = {}
    key_of: dict[int, tuple[str, str]] = {}
    truncated = False
    for idx, raw in enumerate(raw_steps):
        event = raw.get("event")
        if event == "call" and raw.get("func") != "<module>":
            if len(nodes) >= MAX_NODES:
                truncated = True
                stack.append(-1)
                continue
            args, subproblem = _args(raw.get("locals") or {}, null)
            key = (raw["func"], subproblem)
            node = CallNode(id=len(nodes), parent=stack[-1] if stack and stack[-1] >= 0 else None,
                            func=raw["func"], args=args, start=idx, repeat=seen.get(key, 0))
            seen[key] = seen.get(key, 0) + 1
            first_of.setdefault(key, node.id)
            key_of[node.id] = key
            nodes.append(node)
            stack.append(node.id)
        elif event == "return" and raw.get("func") != "<module>" and stack:
            node_id = stack.pop()
            if node_id >= 0:
                nodes[node_id].end = idx
                if "ret" in raw:
                    nodes[node_id].ret = _short(raw["ret"], null) if tag(raw["ret"]) in ("obj", "ref") or \
                        raw["ret"] is None else fmt(raw["ret"])
    if not nodes:
        return None
    by_id = {n.id: n for n in nodes}

    def recursive(n: CallNode) -> bool:
        p = by_id.get(n.parent) if n.parent is not None else None
        while p is not None:
            if p.func == n.func:
                return True
            p = by_id.get(p.parent) if p.parent is not None else None
        return False

    for func in {n.func for n in nodes}:  # void functions: no "→ None" badge on every node
        calls = [n for n in nodes if n.func == func]
        if all(n.ret in (None, null, "None") for n in calls):
            for n in calls:
                n.ret = None
    is_recursive = any(recursive(n) for n in nodes)
    has_children = {n.parent for n in nodes if n.parent is not None}
    for n in nodes:
        if not n.repeat:
            continue
        first_did_work = first_of[key_of[n.id]] in has_children
        if not first_did_work:
            n.repeat = 0  # trivial base case (e.g. f(null)) — cheap, not a real repeated subproblem
        elif n.id not in has_children:
            n.cached = True  # did work the first time, answered instantly now: memo / cache hit
    return CallTree(nodes=nodes, recursive=is_recursive, repeated=sum(1 for n in nodes if n.repeat and not n.cached),
                    cache_hits=sum(1 for n in nodes if n.cached), truncated=truncated)
