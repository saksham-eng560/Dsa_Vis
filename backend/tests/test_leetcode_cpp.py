"""C++ LeetCode support: types, starter code, literals and the compiled judge."""

import pytest

from api.schemas.leetcode import LCTestCase
from core.lc_cpp import cpp_type, literal
from core.lc_judge_cpp import run_cpp_tests
from core.lc_problem import catalog
from core.lc_runtime import TestInputError
from sandbox.native import find_compiler

needs_cxx = pytest.mark.skipif(find_compiler() is None, reason="no C++ compiler")


def examples(pid: str) -> list[LCTestCase]:
    return [LCTestCase(input=e.input, expected=e.expected) for e in catalog()[pid].examples]


@pytest.mark.parametrize("lc,cpp", [
    ("integer", "int"), ("integer[][]", "vector<vector<int>>"), ("character[][]", "vector<vector<char>>"),
    ("list<string>", "vector<string>"), ("TreeNode", "TreeNode*"), ("long", "long long"),
])
def test_cpp_type(lc: str, cpp: str) -> None:
    assert cpp_type(lc) == cpp


def test_literals() -> None:
    assert literal([[1, 2], []], "integer[][]") == "vector<vector<int>>{vector<int>{1, 2}, vector<int>{}}"
    assert literal('a"b', "string") == 'string("a\\"b")'
    assert literal("x", "character") == "'x'"
    assert literal([3, None, 4], "TreeNode") == '_lc_tree({"3", "null", "4"})'
    with pytest.raises(TestInputError):
        literal(5, "integer[]")


def test_every_bundled_problem_has_cpp_starter() -> None:
    for p in {p.slug: p for p in catalog().values()}.values():
        assert p.starter_code_cpp, p.slug
    assert "vector<int> twoSum(vector<int>& nums, int target)" in catalog()["1"].starter_code_cpp
    assert "class MinStack {" in catalog()["155"].starter_code_cpp


@needs_cxx
async def test_cpp_judge_verdicts() -> None:
    two_sum = ("class Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n"
               "        unordered_map<int, int> m;\n        for (int i = 0; i < (int)nums.size(); i++) {\n"
               "            if (m.count(target - nums[i])) return {m[target - nums[i]], i};\n"
               "            m[nums[i]] = i;\n        }\n        return {};\n    }\n};\n")
    res = await run_cpp_tests(catalog()["1"], two_sum, examples("1"), None, 512)
    assert (res.passed, res.total, res.error) == (3, 3, None)
    tree = ("#include <bits/stdc++.h>\nclass Solution {\npublic:\n    TreeNode* invertTree(TreeNode* root) {\n"
            "        if (!root) return nullptr;\n        swap(root->left, root->right);\n"
            "        invertTree(root->left);\n        invertTree(root->right);\n        return root;\n    }\n};\n")
    assert (await run_cpp_tests(catalog()["226"], tree, examples("226"), None, 512)).passed == 3


@needs_cxx
async def test_cpp_judge_failures() -> None:
    crash = "class Solution {\npublic:\n    int maxDepth(TreeNode* root) { return root->left->left->val; }\n};\n"
    res = await run_cpp_tests(catalog()["104"], crash, examples("104"), None, 512)
    assert res.results[0].status == "error" and "Runtime Error" in (res.results[0].error or "")
    loop = "class Solution {\npublic:\n    int climbStairs(int n) { volatile int x = 0; while (true) x++; }\n};\n"
    assert (await run_cpp_tests(catalog()["70"], loop, examples("70")[:1], None, 512)).results[0].status == "timeout"
    res = await run_cpp_tests(catalog()["1"], "class Solution { int x = }", examples("1"), None, 512)
    assert res.error and res.error.startswith("Compile Error") and res.passed == 0
    printing = ('class Solution {\npublic:\n    bool isValid(string s) { cout << "len " << s.size() << endl; '
                "return true; }\n};\n")
    res = await run_cpp_tests(catalog()["20"], printing, examples("20")[:1], None, 512)
    assert res.results[0].status == "passed" and res.results[0].stdout == "len 2\n"
