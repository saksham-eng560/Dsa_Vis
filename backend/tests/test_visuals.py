"""Recursion trees and AI visual plans."""

import json

import pytest

from api.schemas.response import AnalysisResult
from core.cpp_tracer import trace_cpp_problem
from core.lc_problem import catalog
from core.tracer import trace_python
from core.visual_plan import default_plan, merge_plan
from sandbox.native import find_compiler
from tests.conftest import FakeLLM

USER_CPP = (  # the exact solution from the bug report
    "class Solution {\nprivate:\n    int f(int i,int n) {\n        if(i == n) return 1;\n"
    "        if(i > n) return 0;\n\n"
    "        int onestep = f(i+1,n);\n        int twostep = f(i+2,n);\n\n        return onestep + twostep;\n    }\n"
    "public:\n    int climbStairs(int n) {\n        return f(0,n);\n    }\n};\n"
)
MEMO = ("def climb(n, memo={}):\n    if n <= 1:\n        return 1\n    if n in memo:\n        return memo[n]\n"
        "    memo[n] = climb(n - 1) + climb(n - 2)\n    return memo[n]\n\nprint(climb(5))\n")
NAIVE = "def climb(n):\n    if n <= 1:\n        return 1\n    return climb(n - 1) + climb(n - 2)\n\nprint(climb(5))\n"


@pytest.mark.skipif(find_compiler() is None, reason="no C++ compiler")
async def test_cpp_recursion_tree_for_plain_recursion() -> None:
    run = await trace_cpp_problem(catalog()["70"], USER_CPP, ["4"], "n = 4", max_steps=400, memory_mb=512)
    tree = run.call_tree
    assert tree and tree.recursive and run.error is None
    f_calls = [n for n in tree.nodes if n.func == "f"]
    assert len(f_calls) == 15 and tree.repeated == 3  # f(2,4) once, f(3,4) twice; base cases don't count
    root = next(n for n in f_calls if n.args == "0, 4")
    assert root.ret == "5" and root.end is not None
    assert {n.ret for n in f_calls if n.args == "4, 4"} == {"1"}
    children = [n for n in tree.nodes if n.parent == root.id]
    assert [c.args for c in children] == ["1, 4", "2, 4"]


async def test_memo_vs_naive_repeated_subproblems() -> None:
    memo = (await trace_python(MEMO, None, max_steps=400, timeout_s=5, memory_mb=256)).call_tree
    naive = (await trace_python(NAIVE, None, max_steps=400, timeout_s=5, memory_mb=256)).call_tree
    assert memo and naive and memo.recursive and naive.recursive
    assert [n.args for n in memo.nodes][:3] == ["5", "4", "3"]  # shared memo dict kept out of labels
    assert (len(memo.nodes), memo.repeated, memo.cache_hits) == (9, 0, 2)  # repeats answered by the memo
    assert (len(naive.nodes), naive.repeated, naive.cache_hits) == (15, 3, 0)  # naive redoes climb(3), climb(2)×2


async def test_iterative_code_has_no_recursion_tree_flag() -> None:
    run = await trace_python("def f(a):\n    return sum(a)\n\nprint(f([1, 2]))\n", None, max_steps=100,
                             timeout_s=5, memory_mb=256)
    assert run.call_tree is not None and not run.call_tree.recursive


async def test_plan_is_validated_against_the_trace() -> None:
    code = ("def lcs(a, b):\n    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]\n    seen = {}\n"
            "    for i in range(1, len(a) + 1):\n        for j in range(1, len(b) + 1):\n            seen[i] = j\n"
            "            dp[i][j] = dp[i-1][j-1] + 1 if a[i-1] == b[j-1] else max(dp[i-1][j], dp[i][j-1])\n"
            "    return dp[-1][-1]\n\nprint(lcs('AB', 'B'))\n")
    run = await trace_python(code, None, max_steps=400, timeout_s=5, memory_mb=256)
    result = AnalysisResult(language="python", dry_run=run)
    plan = {"focus": ["seen", "ghost_var", "dp"], "captions": {"dp": "dp[i][j] = LCS of prefixes", "ghost_var": "x"},
            "show_recursion_tree": True, "insight": "Watch each cell come from its neighbours."}
    merged = merge_plan(result, plan).dry_run
    assert merged.plan.focus[:2] == ["seen", "dp"] and "ghost_var" not in merged.plan.focus
    assert merged.plan.show_recursion_tree is False  # no recursion in this code
    last = next(s for s in reversed(merged.steps) if len(s.data_structures) >= 2)
    assert [d.name for d in last.data_structures][:2] == ["seen", "dp"]
    assert next(d for d in last.data_structures if d.name == "dp").caption == "dp[i][j] = LCS of prefixes"
    assert merge_plan(result, "garbage") is result


async def test_default_plan_explains_repeated_work() -> None:
    run = await trace_python(NAIVE, None, max_steps=400, timeout_s=5, memory_mb=256)
    plan = default_plan(run)
    assert plan.show_recursion_tree and "3 of 15" in plan.insight


async def test_ai_plan_reaches_the_api(make_client) -> None:
    llm = FakeLLM(json.dumps({"summary": "Counts stairs.", "visual_plan": {
        "focus": ["memo"], "captions": {"memo": "memo[n] = ways to climb n stairs"},
        "insight": "Green calls are cache hits."}}))
    async with make_client(llm) as client:
        body = (await client.post("/api/analyze", json={"code": MEMO})).json()
    run = body["dry_run"]
    assert run["plan"]["insight"] == "Green calls are cache hits."
    assert run["call_tree"]["recursive"] and run["plan"]["show_recursion_tree"]
    shown = [s for s in run["steps"] if s["data_structures"]]
    assert shown[-1]["data_structures"][0]["caption"] == "memo[n] = ways to climb n stairs"
    assert "Recursion: yes" in llm.prompts[0] and "memo (hash_map)" in llm.prompts[0]


INORDER_CPP = (
    "class Solution {\n    vector<int> ans;\nprivate:\n    void inorder(TreeNode* root) {\n"
    "        if(root == NULL) return;\n        inorder(root->left);\n        ans.push_back(root->val);\n"
    "        inorder(root->right);\n    }\npublic:\n    vector<int> inorderTraversal(TreeNode* root) {\n"
    "        inorder(root);\n        return ans;\n    }\n};\n"
)


@pytest.mark.skipif(find_compiler() is None, reason="no C++ compiler")
async def test_large_cpp_trace_is_not_truncated() -> None:
    big = "[" + ",".join(str(i) for i in range(1, 32)) + "]"  # 31-node tree: a multi-MB trace
    run = await trace_cpp_problem(catalog()["94"], INORDER_CPP, [big], "root", max_steps=400, memory_mb=512)
    assert run.error is None and run.steps and run.call_tree
    assert [n.args for n in run.call_tree.nodes[:3]] == ["node 1", "node 1", "node 2"]
    assert all(n.ret is None for n in run.call_tree.nodes if n.func == "inorder")  # void: no badges
