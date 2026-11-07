"""Problem catalog, input preparation, output comparison and the sandboxed judge."""

import pytest

from api.schemas.leetcode import LCTestCase
from core.lc_judge import run_tests
from core.lc_problem import catalog, catalog_summaries, normalize_ref, py_type
from core.lc_runtime import TestInputError, outputs_match, prepare_test

TWO_SUM = (
    "class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n"
    "        for i, x in enumerate(nums):\n            if target - x in seen:\n"
    "                return [i, seen[target - x]]\n            seen[x] = i\n"
)


def examples(pid: str) -> list[LCTestCase]:
    return [LCTestCase(input=e.input, expected=e.expected) for e in catalog()[pid].examples]


def test_catalog_is_complete_and_indexed() -> None:
    summaries = catalog_summaries()
    assert len(summaries) >= 20 and [int(s.id) for s in summaries] == sorted(int(s.id) for s in summaries)
    for s in summaries:
        p = catalog()[s.id]
        assert catalog()[s.slug] is p and p.examples and p.starter_code
        for ex in p.examples:  # every bundled example input must be preparable
            prepare_test(p, ex.input)


@pytest.mark.parametrize("ref,key", [
    ("1", "1"), (" 0206 ", "206"), ("Two Sum", "two-sum"),
    ("https://leetcode.com/problems/two-sum/description/", "two-sum"), ("valid-parentheses", "valid-parentheses"),
])
def test_normalize_ref(ref: str, key: str) -> None:
    assert normalize_ref(ref) == key


@pytest.mark.parametrize("lc,py", [
    ("integer", "int"), ("integer[][]", "List[List[int]]"), ("character[][]", "List[List[str]]"),
    ("TreeNode", "Optional[TreeNode]"), ("ListNode[]", "List[ListNode]"), ("list<string>", "List[str]"),
])
def test_py_type(lc: str, py: str) -> None:
    assert py_type(lc) == py


def test_prepare_test_builds_structures_and_labels() -> None:
    t = prepare_test(catalog()["21"], ["[1,2,4]", "[1,3,4]"])
    assert "list1 = _lc_list([1, 2, 4])" in t.setup and t.call.startswith("_lc_out_node(")
    assert t.label == "list1 = [1,2,4], list2 = [1,3,4]"
    assert "(Solution().moveZeroes(nums), nums)[1]" in prepare_test(catalog()["283"], ["[0,1]"]).call
    assert prepare_test(catalog()["146"], ['["LRUCache"]', "[[1]]"]).call.startswith("_lc_design(")
    with pytest.raises(TestInputError, match="Expected 2 input line"):
        prepare_test(catalog()["1"], ["[1,2]"])
    with pytest.raises(TestInputError, match="not valid"):
        prepare_test(catalog()["1"], ["[1,2", "3"])


def test_outputs_match_modes() -> None:
    assert outputs_match([1, 0], [0, 1], "unordered") and not outputs_match([1, 0], [0, 1], "exact")
    assert outputs_match([[2, 1], [3]], [[3], [1, 2]], "unordered_nested")
    assert outputs_match(2.000001, 2.0, "exact") and not outputs_match(True, 1, "exact")


async def test_judge_verdicts() -> None:
    res = await run_tests(catalog()["1"], TWO_SUM, examples("1"), None, 256)
    assert (res.passed, res.total, res.compare) == (3, 3, "unordered")
    wrong = await run_tests(catalog()["20"], "class Solution:\n    def isValid(self, s):\n        return True\n",
                            examples("20"), None, 256)
    assert [r.status for r in wrong.results] == ["passed", "passed", "failed", "passed"]
    assert wrong.results[2].output == "true" and wrong.results[2].expected == "false"


async def test_judge_structures_design_and_in_place() -> None:
    rev = "class Solution:\n    def reverseList(self, head):\n        prev = None\n        while head:\n" \
          "            head.next, prev, head = prev, head, head.next\n        return prev\n"
    assert (await run_tests(catalog()["206"], rev, examples("206"), None, 256)).passed == 3
    stack = ("class MinStack:\n    def __init__(self):\n        self.s = []\n    def push(self, val):\n"
             "        self.s.append((val, min(val, self.s[-1][1] if self.s else val)))\n"
             "    def pop(self):\n        self.s.pop()\n    def top(self):\n        return self.s[-1][0]\n"
             "    def getMin(self):\n        return self.s[-1][1]\n")
    assert (await run_tests(catalog()["155"], stack, examples("155"), None, 256)).passed == 1
    mz = "class Solution:\n    def moveZeroes(self, nums):\n        nums.sort(key=lambda x: x == 0)\n"
    assert (await run_tests(catalog()["283"], mz, examples("283"), None, 256)).passed == 2


async def test_judge_errors_timeouts_and_custom_tests() -> None:
    loop = "class Solution:\n    def climbStairs(self, n):\n        while True:\n            pass\n"
    res = await run_tests(catalog()["70"], loop, examples("70")[:1], None, 256)
    assert res.results[0].status == "timeout"
    crash = ("class Solution:\n    def twoSum(self, nums, target):\n"
             "        print('dbg', nums)\n        return nums[99]\n")
    res = await run_tests(catalog()["1"], crash, [LCTestCase(input=["[1,2]", "3"])], None, 256)
    assert res.results[0].status == "error" and "IndexError" in res.results[0].error
    assert res.results[0].stdout == "dbg [1, 2]\n"
    custom = [LCTestCase(input=["[5,5]", "10"], expected="[0,1]"), LCTestCase(input=["[1,4]", "5"]),
              LCTestCase(input=["oops", "1"])]
    res = await run_tests(catalog()["1"], TWO_SUM, custom, None, 256)
    assert [r.status for r in res.results] == ["passed", "ran", "error"]
    res = await run_tests(catalog()["1"], "def twoSum(nums, target)\n", examples("1"), None, 256)
    assert res.error and "SyntaxError" in res.error and res.passed == 0
