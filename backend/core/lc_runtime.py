"""LeetCode execution model: the judge-like prelude, turning LeetCode-format test
inputs (one JSON value per line) into Python setup/call code, and comparing outputs.

All code generated here is trusted harness code; user values are embedded only
via `repr()` of parsed JSON, never as raw text.
"""

import json
import keyword
import math
from dataclasses import dataclass
from typing import Any

from api.schemas.leetcode import CompareMode, LCProblem

# Mirrors the names LeetCode's Python 3 environment pre-imports, plus the
# ListNode/TreeNode definitions and (de)serialisers. Runs untraced.
PRELUDE = '''
import collections, heapq, math, bisect, itertools, functools, string, re, operator
from collections import deque, defaultdict, Counter, OrderedDict
from functools import lru_cache, cache, reduce
from heapq import heappush, heappop, heapify, heappushpop, nlargest, nsmallest
from bisect import bisect_left, bisect_right, insort
from itertools import accumulate, permutations, combinations, product
from math import inf, gcd, sqrt, ceil, floor, comb
from typing import List, Optional, Dict, Set, Tuple

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def _lc_list(vals):
    head = tail = None
    for v in vals:
        node = ListNode(v)
        if head is None:
            head = tail = node
        else:
            tail.next = node
            tail = node
    return head

def _lc_tree(vals):
    if not vals or vals[0] is None:
        return None
    root = TreeNode(vals[0])
    queue, i = deque([root]), 1
    while queue and i < len(vals):
        node = queue.popleft()
        for side in ("left", "right"):
            if i < len(vals) and vals[i] is not None:
                child = TreeNode(vals[i])
                setattr(node, side, child)
                queue.append(child)
            i += 1
    return root

def _lc_out(x):
    if isinstance(x, ListNode):
        out, seen = [], set()
        while x is not None and id(x) not in seen and len(out) < 10000:
            seen.add(id(x)); out.append(_lc_out(x.val)); x = x.next
        return out
    if isinstance(x, TreeNode):
        out, queue = [], deque([x])
        while queue and len(out) < 10000:
            node = queue.popleft()
            if node is None:
                out.append(None)
            else:
                out.append(_lc_out(node.val)); queue.append(node.left); queue.append(node.right)
        while out and out[-1] is None:
            out.pop()
        return out
    if isinstance(x, (list, tuple)):
        return [_lc_out(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted((_lc_out(v) for v in x), key=repr)
    if isinstance(x, dict):
        return {str(k): _lc_out(v) for k, v in x.items()}
    return x

def _lc_out_node(x):
    return [] if x is None else _lc_out(x)  # LeetCode prints an empty list/tree as []

def _lc_design(ns, operations, arguments):
    obj = ns[operations[0]](*arguments[0])
    out = [None]
    for op, args in zip(operations[1:], arguments[1:]):
        out.append(_lc_out(getattr(obj, op)(*args)))
    return out
'''

_LIST_TYPES = {"ListNode[]", "list<ListNode>"}


class TestInputError(ValueError):
    """A test case's input lines do not match the problem's parameters."""

    __test__ = False  # not a pytest test class


@dataclass(frozen=True)
class PreparedTest:
    setup: str  # binds each parameter as a global (visible in the variable watch)
    call: str  # expression whose value is the judged output
    label: str  # LeetCode-style "nums = [2,7,11,15], target = 9"


def parse_value(line: str, what: str) -> Any:
    """Parse one LeetCode input/output line (JSON: true/false/null, "str", [..])."""
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError as exc:
        hint = 'use JSON, e.g. [1,2,3], "abc", true'
        raise TestInputError(f"{what}: `{line.strip()[:60]}` is not valid ({hint})") from exc


def _ident(name: str) -> str:
    if not name.isidentifier() or keyword.iskeyword(name):
        raise TestInputError(f"Unsupported parameter name `{name}`")
    return name


def prepare_test(problem: LCProblem, lines: list[str]) -> PreparedTest:
    """Build setup + call code for one test case of `problem`."""
    lines = [ln for ln in lines if ln.strip()]
    if problem.design:
        if len(lines) != 2:
            raise TestInputError("Design problems need 2 lines: the operations list and the arguments list")
        ops, args = parse_value(lines[0], "operations"), parse_value(lines[1], "arguments")
        if not (isinstance(ops, list) and isinstance(args, list) and len(ops) == len(args) and ops):
            raise TestInputError("operations and arguments must be lists of the same length")
        # dunder names keep the raw inputs out of the variable watch / visualiser focus
        setup = f"__operations = {ops!r}\n__arguments = {args!r}\n"
        return PreparedTest(setup, "_lc_design(globals(), __operations, __arguments)",
                            f"operations = {lines[0].strip()}, arguments = {lines[1].strip()}")

    params = problem.params
    if len(lines) != len(params):
        names = ", ".join(p.name for p in params)
        raise TestInputError(f"Expected {len(params)} input line(s) ({names}), got {len(lines)}")
    setup, labels = [], []
    for param, line in zip(params, lines, strict=True):
        name = _ident(param.name)
        value = parse_value(line, name)
        if param.type == "ListNode":
            expr = f"_lc_list({value!r})"
        elif param.type == "TreeNode":
            expr = f"_lc_tree({value!r})"
        elif param.type in _LIST_TYPES:
            expr = f"[_lc_list(_v) for _v in {value!r}]"
        else:
            expr = repr(value)
        setup.append(f"{name} = {expr}")
        labels.append(f"{name} = {line.strip()}")
    names = ", ".join(p.name for p in params)
    call = f"Solution().{_ident(problem.function_name or 'solve')}({names})"
    if problem.output_param is not None and 0 <= problem.output_param < len(params):
        call = f"({call}, {params[problem.output_param].name})[1]"  # in-place problems
    wrap = "_lc_out_node" if problem.return_type in ("ListNode", "TreeNode") else "_lc_out"
    return PreparedTest("\n".join(setup) + "\n", f"{wrap}({call})", ", ".join(labels))


# --------------------------------------------------------------- judging ----
def _canon(value: Any, nested: bool) -> Any:
    """Order-insensitive canonical form used by the unordered compare modes."""
    if isinstance(value, list):
        items = [_canon(v, nested) if nested else v for v in value]
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True))
    return value


def _equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b if isinstance(a, bool) and isinstance(b, bool) else False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-5)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b, strict=True))
    return a == b


def outputs_match(actual: Any, expected: Any, mode: CompareMode) -> bool:
    """LeetCode-style comparison: exact, any order, or any order at every level."""
    if mode == "unordered":
        return _equal(_canon(actual, False), _canon(expected, False))
    if mode == "unordered_nested":
        return _equal(_canon(actual, True), _canon(expected, True))
    return _equal(actual, expected)
