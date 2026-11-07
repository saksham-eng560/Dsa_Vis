"""Offline knowledge for well-known algorithms.

Used when no LLM is reachable so the Explain tab still teaches something
useful. The LLM output always overrides these entries.
"""

from api.schemas.response import AnalysisResult, KeyConcept

_KB: dict[str, dict] = {
    "Bubble Sort": {
        "summary": "Bubble Sort repeatedly walks through the list, swapping adjacent elements that are out of order, so the largest remaining value 'bubbles' to the end on every pass.",
        "concepts": [("Adjacent swaps", "Compare neighbours and swap when out of order.", "The inner loop compares arr[j] and arr[j+1]."),
                     ("Early termination", "Stop when a full pass makes no swaps.", "A `swapped` flag turns the best case into O(n).")],
        "edge": ["Empty list", "Already sorted input (best case)", "Reverse-sorted input (worst case)", "Duplicate values (sort is stable)"],
        "opt": ["Track whether any swap happened and stop early", "Shrink the inner loop by i each pass", "Use an O(n log n) sort for large inputs"],
        "related": ["Insertion Sort", "Selection Sort", "Cocktail Shaker Sort"],
    },
    "Binary Search": {
        "summary": "Binary Search finds a target in a sorted array by repeatedly halving the search interval, comparing the middle element and discarding the half that cannot contain the target.",
        "concepts": [("Divide and conquer", "Halve the problem each step.", "lo/hi shrink around mid."),
                     ("Loop invariant", "The target, if present, is always within [lo, hi].", "Guarantees correctness.")],
        "edge": ["Empty array", "Target smaller/larger than every element", "Duplicates (which index is returned?)", "Integer overflow computing mid in fixed-width languages"],
        "opt": ["Use lo + (hi - lo) // 2 to avoid overflow", "Use bisect for lower/upper bounds"],
        "related": ["Lower/Upper Bound", "Ternary Search", "Exponential Search"],
    },
    "Merge Sort": {
        "summary": "Merge Sort splits the list in half recursively until single elements remain, then merges the sorted halves back together.",
        "concepts": [("Divide and conquer", "Split, solve, combine.", "Two recursive calls on halves."),
                     ("Merging", "Combine two sorted lists in linear time.", "Two pointers walk both halves.")],
        "edge": ["Empty or single-element list", "Many duplicates (stable)"],
        "opt": ["Switch to insertion sort for small slices", "Merge in place with an auxiliary buffer to avoid repeated slicing"],
        "related": ["Quick Sort", "Timsort", "Counting Inversions"],
    },
    "Quick Sort": {
        "summary": "Quick Sort picks a pivot, partitions the array so smaller elements go left and larger go right, then sorts both sides recursively.",
        "concepts": [("Partitioning", "Rearrange around a pivot in place.", "Lomuto/Hoare partition scheme."),
                     ("Pivot choice", "Balanced splits give O(n log n).", "Sorted input with last-element pivot gives O(n²).")],
        "edge": ["Already sorted input with a fixed pivot", "All-equal elements", "Recursion depth on skewed splits"],
        "opt": ["Randomised or median-of-three pivot", "Three-way partition for duplicates", "Recurse on the smaller side first"],
        "related": ["Quickselect", "Merge Sort", "Introsort"],
    },
    "Breadth-First Search": {
        "summary": "BFS explores a graph level by level from a start vertex using a queue, visiting every vertex reachable from it.",
        "concepts": [("Queue (FIFO)", "Process vertices in discovery order.", "deque.popleft()."),
                     ("Visited set", "Never enqueue a vertex twice.", "Keeps the work at O(V + E).")],
        "edge": ["Disconnected graph", "Self-loops and cycles", "Start vertex missing from graph"],
        "opt": ["Mark visited when enqueuing, not when dequeuing", "Store parents to rebuild shortest paths"],
        "related": ["Depth-First Search", "Dijkstra's Algorithm", "Topological Sort"],
    },
    "Fibonacci": {
        "summary": "Computes Fibonacci numbers, where each number is the sum of the previous two.",
        "concepts": [("Recursion", "A function defined in terms of itself.", "fib(n) calls fib(n-1) and fib(n-2)."),
                     ("Overlapping sub-problems", "The same calls repeat many times.", "Memoisation turns O(2ⁿ) into O(n).")],
        "edge": ["n = 0 or 1", "Negative n", "Large n (recursion depth / big integers)"],
        "opt": ["Memoise with functools.lru_cache", "Iterate with two variables for O(1) space", "Matrix exponentiation for O(log n)"],
        "related": ["Climbing Stairs", "Dynamic Programming", "Tribonacci"],
    },
    "Two Sum (Hash Map)": {
        "summary": "Finds two numbers that add up to a target by storing each value's index in a hash map and checking whether the complement was already seen.",
        "concepts": [("Hash map lookup", "O(1) average membership tests.", "`target - x in seen`."),
                     ("One-pass", "Check before inserting.", "Avoids using the same element twice.")],
        "edge": ["No valid pair", "Duplicate values", "Negative numbers"],
        "opt": ["Sort + two pointers if indices are not needed (O(1) extra space)"],
        "related": ["3Sum", "Two Pointers", "Subarray Sum Equals K"],
    },
}


def enrich_offline(result: AnalysisResult) -> AnalysisResult:
    """Fill teaching fields for recognised algorithms (no-op for custom code)."""
    entry = _KB.get(result.algorithm_name)
    if entry is None:
        return result
    return result.model_copy(update={
        "summary": entry["summary"] + " " + result.summary.split(" — ", 1)[-1].capitalize(),
        "key_concepts": [KeyConcept(concept=c, explanation=e, relevance=r) for c, e, r in entry["concepts"]],
        "edge_cases": entry["edge"],
        "optimizations": entry["opt"],
        "related_algorithms": entry["related"],
    })
