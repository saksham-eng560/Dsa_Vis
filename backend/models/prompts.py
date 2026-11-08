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

# A *complete* worked example. Small models copy the example's length and depth,
# so it is deliberately rich: multi-sentence summary, intuition, line-referenced
# steps, why it works, mistakes. It describes `_EXAMPLE_CODE`, shown alongside it.
_EXAMPLE_CODE = """def max_subarray(nums):
    best = cur = nums[0]
    for x in nums[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best"""

_EXAMPLE_INSIGHT = {
    "summary": "Finds the largest sum of any contiguous slice of the list using Kadane's algorithm. "
               "It walks through the numbers once, keeping the best sum of a slice that ends at the current "
               "position (`cur`) and the best sum seen anywhere so far (`best`). At the end `best` is the answer.",
    "algorithm_name": "Kadane's Algorithm (Maximum Subarray)",
    "data_structures_used": ["array"],
    "intuition": "A slice with a negative running total can only drag down whatever comes after it, so the moment "
                 "extending is worse than starting fresh, we drop the past and restart at the current number.",
    "approach": [
        "Line 2: start both `best` and `cur` at the first element, so a list of all negatives still works.",
        "Line 3: visit every remaining number `x` once, from left to right.",
        "Line 4: either extend the previous slice (`cur + x`) or start a new slice at `x` — keep the larger.",
        "Line 5: if the slice ending here beats the record, update `best`.",
        "Line 6: return `best`, the largest slice sum found.",
    ],
    "why_it_works": "Every subarray ends somewhere. `cur` is always the best sum of a subarray ending at the current "
                    "index (a tiny dynamic-programming recurrence), so taking the maximum over all ending positions "
                    "in `best` covers every possible subarray.",
    "complexity": {
        "time": {"best": "O(n)", "average": "O(n)", "worst": "O(n)",
                 "explanation": "The loop on line 3 visits each of the n numbers exactly once and does O(1) work "
                                "per number (two max calls), so the total work grows linearly."},
        "space": {"complexity": "O(1)",
                  "explanation": "Only two integers (`best`, `cur`) are stored, no matter how long the list is."},
    },
    "key_concepts": [
        {"concept": "Dynamic programming", "explanation": "Build the answer for position i from the answer for i-1.",
         "relevance": "`cur` at line 4 reuses the previous `cur` instead of re-summing slices."},
        {"concept": "Greedy restart", "explanation": "Discard a prefix as soon as it can't help any more.",
         "relevance": "`max(x, cur + x)` restarts the slice when the running sum is negative."},
    ],
    "edge_cases": [
        "All negative numbers — the answer is the largest single element; starting at nums[0] handles it.",
        "A single element — the loop body never runs and nums[0] is returned.",
        "Empty list — nums[0] raises an error; guard it if empty input is allowed.",
    ],
    "optimizations": [
        "Already optimal at O(n) time / O(1) space; track start/end indices too if you need the slice itself.",
    ],
    "common_mistakes": [
        "Initialising `best = 0`, which returns 0 for an all-negative list.",
        "Resetting `cur` to 0 instead of to `x`, which breaks negative-only inputs.",
    ],
    "related_algorithms": ["Maximum Product Subarray", "Best Time to Buy and Sell Stock", "Prefix sums"],
    "visual_plan": {
        "focus": ["nums"],
        "captions": {"nums": "the input — the blue pointer is the element x being added to the running slice"},
        "show_recursion_tree": False,
        "insight": "Watch `cur` reset to x whenever the running sum turns negative — that is the restart rule.",
    },
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
        f"You are teaching a student how THEIR {language} code works. Here it is "
        "(line numbers on the left are for reference only):",
        _numbered(code),
        f"Static analyzer notes (heuristic, may be wrong — correct them if needed):\n{hints}",
        "Here is an example of the depth and style expected, for a DIFFERENT piece of code:",
        _numbered(_EXAMPLE_CODE),
        json.dumps(_EXAMPLE_INSIGHT, ensure_ascii=False),
        "Now write the same JSON (exactly these keys) for the student's code above. Requirements: "
        "summary = 2-4 sentences explaining what it does and how; intuition = the core idea in plain words; "
        "approach = 3-7 steps that each start with the real line number (\"Line N: …\") and use the student's "
        "variable names; why_it_works = 2-3 sentences; complexity explanations must say WHICH loops/calls cause the "
        "cost; 2-4 key_concepts; 3-5 edge_cases saying what happens; 1-3 optimizations (or say it's optimal and "
        "why); 2-3 common_mistakes; 2-4 related_algorithms. Use Big-O notation like O(1), O(log n), O(n), "
        "O(n log n), O(n²), O(2ⁿ). visual_plan: decide what the student should SEE for this problem — focus = "
        "the traced variables (only from the list in the notes) in order of importance; captions = what each "
        "variable means for THIS problem (e.g. \"dp[i] = ways to reach stair i\"); show_recursion_tree = true "
        "for recursive solutions; insight = one sentence on what to watch in the animation.",
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
        "Explain it like I'm 5: short sentences, one everyday analogy carried through every field (toys, a "
        "queue at a shop, sorting cards), no jargon. The approach steps should still follow the code's lines, "
        "but in simple words."
        if eli5 else
        "Explain it for a computer-science student: precise, step by step, naming the technique."
    )
    keys = {k: _EXAMPLE_INSIGHT[k] for k in _EXPLAIN_KEYS}
    return "\n\n".join([
        f"Explain what this {language} code does.",
        _numbered(code),
        style,
        "Respond with JSON using exactly these keys (example values are for a different program — "
        "match their depth, not their content):",
        json.dumps(keys, ensure_ascii=False),
    ])


_EXPLAIN_KEYS = ("summary", "algorithm_name", "intuition", "approach", "why_it_works", "key_concepts",
                 "edge_cases", "optimizations", "common_mistakes", "related_algorithms")


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
