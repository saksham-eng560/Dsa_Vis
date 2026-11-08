"""Helpers for the tagged value model emitted by `sandbox/harness.py`.

Primitives are plain JSON (None/bool/int/float/str). Containers are tagged dicts:
  {"t": "list"|"tuple"|"set"|"deque", "v": [...]}
  {"t": "dict", "v": [[key, value], ...]}
  {"t": "obj", "cls": str, "id": int, "f": {field: value}}
  {"t": "ref", "id": int}          # already-serialised object (cycle/alias)
  {"t": "repr", "v": str}           # anything else
"""

from typing import Any

Value = Any  # JSON value in the tagged model

SEQ_TAGS = ("list", "tuple", "set", "deque")


def tag(value: Value) -> str | None:
    """Return the container tag, or None for primitives."""
    return value.get("t") if isinstance(value, dict) else None


def is_prim(value: Value) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def is_seq(value: Value) -> bool:
    return tag(value) in SEQ_TAGS


def items(value: Value) -> list[Value]:
    """Elements of a sequence model (empty for non-sequences)."""
    return value["v"] if is_seq(value) else []


def is_int(value: Value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def node_value(fields: dict[str, Value]) -> Value:
    """Pick the payload field of a node-like object (val/value/data/key)."""
    for name in ("val", "value", "data", "key", "item", "name"):
        if name in fields:
            return fields[name] if is_prim(fields[name]) else fmt(fields[name])
    return "•"


def fmt(value: Value, depth: int = 0) -> str:
    """Python-flavoured display string for the variable watch panel."""
    if value is None or isinstance(value, bool):
        return repr(value)
    if isinstance(value, str):
        return repr(value)
    if is_prim(value):
        return str(value)
    t = tag(value)
    if depth > 3:
        return "…"
    if t in SEQ_TAGS:
        inner = ", ".join(fmt(v, depth + 1) for v in value["v"])
        if t == "tuple":
            return f"({inner}{',' if len(value['v']) == 1 else ''})"
        if t == "set":
            return "{" + inner + "}" if inner else "set()"
        if t == "deque":
            return f"deque([{inner}])"
        return f"[{inner}]"
    if t == "dict":
        return "{" + ", ".join(f"{fmt(k, depth + 1)}: {fmt(v, depth + 1)}" for k, v in value["v"]) + "}"
    if t == "obj":
        fields = ", ".join(f"{k}={fmt(v, depth + 1)}" for k, v in list(value["f"].items())[:4])
        return f"{value['cls']}({fields})"
    if t == "ref":
        return f"<ref #{value['id']}>"
    return str(value.get("v", "?"))
