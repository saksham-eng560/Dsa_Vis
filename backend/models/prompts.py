"""All LLM prompt templates.

Design notes (small local models, 7–10B):
* One system prompt fixes the role and the "JSON only" contract.
* The schema is shown as a compact few-shot *example*, not a JSON-Schema
  document — small models imitate examples far more reliably.
* Static-analysis facts are passed as hints so the model explains rather than
  guesses; the dry run is only requested when we could not trace the code.
* Prompts never ask for prose outside JSON; the backend repairs and validates
  whatever comes back (`core/json_utils.py`).
"""

import json

SYSTEM_PROMPT = (
    "You are CodeLens, an expert computer-science teacher and code analyst. "
    "You always answer with a single valid JSON object and nothing else — no markdown, "
    "no code fences, no commentary. Be precise, concise and correct."
)

_EXAMPLE_INSIGHT = {
    "summary": "Finds the largest number in a list by scanning it once and remembering the best value seen so far.",
    "algorithm_name": "Linear Scan (Maximum)",
    "data_structures_used": ["array"],
    "complexity": {
        "time": {"best": "O(n)", "average": "O(n)", "worst": "O(n)",
                 "explanation": "Every element is compared exactly once."},
        "space": {"complexity": "O(1)", "explanation": "Only one extra variable `best` is stored."},
    },
    "key_concepts": [{"concept": "Running maximum", "explanation": "Keep the best answer so far.",
                      "relevance": "`best` is updated whenever a larger value appears."}],
    "edge_cases": ["Empty list raises IndexError on nums[0]"],
    "optimizations": ["Use the built-in max(nums) for clarity"],
    "related_algorithms": ["Linear Search", "Kadane's Algorithm"],
}

_EXAMPLE_DRY_RUN = {
    "input_example": "nums = [3, 7, 2]",
    "steps": [
        {"step": 1, "line": 2, "description": "best starts at nums[0] = 3",
         "variables": {"best": "3"},
         "data_structure_state": {"type": "array", "name": "nums", "state": {"values": [3, 7, 2]},
                                  "highlights": [{"target": 0, "color": "green", "label": "best"}]}},
        {"step": 2, "line": 4, "description": "7 > 3, so best becomes 7",
         "variables": {"best": "7", "x": "7"},
         "data_structure_state": {"type": "array", "name": "nums", "state": {"values": [3, 7, 2]},
                                  "highlights": [{"target": 1, "color": "yellow", "label": "x"}]}},
    ],
}

_DS_SHAPES = (
    "data_structure_state.type is one of array|matrix|stack|queue|linked_list|tree|graph|hash_map|heap. "
    'state shapes: array/stack/queue/heap {"values": [...]}; matrix {"rows": [[...]]}; '
    'hash_map {"entries": [[key, value], ...]}; linked_list {"nodes": [{"id": "a", "value": 1}]}; '
    'tree {"root": {"id": "a", "value": 1, "children": [child_or_null, ...]}}; '
    'graph {"nodes": [{"id": "A", "label": "A"}], "edges": [{"source": "A", "target": "B"}], "directed": false}. '
    "highlights.target is an index (array), node id (tree/graph/list), key (hash_map) or [row, col] (matrix)."
)


def _numbered(code: str) -> str:
    return "\n".join(f"{i + 1:>3} | {line}" for i, line in enumerate(code.splitlines()))


def analysis_prompt(code: str, language: str, hints: str, need_dry_run: bool = False) -> str:
    """Insight prompt: summary, complexity, concepts, edge cases (no trace — see `dry_run_prompt`).

    Kept deliberately small so a 7B model answers in seconds and never truncates.
    `need_dry_run` is accepted for backwards compatibility and ignored.
    """
    del need_dry_run
    return "\n\n".join([
        f"Analyze this {language} code (line numbers on the left are for reference only):",
        _numbered(code),
        f"Static analyzer notes (heuristic, may be wrong — correct them if needed):\n{hints}",
        "Respond with JSON using exactly the keys of this example (values are illustrative):",
        json.dumps(_EXAMPLE_INSIGHT, ensure_ascii=False),
        "Complexities must use Big-O notation such as O(1), O(log n), O(n), O(n log n), O(n²), O(2ⁿ). "
        "Give 2-4 key_concepts and 2-5 edge_cases.",
    ])


def dry_run_prompt(code: str, language: str, input_label: str, title: str) -> str:
    """Focused trace prompt: execute the code by hand on ONE input, compactly."""
    what = f" (LeetCode “{title}”)" if title else ""
    given = (f"Trace it on exactly this input: {input_label}" if input_label
             else "Choose one small representative input and state it in input_example.")
    return "\n\n".join([
        f"Dry-run this {language} code{what} step by step, like a teacher at a whiteboard.",
        _numbered(code),
        given,
        "Respond with JSON exactly like this example (values are illustrative):",
        json.dumps(_EXAMPLE_DRY_RUN, ensure_ascii=False),
        "Rules: 8-20 steps; each step is one meaningful action (a comparison, an update, a call, a return); "
        "`line` is the real line number from the listing; `variables` holds only the important variables "
        "with short values; include data_structure_state whenever an array/grid/stack/map/list/tree/graph "
        "changes or is read. The last step must show the final return value in its description.",
        _DS_SHAPES,
    ])


def explain_prompt(code: str, language: str, eli5: bool) -> str:
    """Explanation-only prompt; `eli5` switches to a child-friendly register."""
    style = (
        "Explain it like I'm 5: short sentences, an everyday analogy (toys, lines at a shop, "
        "sorting cards), no jargon. Concepts should also be explained simply."
        if eli5 else
        "Explain it for a computer-science student: precise, step by step, naming the technique."
    )
    keys = {k: _EXAMPLE_INSIGHT[k] for k in
            ("summary", "algorithm_name", "key_concepts", "edge_cases", "optimizations", "related_algorithms")}
    return "\n\n".join([
        f"Explain what this {language} code does.",
        code,
        style,
        "Respond with JSON using exactly these keys:",
        json.dumps(keys, ensure_ascii=False),
    ])


CHAT_SYSTEM = (
    "You are CodeLens Tutor, a friendly expert in data structures, algorithms and C++/Python. "
    "Answer the student's question about THEIR code using the context provided. Be concise and concrete: "
    "refer to their variable names and line numbers, use short Markdown (bullets, `code`, ```code blocks```), "
    "and show small examples. If they ask for a hint, give a hint — not the full solution — unless they ask for it."
)


def chat_prompt(context: str, history: list[tuple[str, str]], question: str) -> str:
    """Single-turn prompt carrying the context and the last few exchanges (small-model friendly)."""
    turns = "\n\n".join(f"{'Student' if role == 'user' else 'Tutor'}: {text}" for role, text in history[-8:])
    return "\n\n".join(p for p in [
        f"## Context\n{context}",
        f"## Conversation so far\n{turns}" if turns else "",
        f"## Student's question\n{question}",
        "Answer as the Tutor:",
    ] if p)
