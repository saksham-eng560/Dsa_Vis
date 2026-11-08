"""Offline concept detection from code patterns (any language).

Fills the Explain tab when no LLM is available or it returns nothing, so
custom code and LeetCode solutions still get useful teaching notes.
"""

import re

from api.schemas.response import AnalysisResult, KeyConcept

# (pattern, concept, explanation, relevance)
_PATTERNS: list[tuple[str, str, str, str]] = [
    (r"\bdp\b|memo|lru_cache|@cache|vector<\w+>\s*dp|dp\s*\[", "Dynamic Programming",
     "Solve each sub-problem once and reuse its answer instead of recomputing it.",
     "A table/memo stores intermediate results."),
    (r"unordered_map|unordered_set|HashMap|HashSet|\{\}|dict\(|defaultdict|Counter|\bset\(", "Hash Map / Set",
     "Average O(1) insert and lookup by key.", "Used to remember values seen so far."),
    (r"\b(lo|low|left|l)\b.*\b(hi|high|right|r)\b.*\bmid\b|\bmid\s*=", "Binary Search",
     "Halve the search range each step using a sorted order or a monotonic condition.",
     "`mid` splits the range between the two pointers."),
    (r"\b(left|l|i)\s*<\s*(right|r|j)\b|while\s*\(?\s*(left|l)\s*<", "Two Pointers",
     "Move two indices toward each other (or together) to scan in a single pass.",
     "Two indices narrow the window."),
    (r"\bwindow\b|\bstart\b.*\bend\b.*while", "Sliding Window",
     "Grow and shrink a contiguous window while keeping its state up to date.", "The window expands/contracts."),
    (r"\bstack\b|\.push_back\(.*\)\s*;.*\.pop_back|\bst\.push|\bstk\b", "Stack (LIFO)",
     "Last in, first out — ideal for matching pairs and next-greater problems.", "Items are pushed and popped."),
    (r"\bqueue\b|deque|popleft|\.front\(\)", "Queue / BFS",
     "First in, first out — explores items level by level.", "A queue holds the frontier."),
    (r"heapq|priority_queue|PriorityQueue", "Heap / Priority Queue",
     "Always gives the smallest (or largest) item in O(log n).", "A heap keeps the best candidate on top."),
    (r"sort\(|sorted\(|\.sort\(", "Sorting", "Ordering the data first often unlocks a simpler scan.",
     "The input is sorted before processing."),
    (r"->left|->right|\.left\b|\.right\b", "Tree Traversal", "Visit nodes recursively (DFS) or level by level (BFS).",
     "The code walks a binary tree."),
    (r"->next|\.next\b", "Linked List Pointers", "Re-wire `next` pointers carefully to avoid losing nodes.",
     "Nodes are traversed via `next`."),
    (r"\^|<<|>>|&\s*1\b|__builtin_popcount|bin\(", "Bit Manipulation", "Work with the binary representation directly.",
     "Bitwise operators are used."),
]


def detect_concepts(code: str, limit: int = 4) -> list[KeyConcept]:
    found = [KeyConcept(concept=c, explanation=e, relevance=r)
             for pattern, c, e, r in _PATTERNS if re.search(pattern, code, flags=re.S)]
    return found[:limit]


def generic_edge_cases(code: str) -> list[str]:
    cases = []
    if re.search(r"\[|vector|List|nums|arr", code):
        cases += ["Empty input", "Single element", "Duplicates and negative numbers"]
    if re.search(r"->left|\.left\b|->next|\.next\b", code):
        cases.append("Null / empty structure (no nodes)")
    if re.search(r"\bint\b.*[*+]", code):
        cases.append("Integer overflow on large values")
    return cases or ["Smallest possible input", "Largest allowed input (performance)"]


def fill_offline(result: AnalysisResult, code: str) -> AnalysisResult:
    """Add detected concepts / edge cases where nothing better exists."""
    update = {}
    if not result.key_concepts:
        update["key_concepts"] = detect_concepts(code)
    if not result.edge_cases:
        update["edge_cases"] = generic_edge_cases(code)
    return result.model_copy(update=update) if update else result
