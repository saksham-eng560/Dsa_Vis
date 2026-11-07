"""Turn real Python execution into a `DryRun`: run the harness in the sandbox,
then post-process raw line events into described steps with data-structure
snapshots and highlights.
"""

import json
import re
from pathlib import Path

from api.schemas.response import DataStructureState, DryRun, DryRunStep
from core.ds_highlights import highlights
from core.ds_inference import classify, score, to_state
from core.node_registry import NodeRegistry
from core.value_model import Value, fmt
from sandbox.executor import run_python

_HARNESS = (Path(__file__).parent.parent / "sandbox" / "harness.py").read_text()
_HEAPQ_RX = re.compile(r"heapq\.\w+\(\s*(\w+)")


async def trace_python(
    code: str,
    entry_call: str | None,
    *,
    max_steps: int,
    timeout_s: float,
    memory_mb: int,
    prelude: str = "",
    setup: str = "",
    input_label: str | None = None,
) -> DryRun:
    """Execute `code` (+ optional `entry_call`) in the sandbox and build a DryRun.

    `prelude` (helpers) and `setup` (input bindings) run untraced before the entry call;
    `input_label` replaces the raw entry call in the UI (e.g. LeetCode's `nums = [2,7]`).
    """
    payload = json.dumps({"code": code, "entry_call": entry_call, "max_steps": max_steps,
                          "prelude": prelude, "setup": setup})
    result = await run_python(_HARNESS, payload, timeout_s, memory_mb)
    if result.timed_out:
        return DryRun(source="trace", error="Execution timed out (possible infinite loop).")
    try:
        doc = json.loads(result.stdout)
    except json.JSONDecodeError:
        tail = result.stderr.strip().splitlines()[-1:] or ["sandbox crashed"]
        return DryRun(source="trace", error=f"Sandbox error: {tail[0]}")
    steps = build_steps(doc["steps"], doc["stdout"], code, frozenset(_HEAPQ_RX.findall(code)))
    error = doc.get("error")
    label = input_label or entry_call
    if doc.get("result") is not None and steps:
        steps[-1].output_so_far += f"\n→ {'result' if input_label else entry_call} = {doc['result']}"
    return DryRun(
        input_example=label or "",
        steps=steps,
        source="trace",
        truncated=bool(doc.get("truncated")),
        error=error,
    )


def _scope(raw: dict) -> dict[str, Value]:
    """Visible variables: globals, overlaid by locals, plus `self.<field>` for methods.

    Expanding `self` lets class-based code (MinStack, LRUCache, …) visualise its fields.
    """
    scope = {**raw["globals"], **raw["locals"]}
    me = raw["locals"].get("self")
    if isinstance(me, dict) and me.get("t") == "obj":
        scope.update({f"self.{k}": v for k, v in me["f"].items()})
    return scope


def _pick_focus(raw_steps: list[dict], heap_names: frozenset[str]) -> tuple[str, str] | None:
    """Choose the (variable, kind) that best represents the algorithm's state."""
    best: dict[tuple[str, str], int] = {}
    for raw in raw_steps:
        for name, value in _scope(raw).items():
            kind = classify(name, value, heap_names)
            if kind:
                key = (name, kind)
                best[key] = max(best.get(key, 0), score(kind, name, value)) + 1
    return max(best, key=lambda k: best[k]) if best else None


def _focus_value(focus: tuple[str, str], raw: dict, heap_names: frozenset[str]) -> Value | None:
    """Value of the focus variable at this step.

    Linked structures prefer the *global* binding: inside recursive helpers the
    local `root`/`head` is just a sub-structure, while the global one is whole.
    """
    name, kind = focus
    if name.startswith("self."):
        value = _scope(raw).get(name)
        return value if value is not None and classify(name, value, heap_names) == kind else None
    order = ("globals", "locals") if kind in ("tree", "linked_list") else ("locals", "globals")
    for space in order:
        value = raw[space].get(name)
        if value is not None and classify(name, value, heap_names) == kind:
            return value
    return None


def build_steps(
    raw_steps: list[dict], stdout: str, code: str, heap_names: frozenset[str] = frozenset()
) -> list[DryRunStep]:
    """Convert harness events into API steps (pure function — unit tested)."""
    lines = code.splitlines()
    focus = _pick_focus(raw_steps, heap_names)
    steps: list[DryRunStep] = []
    prev_vars: dict[str, str] = {}
    prev_frame: tuple[str, int] | None = None
    prev_focus_value: Value | None = None
    last_state: DataStructureState | None = None
    registry = NodeRegistry()
    root_id: int | None = None

    for idx, raw in enumerate(raw_steps):
        scope = _scope(raw)
        variables = {k: fmt(v) for k, v in scope.items()}
        frame = (raw["func"], raw["depth"])
        changed = (
            [k for k, v in variables.items() if prev_vars.get(k) != v] if frame == prev_frame else []
        )
        ds_state = last_state.model_copy(update={"highlights": []}) if last_state else None
        value = _focus_value(focus, raw, heap_names) if focus else None
        linked = focus is not None and focus[1] in ("tree", "linked_list")
        if linked:
            for v in scope.values():
                registry.update(v)
            if value is not None and root_id is None:
                root_id = value.get("id")
            if root_id is not None:  # whole structure, rebuilt from the freshest node data
                value = (registry.all_lists(root_id) if focus[1] == "linked_list"  # type: ignore[index]
                         else registry.whole(focus[1], root_id))  # type: ignore[index]
        if focus and value is not None:
            ds_state = DataStructureState(
                type=focus[1],  # type: ignore[arg-type]
                name=focus[0],
                state=registry.list_state(root_id) if focus[1] == "linked_list" else to_state(focus[1], value),
                highlights=highlights(focus[1], value, prev_focus_value, raw["locals"] or scope),
            )
            prev_focus_value, last_state = value, ds_state
        elif focus and last_state is not None and prev_focus_value is not None:
            # focus variable out of scope (e.g. inside a helper): keep the structure, refresh pointers
            ds_state = last_state.model_copy(update={
                "highlights": highlights(focus[1], prev_focus_value, None, raw["locals"] or scope)})

        steps.append(
            DryRunStep(
                step=idx + 1,
                line=raw["line"],
                event=raw["event"],
                function=raw["func"],
                depth=max(raw["depth"], 0),
                description=_describe(raw, lines, variables),
                variables=variables,
                changed=changed,
                data_structure_state=ds_state,
                output_so_far=stdout[: raw["out"]],
            )
        )
        prev_vars, prev_frame = variables, frame
    return steps


def _describe(raw: dict, lines: list[str], variables: dict[str, str]) -> str:
    """Human-readable sentence for one step."""
    event, func = raw["event"], raw["func"]
    if event == "call":
        args = ", ".join(f"{k}={v}" for k, v in variables.items() if k in raw["locals"])
        return f"Call {func}({args})"
    if event == "return":
        return f"{func} returns {fmt(raw.get('ret'))}"
    if event == "exception":
        return f"Exception raised: {raw.get('exc', '')}"
    line_no = raw["line"]
    source = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
    return f"Line {line_no}: {source}"
