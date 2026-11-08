"""Validate the LLM's JSON field-by-field and merge it over the static result.

Small models get *parts* of the schema wrong; validating per field keeps every
good part instead of discarding the whole response.
"""

import json
import re
from typing import Any

from pydantic import ValidationError

from api.schemas.response import (
    AnalysisResult,
    Complexity,
    DryRun,
    DryRunStep,
    Explanation,
    Flowchart,
    KeyConcept,
)

_BIG_O_RX = re.compile(r"^O\(.+\)$")
_SUPERSCRIPTS = (("^2", "²"), ("**2", "²"), ("^3", "³"), ("**3", "³"), ("2^n", "2ⁿ"), ("2**n", "2ⁿ"))


def normalize_big_o(notation: str) -> str:
    """Canonical spelling so `O(n^2)` and `O(n²)` compare equal."""
    text = " ".join(notation.strip().split())
    for raw, pretty in _SUPERSCRIPTS:
        text = text.replace(raw, pretty)
    text = re.sub(r"(?i)n\s*\*?\s*log\s*(?:\(n\)|n)", "n log n", text)
    return re.sub(r"(?i)\blog\s*\(n\)", "log n", text)


def _str_list(value: Any, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if isinstance(v, (str, int, float)) and str(v).strip()][:limit]


def _concepts(value: Any) -> list[KeyConcept]:
    out = []
    for item in value if isinstance(value, list) else []:
        try:
            out.append(KeyConcept.model_validate(item))
        except ValidationError:
            continue
    return out[:8]


def _complexity(value: Any) -> Complexity | None:
    try:
        parsed = Complexity.model_validate(value)
    except ValidationError:
        return None
    t = parsed.time
    if not all(_BIG_O_RX.match(x.strip()) for x in (t.best, t.average, t.worst, parsed.space.complexity)):
        return None
    time = t.model_copy(update={k: normalize_big_o(getattr(t, k)) for k in ("best", "average", "worst")})
    space = parsed.space.model_copy(update={"complexity": normalize_big_o(parsed.space.complexity)})
    return parsed.model_copy(update={"time": time, "space": space, "source": "llm"})


_DS_ALIASES = {
    "array": "array", "list": "array", "vector": "array", "arraylist": "array", "string": "array",
    "matrix": "matrix", "grid": "matrix", "2d array": "matrix", "2d_array": "matrix", "table": "matrix",
    "dp": "matrix", "dp table": "matrix", "dp_table": "matrix",
    "stack": "stack", "queue": "queue", "deque": "queue", "heap": "heap", "priority_queue": "heap",
    "priority queue": "heap", "hash_map": "hash_map", "hashmap": "hash_map", "map": "hash_map", "dict": "hash_map",
    "dictionary": "hash_map", "unordered_map": "hash_map", "hash table": "hash_map", "set": "array",
    "linked_list": "linked_list", "linked list": "linked_list", "linkedlist": "linked_list",
    "tree": "tree", "binary tree": "tree", "binary_tree": "tree", "bst": "tree", "graph": "graph",
}
_COLORS = {"green", "red", "yellow", "blue", "purple"}


def _scalar(v: Any) -> Any:
    return v if v is None or isinstance(v, (bool, int, float, str)) else json.dumps(v)


def _norm_ds(raw: Any) -> dict | None:
    """Coerce a small model's data-structure snapshot into our schema (or None)."""
    if not isinstance(raw, dict):
        return None
    kind = _DS_ALIASES.get(str(raw.get("type", "")).strip().lower())
    if kind is None:
        return None
    state = raw.get("state", raw.get("values", raw.get("data")))
    if kind in ("array", "stack", "queue", "heap"):
        values = state.get("values", state.get("items")) if isinstance(state, dict) else state
        if isinstance(values, str):
            values = list(values)
        if not isinstance(values, list):
            return None
        state = {"values": [_scalar(v) for v in values]}
    elif kind == "matrix":
        rows = state.get("rows", state.get("values")) if isinstance(state, dict) else state
        if not (isinstance(rows, list) and all(isinstance(r, list) for r in rows)):
            return None
        state = {"rows": [[_scalar(v) for v in r] for r in rows]}
    elif kind == "hash_map":
        entries = state.get("entries", state) if isinstance(state, dict) else state
        if isinstance(entries, dict):
            entries = list(entries.items())
        if not isinstance(entries, list):
            return None
        pairs = [e for e in entries if isinstance(e, (list, tuple)) and len(e) == 2]
        state = {"entries": [[_scalar(k), _scalar(v)] for k, v in pairs]}
    elif not isinstance(state, dict):
        return None
    highlights = []
    for h in raw.get("highlights") or []:
        if not isinstance(h, dict):
            continue
        target = next((h[k] for k in ("target", "index_or_node", "index", "node", "key", "cell", "id") if k in h), None)
        if target is None:
            continue
        color = str(h.get("color", "yellow")).lower()
        highlights.append({"target": target, "color": color if color in _COLORS else "yellow",
                           "label": str(h.get("label", ""))[:20]})
    return {"type": kind, "name": str(raw.get("name", "")), "state": state, "highlights": highlights}


def _find_steps(value: Any) -> tuple[list, str]:
    """Locate the step list in whatever shape the model returned."""
    if isinstance(value, list):
        return value, ""
    if not isinstance(value, dict):
        return [], ""
    for key in ("dry_run", "dryRun", "dry_run_steps", "trace"):
        if key in value and value[key] is not value:
            steps, label = _find_steps(value[key])
            if steps:
                return steps, label or str(value.get("input_example", ""))
    steps = value.get("steps")
    return (steps if isinstance(steps, list) else []), str(value.get("input_example", value.get("input", "")))


def parse_dry_run(value: Any) -> DryRun | None:
    """Tolerant parse of an LLM trace: keeps every step that can be salvaged."""
    raw_steps, label = _find_steps(value)
    steps: list[DryRunStep] = []
    for raw in raw_steps[:60]:
        if not isinstance(raw, dict):
            continue
        variables = raw.get("variables") if isinstance(raw.get("variables"), dict) else {}
        line = raw.get("line")
        step = {
            "step": len(steps) + 1,
            "line": int(line) if isinstance(line, (int, float)) or (isinstance(line, str) and line.isdigit()) else None,
            "description": str(raw.get("description") or raw.get("action") or raw.get("explanation") or ""),
            "function": "<ai>",
            "variables": {str(k): v if isinstance(v, str) else json.dumps(v) for k, v in variables.items()},
            "output_so_far": str(raw.get("output_so_far") or raw.get("output") or ""),
            "data_structure_state": _norm_ds(raw.get("data_structure_state") or raw.get("state")),
        }
        try:
            steps.append(DryRunStep.model_validate(step))
        except ValidationError:
            step["data_structure_state"] = None  # keep the narration even if the snapshot is unusable
            try:
                steps.append(DryRunStep.model_validate(step))
            except ValidationError:
                continue
    if not steps:
        return None
    _carry_forward(steps)
    return DryRun(input_example=label, steps=steps, source="llm")


def _carry_forward(steps: list[DryRunStep]) -> None:
    """Steps without a snapshot keep showing the previous structure (without highlights)."""
    last = None
    for s in steps:
        if s.data_structure_state is None and last is not None:
            s.data_structure_state = last.model_copy(update={"highlights": []})
        elif s.data_structure_state is not None:
            last = s.data_structure_state


def merge_dry_run(result: AnalysisResult, data: Any) -> AnalysisResult:
    """Attach an AI-generated trace (keeping the user's chosen input label)."""
    run = parse_dry_run(data)
    warnings = [w for w in result.warnings if "needs AI model" not in w]
    if run is None:
        warnings.append("The AI model didn't return a usable dry run — try Visualize again, "
                        "or use Python for a live trace.")
        return result.model_copy(update={"warnings": warnings})
    if result.dry_run.input_example:
        run = run.model_copy(update={"input_example": result.dry_run.input_example})
    warnings.append("This dry run was generated by the AI model and may contain mistakes.")
    return result.model_copy(update={"dry_run": run, "warnings": warnings, "llm_used": True})


def merge_analysis(static: AnalysisResult, data: dict[str, Any]) -> AnalysisResult:
    """Overlay valid LLM fields on the static result."""
    update: dict[str, Any] = {"llm_used": True}
    if isinstance(data.get("summary"), str) and data["summary"].strip():
        update["summary"] = data["summary"].strip()
    if isinstance(data.get("algorithm_name"), str) and data["algorithm_name"].strip():
        update["algorithm_name"] = data["algorithm_name"].strip()
    if structures := _str_list(data.get("data_structures_used")):
        update["data_structures_used"] = structures
    for key in ("edge_cases", "optimizations", "related_algorithms", "common_mistakes", "approach"):
        if values := _str_list(data.get(key), limit=10):  # an omitted/truncated field keeps the static value
            update[key] = values
    for key in ("intuition", "why_it_works"):
        if isinstance(data.get(key), str) and data[key].strip():
            update[key] = data[key].strip()
    if concepts := _concepts(data.get("key_concepts")):
        update["key_concepts"] = concepts

    warnings = list(static.warnings)
    if llm_cx := _complexity(data.get("complexity")):
        if static.complexity.source == "static" and llm_cx.time.worst != static.complexity.time.worst:
            warnings.append(
                f"Static analysis estimated {static.complexity.time.worst} worst-case time; "
                f"the AI model says {llm_cx.time.worst}."
            )
        update["complexity"] = llm_cx
    if not static.flowchart.nodes and isinstance(data.get("flowchart"), dict):
        try:
            update["flowchart"] = Flowchart.model_validate({**data["flowchart"], "source": "llm"})
        except ValidationError:
            pass
    update["warnings"] = warnings
    return static.model_copy(update=update)


def merge_explanation(fallback: Explanation, data: dict[str, Any], eli5: bool) -> Explanation:
    """Build an Explanation from LLM JSON, keeping fallback values for bad fields."""
    def text(key: str) -> str:
        value = data.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else getattr(fallback, key)

    return Explanation(
        summary=text("summary"),
        algorithm_name=text("algorithm_name"),
        intuition=text("intuition"),
        why_it_works=text("why_it_works"),
        approach=_str_list(data.get("approach"), limit=10) or fallback.approach,
        common_mistakes=_str_list(data.get("common_mistakes")) or fallback.common_mistakes,
        key_concepts=_concepts(data.get("key_concepts")) or fallback.key_concepts,
        edge_cases=_str_list(data.get("edge_cases")) or fallback.edge_cases,
        optimizations=_str_list(data.get("optimizations")) or fallback.optimizations,
        related_algorithms=_str_list(data.get("related_algorithms")) or fallback.related_algorithms,
        eli5=eli5,
        llm_used=True,
    )
