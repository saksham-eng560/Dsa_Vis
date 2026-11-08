"""Visualisation plan: which traced structures to show, in what order, with what captions.

The AI proposes a plan per problem/solution (declarative JSON — never code), and
a deterministic default plan is always available. Plans only reorder/caption
data the real trace produced, so the visuals stay truthful.
"""

from typing import Any

from pydantic import ValidationError

from api.schemas.response import AnalysisResult, DryRun, VisualPlan

_DEFAULT_CAPTIONS = {
    "dp": "dp table — each cell holds the answer to one subproblem, built from smaller ones",
    "memo": "memo — answers to subproblems already solved, reused instead of recomputed",
    "cache": "cache — answers to subproblems already solved",
    "visited": "visited — nodes already explored, so none is processed twice",
    "seen": "seen — values met so far, for O(1) lookups",
    "stack": "stack — last in, first out",
    "queue": "queue — first in, first out (the BFS frontier)",
    "heap": "heap — the smallest/largest item is always on top",
    "grid": "grid — the 2-D board being explored",
}


def available_structures(run: DryRun) -> list[tuple[str, str]]:
    """(name, type) of every structure the trace tracked, in first-seen order."""
    seen: dict[str, str] = {}
    for step in run.steps:
        for ds in step.data_structures:
            seen.setdefault(ds.name, ds.type)
    return list(seen.items())


def describe_for_prompt(run: DryRun) -> str:
    """Facts handed to the model so its plan can only pick real variables."""
    parts = []
    if names := available_structures(run):
        parts.append("Traced variables available to visualise: " + ", ".join(f"{n} ({t})" for n, t in names))
    tree = run.call_tree
    if tree and tree.recursive:
        parts.append(f"Recursion: yes — {len(tree.nodes)} calls, {tree.repeated} repeated subproblems")
    return "\n".join(f"- {p}" for p in parts)


def default_plan(run: DryRun) -> VisualPlan:
    names = [n for n, _ in available_structures(run)]
    captions = {n: c for n in names for key, c in _DEFAULT_CAPTIONS.items() if n.lower().startswith(key)}
    tree = run.call_tree
    insight = ""
    if tree and tree.recursive and tree.repeated:
        insight = (f"Orange calls recompute a subproblem that was already solved — {tree.repeated} of "
                   f"{len(tree.nodes)} calls. Caching them (memo / DP table) removes that work.")
    elif tree and tree.recursive and tree.cache_hits:
        insight = (f"Green dashed calls are cache hits — {tree.cache_hits} times the memo returned a stored "
                   "answer instead of recursing again. That is what keeps this solution fast.")
    elif tree and tree.recursive:
        insight = "Follow the blue path: it is the chain of calls currently on the stack."
    return VisualPlan(focus=names, captions=captions, show_recursion_tree=bool(tree and tree.recursive),
                      insight=insight)


def apply_plan(run: DryRun, plan: VisualPlan) -> DryRun:
    """Reorder each step's structures by the plan and attach captions."""
    order = {name: i for i, name in enumerate(plan.focus)}
    steps = []
    for step in run.steps:
        structures = sorted(step.data_structures, key=lambda d: order.get(d.name, len(order)))
        structures = [d.model_copy(update={"caption": plan.captions.get(d.name, d.caption)}) for d in structures]
        steps.append(step.model_copy(update={"data_structures": structures,
                                             "data_structure_state": structures[0] if structures else None}))
    return run.model_copy(update={"steps": steps, "plan": plan})


def merge_plan(result: AnalysisResult, data: Any) -> AnalysisResult:
    """Validate the model's plan against the real trace and apply it (else keep the default)."""
    if not isinstance(data, dict) or not result.dry_run.steps:
        return result
    try:
        proposed = VisualPlan.model_validate(data)
    except ValidationError:
        return result
    real = {n for n, _ in available_structures(result.dry_run)}
    base = result.dry_run.plan or default_plan(result.dry_run)
    focus = [n for n in proposed.focus if n in real] + [n for n in base.focus if n not in proposed.focus]
    plan = VisualPlan(
        focus=focus,
        captions={**base.captions, **{k: v[:160] for k, v in proposed.captions.items() if k in real and v}},
        show_recursion_tree=base.show_recursion_tree if proposed.show_recursion_tree is None
        else proposed.show_recursion_tree and bool(result.dry_run.call_tree and result.dry_run.call_tree.recursive),
        insight=(proposed.insight or base.insight)[:240],
    )
    return result.model_copy(update={"dry_run": apply_plan(result.dry_run, plan)})
