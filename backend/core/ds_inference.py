"""Infer which data structure a traced variable represents and convert it to
the `DataStructureState.state` shape the frontend renders.
"""

import re

from core.value_model import Value, fmt, is_int, is_prim, is_seq, items, node_value, tag

_GRAPH_NAMES = re.compile(r"graph|adj|neighbo|edges", re.I)
_KIND_BONUS = {
    "graph": 1000, "tree": 1000, "linked_list": 1000, "matrix": 500, "heap": 400,
    "stack": 300, "queue": 300, "array": 200, "hash_map": 100,
}


def classify(name: str, value: Value, heap_names: frozenset[str] = frozenset()) -> str | None:
    """Return the DSType for `value`, or None when it is not visualisable."""
    t = tag(value)
    lname = name.lower()
    if t == "deque":
        return "queue"
    if t in ("list", "tuple"):
        elems = value["v"]
        if elems and all(is_seq(e) for e in elems):
            if _GRAPH_NAMES.search(name) and all(all(is_int(x) for x in items(e)) for e in elems):
                return "graph"
            if all(all(is_prim(x) for x in items(e)) for e in elems):
                return "matrix"
            return None
        if not all(is_prim(e) for e in elems):
            return None
        if "stack" in lname or lname in ("st", "stk"):
            return "stack"
        if "queue" in lname or lname in ("q", "dq"):
            return "queue"
        if "heap" in lname or lname == "pq" or name in heap_names:
            return "heap"
        return "array"
    if t == "dict":
        return "graph" if _looks_like_adjacency(name, value) else "hash_map"
    if t == "obj":
        fields = value["f"]
        if "next" in fields:
            return "linked_list"
        if {"left", "right"} & fields.keys() or "children" in fields:
            return "tree"
    return None


def _looks_like_adjacency(name: str, value: Value) -> bool:
    """dict[key -> list of keys | (key, weight)] whose neighbours are mostly keys."""
    entries = value["v"]
    if not entries or not all(is_prim(k) and is_seq(v) for k, v in entries):
        return False
    keys = {k for k, _ in entries}
    neighbours = [n[0] if is_seq(n) else n for _, v in entries for n in items(v)]
    if not neighbours or not all(is_prim(n) for n in neighbours):
        return False
    overlap = sum(n in keys for n in neighbours) / len(neighbours)
    return overlap >= 0.6 or bool(_GRAPH_NAMES.search(name))


def score(kind: str, name: str, value: Value) -> int:
    """Rank candidates when picking the trace's focus variable."""
    size = len(value.get("v", [])) if isinstance(value, dict) else 0
    return _KIND_BONUS.get(kind, 0) + min(size, 50) + (50 if len(name) > 1 else 0)


def to_state(kind: str, value: Value) -> dict:
    """Convert a value model to the renderer state for `kind`."""
    if kind in ("array", "stack", "queue", "heap"):
        return {"values": [v if is_prim(v) else fmt(v) for v in items(value)]}
    if kind == "matrix":
        return {"rows": [[x if is_prim(x) else fmt(x) for x in items(r)] for r in items(value)]}
    if kind == "hash_map":
        return {"entries": [[k if is_prim(k) else fmt(k), v if is_prim(v) else fmt(v)]
                            for k, v in value["v"]]}
    if kind == "graph":
        return _graph_state(value)
    if kind == "linked_list":
        return _list_state(value)
    if kind == "tree":
        return {"root": _tree_node(value, set())}
    return {}


def _graph_state(value: Value) -> dict:
    if tag(value) == "dict":
        adjacency = [(k, items(v)) for k, v in value["v"]]
    else:  # index-based adjacency list
        adjacency = [(i, items(row)) for i, row in enumerate(items(value))]
    node_ids: list = []
    edges: list[dict] = []
    for src, neighbours in adjacency:
        node_ids.append(src)
        for n in neighbours:
            dst, weight = (items(n)[0], items(n)[1] if len(items(n)) > 1 else None) if is_seq(n) else (n, None)
            node_ids.append(dst)
            edges.append({"source": str(src), "target": str(dst), "weight": weight})
    pairs = {(e["source"], e["target"]) for e in edges}
    directed = any((b, a) not in pairs for a, b in pairs)
    if not directed:  # keep one edge per undirected pair
        edges = [e for e in edges if e["source"] <= e["target"]]
    unique = list(dict.fromkeys(str(n) for n in node_ids))
    return {"nodes": [{"id": n, "label": n} for n in unique], "edges": edges, "directed": directed}


def _list_state(value: Value) -> dict:
    nodes, cycle_to, current = [], None, value
    while tag(current) == "obj" and len(nodes) < 60:
        nodes.append({"id": str(current["id"]), "value": node_value(current["f"])})
        current = current["f"].get("next")
    if tag(current) == "ref":
        cycle_to = str(current["id"])
    return {"nodes": nodes, "cycle_to": cycle_to}


def _tree_node(value: Value, seen: set[int]) -> dict | None:
    if tag(value) != "obj" or value["id"] in seen or len(seen) > 120:
        return None
    seen.add(value["id"])
    fields = value["f"]
    if "children" in fields:
        kids = [_tree_node(c, seen) for c in items(fields["children"])]
    else:
        kids = [_tree_node(fields.get("left"), seen), _tree_node(fields.get("right"), seen)]
    return {"id": str(value["id"]), "value": node_value(fields), "children": kids}


def collect_ids(value: Value) -> set[str]:
    """All object ids reachable inside a value model (for pointer highlights)."""
    found: set[str] = set()
    stack = [value]
    while stack:
        v = stack.pop()
        if tag(v) == "obj":
            found.add(str(v["id"]))
            stack.extend(v["f"].values())
        elif tag(v) in ("list", "tuple", "set", "deque"):
            stack.extend(v["v"])
    return found
