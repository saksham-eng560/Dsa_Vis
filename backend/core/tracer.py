"""Turn real Python execution into a `DryRun`: run the harness in the sandbox,
then post-process raw line events into described steps with data-structure
snapshots and highlights.
"""

import json
import re
from pathlib import Path

from api.schemas.response import DataStructureState, DryRun, DryRunStep
from core.call_tree import build_call_tree
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
        call_tree=build_call_tree(doc["steps"]),
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


MAX_FOCI = 4


def _pick_foci(raw_steps: list[dict], heap_names: frozenset[str]) -> list[tuple[str, str]]:
    """Rank the (variable, kind) pairs that best represent the algorithm's state."""
    best: dict[tuple[str, str], int] = {}
    for raw in raw_steps:
        for name, value in _scope(raw).items():
            kind = classify(name, value, heap_names)
            if kind:
                key = (name, kind)
                best[key] = max(best.get(key, 0), score(kind, name, value)) + 1
    ranked = sorted(best, key=lambda k: best[k], reverse=True)
    picked: list[tuple[str, str]] = []
    for name, kind in ranked:
        if any(n == name for n, _ in picked):
            continue
        # one view per linked structure is enough (they all draw the whole structure)
        if kind in ("tree", "linked_list") and any(k == kind for _, k in picked):
            continue
        picked.append((name, kind))
        if len(picked) == MAX_FOCI:
            break
    return picked


def _pick_focus(raw_steps: list[dict], heap_names: frozenset[str]) -> tuple[str, str] | None:
    foci = _pick_foci(raw_steps, heap_names)
    return foci[0] if foci else None


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


class _FocusTracker:
    """Produces the snapshot of one tracked variable at every step."""

    def __init__(self, focus: tuple[str, str], heap_names: frozenset[str]) -> None:
        self.focus, self.heap_names = focus, heap_names
        self.prev_value: Value | None = None
        self.last_state: DataStructureState | None = None
        self.registry = NodeRegistry()
        self.root_id: int | None = None

    def snapshot(self, raw: dict, scope: dict[str, Value]) -> DataStructureState | None:
        name, kind = self.focus
        value = _focus_value(self.focus, raw, self.heap_names)
        if kind in ("tree", "linked_list"):
            for v in scope.values():
                self.registry.update(v)
            if value is not None and self.root_id is None:
                self.root_id = value.get("id")
            if self.root_id is not None:  # whole structure, rebuilt from the freshest node data
                value = (self.registry.all_lists(self.root_id) if kind == "linked_list"
                         else self.registry.whole(kind, self.root_id))
        pointer_scope = raw["locals"] or scope
        if value is not None:
            state = (self.registry.list_state(self.root_id) if kind == "linked_list" else to_state(kind, value))
            ds = DataStructureState(type=kind, name=name, state=state,  # type: ignore[arg-type]
                                    highlights=highlights(kind, value, self.prev_value, pointer_scope))
            self.prev_value, self.last_state = value, ds
            return ds
        if self.last_state is not None and self.prev_value is not None:
            # out of scope (e.g. inside a helper): keep the structure, refresh pointer highlights
            return self.last_state.model_copy(update={
                "highlights": highlights(kind, self.prev_value, None, pointer_scope)})
        return None


def build_steps(
    raw_steps: list[dict], stdout: str, code: str, heap_names: frozenset[str] = frozenset()
) -> list[DryRunStep]:
    """Convert harness events into API steps (pure function — unit tested)."""
    lines = code.splitlines()
    trackers = [_FocusTracker(f, heap_names) for f in _pick_foci(raw_steps, heap_names)]
    steps: list[DryRunStep] = []
    prev_vars: dict[str, str] = {}
    prev_frame: tuple[str, int] | None = None
    frame_vars: dict[tuple[str, int], dict[str, str]] = {}  # last variables seen in each frame

    for idx, raw in enumerate(raw_steps):
        scope = _scope(raw)
        variables = {k: fmt(v) for k, v in scope.items()}
        frame = (raw["func"], raw["depth"])
        if raw["event"] == "return" and not variables:  # C++ returns carry no locals: keep the frame's last view
            variables = dict(frame_vars.get(frame, {}))
        frame_vars[frame] = variables
        changed = (
            [k for k, v in variables.items() if prev_vars.get(k) != v] if frame == prev_frame else []
        )
        structures = [ds for t in trackers if (ds := t.snapshot(raw, scope)) is not None]
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
                data_structure_state=structures[0] if structures else None,
                data_structures=structures,
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
