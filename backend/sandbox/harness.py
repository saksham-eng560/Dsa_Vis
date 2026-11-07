# Trace harness — trusted code executed inside the sandbox subprocess.
#
# Reads {"code", "prelude", "setup", "entry_call", "max_steps"} JSON from stdin.
# The prelude (trusted helpers, e.g. LeetCode's ListNode) and setup (binding test
# inputs) run untraced; then the user code runs
# under sys.settrace, and writes one JSON document describing every executed
# line (locals snapshot, call depth, stdout offset) to the real stdout.
import builtins
import io
import json
import math
import sys
from collections import deque

_USER_FILE = "<user_code>"
_MAX_NODES = 300  # per-variable serialisation budget
_ids: dict[int, int] = {}  # python id -> small stable id (stable animation keys)


class _StopTrace(BaseException):
    """Raised from the tracer once the step budget is exhausted."""


def _stable_id(obj):
    key = id(obj)
    if key not in _ids:
        _ids[key] = len(_ids) + 1
    return _ids[key]


def _ser(value, seen, budget):
    """Convert a Python value to a JSON-safe tagged model (see tracer.py)."""
    budget[0] -= 1
    if budget[0] < 0:
        return {"t": "repr", "v": "…"}
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) < 2**53 else {"t": "repr", "v": str(value)}
    if isinstance(value, float):
        return value if math.isfinite(value) else {"t": "repr", "v": repr(value)}
    if isinstance(value, str):
        return value if len(value) <= 200 else value[:200] + "…"
    if isinstance(value, (list, tuple, set, frozenset, deque)):
        tag = {list: "list", tuple: "tuple", deque: "deque"}.get(type(value), "set")
        items = sorted(value, key=repr) if tag == "set" else value
        return {"t": tag, "v": [_ser(v, seen, budget) for v in list(items)[:200]]}
    if isinstance(value, dict):
        return {"t": "dict", "v": [[_ser(k, seen, budget), _ser(v, seen, budget)]
                                    for k, v in list(value.items())[:200]]}
    if hasattr(value, "__dict__") and not callable(value) and not isinstance(value, type):
        oid = _stable_id(value)
        if oid in seen:
            return {"t": "ref", "id": oid}
        seen.add(oid)
        fields = {k: _ser(v, seen, budget) for k, v in vars(value).items()
                  if not k.startswith("_")}
        return {"t": "obj", "cls": type(value).__name__, "id": oid, "f": fields}
    return {"t": "repr", "v": repr(value)[:120]}


def _visible(name, value):
    """Hide dunders, modules, classes and callables — only data is visualised."""
    return not name.startswith("__") and not isinstance(value, type) and \
        not isinstance(value, type(sys)) and not callable(value)


def _snapshot(namespace, hidden=None):
    """Serialise visible variables; `hidden` maps prelude names to their original values."""
    seen = set()
    hidden = hidden or {}
    return {k: _ser(v, seen, [_MAX_NODES]) for k, v in list(namespace.items())
            if _visible(k, v) and hidden.get(k, _ser) is not v}


def _depth(frame):
    depth = 0
    while frame is not None:
        if frame.f_code.co_filename == _USER_FILE:
            depth += 1
        frame = frame.f_back
    return depth - 1


def _main():
    payload = json.loads(sys.stdin.read())
    max_steps = int(payload.get("max_steps", 400))
    user_globals = {"__name__": "__main__", "__builtins__": builtins}
    steps = []
    state = {"truncated": False, "last_exc": None}
    out = io.StringIO()
    if payload.get("prelude"):
        exec(compile(payload["prelude"], "<prelude>", "exec"), user_globals)
    prelude_names = dict(user_globals)

    def tracer(frame, event, arg):
        code = frame.f_code
        if code.co_filename != _USER_FILE:
            return None
        if event == "call" and code.co_name == "<module>":
            return tracer
        if event == "exception":
            if state["last_exc"] is arg[1]:
                return tracer
            state["last_exc"] = arg[1]
        if len(steps) >= max_steps:
            state["truncated"] = True
            raise _StopTrace
        is_module = code.co_name == "<module>"
        step = {
            "line": frame.f_lineno, "event": event, "func": code.co_name,
            "depth": _depth(frame), "out": out.tell(),
            "locals": {} if is_module else _snapshot(frame.f_locals),
            "globals": _snapshot(user_globals, prelude_names),
        }
        if event == "return":
            step["ret"] = _ser(arg, set(), [_MAX_NODES])
        elif event == "exception":
            step["exc"] = f"{arg[0].__name__}: {arg[1]}"
        steps.append(step)
        return tracer

    error, result = None, None
    sys.stdout, sys.stdin = out, io.StringIO("")
    try:
        compiled = compile(payload["code"], _USER_FILE, "exec")
        entry = payload.get("entry_call")
        entry_code = compile(entry, "<entry>", "eval") if entry else None
        setup_code = compile(payload.get("setup") or "", "<setup>", "exec")
        _codelens_arm()  # noqa: F821 - defined by guard.py, prepended at runtime
        sys.settrace(tracer)
        exec(compiled, user_globals)
        exec(setup_code, user_globals)
        if entry_code is not None:
            result = repr(eval(entry_code, user_globals))[:500]
    except _StopTrace:
        pass
    except BaseException as exc:  # report user errors instead of crashing
        error = f"{type(exc).__name__}: {exc}"
    finally:
        sys.settrace(None)
        sys.stdout, sys.stdin = sys.__stdout__, sys.__stdin__
    doc = {"steps": steps, "stdout": out.getvalue()[:100_000], "error": error,
           "truncated": state["truncated"], "result": result}
    sys.__stdout__.write(json.dumps(doc, default=repr))


_main()
