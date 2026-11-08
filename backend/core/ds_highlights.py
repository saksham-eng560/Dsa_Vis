"""Compute highlight annotations (pointers, visited nodes, changed cells) for a
data-structure snapshot from the surrounding local variables.
"""

import re

from api.schemas.response import Highlight
from core.ds_inference import collect_ids
from core.value_model import Value, is_int, is_prim, is_seq, items, tag

_POINTER_NAMES = {
    "i", "j", "k", "l", "r", "p", "q", "m", "lo", "hi", "low", "high", "left", "right",
    "mid", "start", "end", "idx", "index", "pos", "ptr", "slow", "fast", "front", "rear",
    "top", "head", "tail", "cur", "curr", "pivot", "last", "first", "row", "col", "c",
}
_POINTER_SUFFIX = re.compile(r"_(idx|index|ptr|pos)$")
_PALETTE = ("green", "yellow", "purple", "blue")
_NODE_COLORS = {"slow": "green", "fast": "red", "prev": "purple", "head": "blue"}
_CURRENT_NODE = {"node", "u", "v", "cur", "curr", "current", "vertex", "at"}
_KEY_NAMES = {"key", "k", "num", "x", "complement", "c", "ch", "char", "word", "item", "diff"}


def _is_pointer(name: str) -> bool:
    return name in _POINTER_NAMES or bool(_POINTER_SUFFIX.search(name))


def highlights(kind: str, value: Value, prev_value: Value | None, scope: dict) -> list[Highlight]:
    """Return highlight list for `value` given the variables in `scope`."""
    if kind in ("array", "stack", "queue", "heap"):
        return _sequence(items(value), items(prev_value) if prev_value else None, scope)
    if kind == "matrix":
        return _matrix(value, prev_value, scope)
    if kind == "hash_map":
        return _hash_map(value, prev_value, scope)
    if kind in ("linked_list", "tree"):
        return _object_pointers(value, scope)
    if kind == "graph":
        return _graph(scope)
    return []


def _sequence(values: list, prev: list | None, scope: dict) -> list[Highlight]:
    out: list[Highlight] = []
    pointers = [(n, v) for n, v in scope.items() if is_int(v) and _is_pointer(n)]
    for idx, (name, val) in enumerate(pointers):
        if 0 <= val < len(values):
            out.append(Highlight(target=val, color=_PALETTE[idx % len(_PALETTE)], label=name))
    if prev is not None and len(prev) == len(values):
        out += [Highlight(target=i, color="red", label="changed")
                for i, (a, b) in enumerate(zip(prev, values)) if a != b]
    return out


def _matrix(value: Value, prev: Value | None, scope: dict) -> list[Highlight]:
    rows = [items(r) for r in items(value)]
    ints = [(n, v) for n, v in scope.items() if is_int(v) and _is_pointer(n)]
    out: list[Highlight] = []
    if len(ints) >= 2:
        (rn, r), (cn, c) = ints[0], ints[1]
        if 0 <= r < len(rows) and 0 <= c < len(rows[r]):
            out.append(Highlight(target=[r, c], color="yellow", label=f"{rn},{cn}"))
    if prev is not None:
        prev_rows = [items(r) for r in items(prev)]
        for r, (a, b) in enumerate(zip(prev_rows, rows)):
            out += [Highlight(target=[r, c], color="red", label="changed")
                    for c, (x, y) in enumerate(zip(a, b)) if x != y]
    return out


def _hash_map(value: Value, prev: Value | None, scope: dict) -> list[Highlight]:
    entries = {repr(k): v for k, v in value["v"]}
    before = {repr(k): v for k, v in prev["v"]} if prev and tag(prev) == "dict" else None
    out: list[Highlight] = []
    for k, v in value["v"]:
        if before is not None and before.get(repr(k), object()) != v:
            out.append(Highlight(target=k, color="red", label="updated"))
    for name, val in scope.items():
        if name in _KEY_NAMES and is_prim(val) and repr(val) in entries:
            out.append(Highlight(target=val, color="green", label=name))
    return out


def _object_pointers(value: Value, scope: dict) -> list[Highlight]:
    ids = collect_ids(value)
    out: list[Highlight] = []
    for name, val in scope.items():
        ref_id = str(val["id"]) if tag(val) in ("obj", "ref") else None
        if ref_id in ids:
            out.append(Highlight(target=ref_id, color=_NODE_COLORS.get(name, "yellow"), label=name))
    return out


def _graph(scope: dict) -> list[Highlight]:
    out: list[Highlight] = []
    for name, val in scope.items():
        lname = name.lower()
        if ("visit" in lname or "seen" in lname) and (is_seq(val) or tag(val) == "dict"):
            members = [k for k, _ in val["v"]] if tag(val) == "dict" else items(val)
            out += [Highlight(target=str(m), color="green", label="visited")
                    for m in members if is_prim(m)]
        elif ("queue" in lname or "stack" in lname or lname in ("q", "dq")) and is_seq(val):
            out += [Highlight(target=str(m), color="yellow", label="frontier")
                    for m in items(val) if is_prim(m)]
        elif name in _CURRENT_NODE and is_prim(val):
            out.append(Highlight(target=str(val), color="red", label="current"))
    return out
