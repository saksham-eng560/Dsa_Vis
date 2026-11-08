"""HTTP-level tests with a scripted LLM injected through the app factory."""

import json

import pytest

from core.config import Settings
from sandbox.native import find_compiler
from tests.conftest import FakeLLM

BUBBLE = (
    "def bubble_sort(arr):\n"
    "    for i in range(len(arr)):\n"
    "        for j in range(len(arr) - i - 1):\n"
    "            if arr[j] > arr[j + 1]:\n"
    "                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
    "    return arr\n"
)
LLM_JSON = json.dumps({
    "summary": "Sorts by swapping neighbours.",
    "algorithm_name": "Bubble Sort",
    "data_structures_used": ["array"],
    "complexity": {"time": {"best": "O(n)", "average": "O(n²)", "worst": "O(n²)", "explanation": "nested"},
                   "space": {"complexity": "O(1)", "explanation": "in place"}},
    "key_concepts": [{"concept": "Swapping", "explanation": "x", "relevance": "y"}, {"bad": 1}],
    "edge_cases": ["empty"], "optimizations": ["early exit"], "related_algorithms": ["Insertion Sort"],
})


async def test_health(make_client) -> None:
    async with make_client() as client:
        res = await client.get("/api/health")
    assert res.status_code == 200 and res.json()["llm_available"] is False


async def test_analyze_static_only(make_client) -> None:
    async with make_client() as client:
        res = await client.post("/api/analyze", json={"code": BUBBLE})
    body = res.json()
    assert res.status_code == 200
    assert body["language"] == "python" and body["llm_used"] is False
    assert body["complexity"]["time"]["worst"] == "O(n²)"
    assert body["dry_run"]["source"] == "trace" and body["dry_run"]["input_example"].startswith("bubble_sort(")
    assert body["flowchart"]["nodes"] and body["key_concepts"]  # offline knowledge base


async def test_analyze_merges_llm_output(make_client) -> None:
    llm = FakeLLM("Sure!\n```json\n" + LLM_JSON + "\n```")
    async with make_client(llm) as client:
        body = (await client.post("/api/analyze", json={"code": BUBBLE})).json()
    assert body["llm_used"] is True and body["summary"] == "Sorts by swapping neighbours."
    assert body["complexity"]["source"] == "llm" and body["complexity"]["time"]["best"] == "O(n)"
    assert [c["concept"] for c in body["key_concepts"]] == ["Swapping"]  # invalid item dropped
    assert body["dry_run"]["source"] == "trace"  # real trace beats the LLM
    assert len(llm.prompts) == 1 and "Dry-run" not in llm.prompts[0]  # no AI trace for Python
    assert "Line N:" in llm.prompts[0] and "common_mistakes" in llm.prompts[0]  # rich explanation requested


async def test_llm_dry_run_used_for_other_languages(make_client) -> None:
    run = {"input_example": "[2,1]", "steps": [
        {"step": 1, "line": 2, "description": "compare", "variables": {"i": 0},
         "data_structure_state": {"type": "array", "state": {"values": [2, 1]},
                                  "highlights": [{"index_or_node": 0, "color": "green", "label": "i"}]}},
        {"step": 2, "line": 3, "description": "bad ds", "data_structure_state": {"type": "spaceship"}},
    ]}
    llm = FakeLLM(json.dumps({"summary": "js", "dry_run": run}))
    code = "function f(a) {\n  for (let i = 0; i < a.length; i++) {\n    console.log(a[i]);\n  }\n}"
    async with make_client(llm) as client:
        body = (await client.post("/api/analyze", json={"code": code})).json()
    assert body["language"] == "javascript" and body["dry_run"]["source"] == "llm"
    steps = body["dry_run"]["steps"]
    assert len(steps) == 2 and steps[0]["variables"] == {"i": "0"}
    assert steps[0]["data_structure_state"]["highlights"][0]["target"] == 0
    assert steps[1]["data_structure_state"]["state"] == {"values": [2, 1]}  # unusable snapshot → carried forward


async def test_invalid_llm_json_falls_back(make_client) -> None:
    async with make_client(FakeLLM("I cannot do that")) as client:
        body = (await client.post("/api/analyze", json={"code": BUBBLE})).json()
    assert body["llm_used"] is False and any("not valid JSON" in w for w in body["warnings"])


async def test_stream_event_order(make_client) -> None:
    async with make_client(FakeLLM(LLM_JSON)) as client:
        res = await client.post("/api/analyze/stream", json={"code": BUBBLE})
    events = [line.split(": ", 1)[1] for line in res.text.splitlines() if line.startswith("event:")]
    assert events[0] == "stage" and events[1] == "partial"
    assert "token" in events and events[-2:] == ["result", "done"]


async def test_focused_endpoints(make_client) -> None:
    async with make_client() as client:
        flow = (await client.post("/api/visualize", json={"code": BUBBLE})).json()
        run = (await client.post("/api/dryrun", json={"code": BUBBLE, "entry_call": "bubble_sort([2, 1])"})).json()
        cx = (await client.post("/api/complexity", json={"code": BUBBLE})).json()
        ex = (await client.post("/api/explain", json={"code": BUBBLE, "eli5": True})).json()
    assert flow["nodes"] and run["input_example"] == "bubble_sort([2, 1])"
    assert cx["time"]["worst"] == "O(n²)" and ex["eli5"] is True and ex["summary"]


async def test_validation_and_limits(make_client, settings: Settings) -> None:
    async with make_client() as client:
        assert (await client.post("/api/analyze", json={"code": "   "})).status_code == 422
        assert (await client.post("/api/analyze", json={"code": "x", "language": "cobol"})).status_code == 422
    cfg = settings.model_copy(update={"max_code_chars": 10})
    async with make_client(cfg=cfg) as client:
        assert (await client.post("/api/analyze", json={"code": "x = 1\n" * 10})).status_code == 413


async def test_rate_limit(make_client, settings: Settings) -> None:
    cfg = settings.model_copy(update={"rate_limit_per_minute": 2})
    async with make_client(cfg=cfg) as client:
        codes = [(await client.post("/api/complexity", json={"code": "x = 1"})).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


async def test_leetcode_endpoints_and_problem_dry_run(make_client) -> None:
    code = (
        "class Solution:\n    def maxDepth(self, root):\n        if not root:\n            return 0\n"
        "        return 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))\n"
    )
    async with make_client() as client:
        listing = (await client.get("/api/leetcode/problems")).json()
        problem = (await client.get("/api/leetcode/problems/104")).json()
        run = (await client.post("/api/leetcode/run", json={
            "code": code, "problem": "104",
            "tests": [*({"input": e["input"], "expected": e["expected"]} for e in problem["examples"]),
                      {"input": ["[1,2]"], "expected": "5"}],
        })).json()
        body = (await client.post("/api/analyze", json={
            "code": code, "problem": "maximum-depth-of-binary-tree", "test_input": ["[3,9,20,null,null,15,7]"],
        })).json()
        bad = await client.post("/api/analyze", json={"code": code, "problem": "104", "test_input": ["[1", "2"]})
    assert any(p["id"] == "104" for p in listing) and problem["starter_code"].startswith("# Definition")
    assert (run["passed"], run["total"]) == (2, 3) and run["results"][2]["status"] == "failed"
    assert body["algorithm_name"] == "104. Maximum Depth of Binary Tree"
    assert body["dry_run"]["input_example"] == "root = [3,9,20,null,null,15,7]"
    steps = body["dry_run"]["steps"]
    assert any(s["function"] == "maxDepth" for s in steps)
    assert "ListNode" not in steps[-1]["variables"] and "inf" not in steps[-1]["variables"]  # prelude hidden
    trees = [s["data_structure_state"] for s in steps if s["data_structure_state"]]
    assert trees and all(t["state"]["root"]["value"] == 3 for t in trees)  # whole tree, not subtrees
    assert "3" in steps[-1]["output_so_far"]
    assert bad.status_code == 422


async def test_design_problem_dry_run_focuses_on_object_state(make_client) -> None:
    code = (
        "class MinStack:\n    def __init__(self):\n        self.stack = []\n        self.mins = []\n"
        "    def push(self, val):\n        self.stack.append(val)\n"
        "        self.mins.append(min(val, self.mins[-1] if self.mins else val))\n"
        "    def pop(self):\n        self.stack.pop()\n        self.mins.pop()\n"
        "    def top(self):\n        return self.stack[-1]\n    def getMin(self):\n        return self.mins[-1]\n"
    )
    async with make_client() as client:
        body = (await client.post("/api/analyze", json={"code": code, "problem": "155"})).json()
    states = [s["data_structure_state"] for s in body["dry_run"]["steps"] if s["data_structure_state"]]
    assert states and {s["name"] for s in states} <= {"self.stack", "self.mins"}
    assert states[0]["type"] == "stack"
    assert body["complexity"]["time"]["worst"] == "O(1)"
    assert "__operations" not in body["dry_run"]["steps"][-1]["variables"]


async def test_leetcode_cpp_run_and_search(make_client) -> None:
    code = ("class Solution {\npublic:\n    int climbStairs(int n) {\n        int a = 1, b = 1;\n"
            "        while (n--) { int c = a + b; a = b; b = c; }\n        return a;\n    }\n};\n")
    async with make_client() as client:
        problem = (await client.get("/api/leetcode/problems/70")).json()
        run = (await client.post("/api/leetcode/run", json={
            "code": code, "problem": "70", "language": "cpp",
            "tests": [{"input": e["input"], "expected": e["expected"]} for e in problem["examples"]]})).json()
        hits = (await client.get("/api/leetcode/search", params={"q": "stair"})).json()
        body = (await client.post("/api/analyze", json={
            "code": code, "language": "cpp", "problem": "70", "test_input": ["5"]})).json()
    assert problem["starter_code_cpp"].startswith("class Solution {")
    assert (run["passed"], run["total"]) == (2, 2)
    assert hits[0]["slug"] == "climbing-stairs"
    assert body["language"] == "cpp" and body["algorithm_name"] == "70. Climbing Stairs"
    assert body["dry_run"]["input_example"] == "n = 5" and body["flowchart"]["nodes"]


SLOPPY_TRACE = (  # what a 7B model really produces: aliases, strings for numbers, bare lists, truncation
    '{"input_example": "n = 3", "steps": ['
    '{"step": "1", "line": "3", "action": "dp starts as [1, 1, 0, 0]", "variables": {"n": 3, "dp": [1, 1, 0, 0]},'
    ' "data_structure_state": {"type": "vector", "state": [1, 1, 0, 0],'
    ' "highlights": [{"index": 2, "color": "orange"}]}},'
    '{"line": 4, "description": "dp[2] = dp[1] + dp[0] = 2", "variables": {"i": 2},'
    ' "data_structure_state": {"type": "DP Table", "state": [[1, 1, 2, 0]]}},'
    '{"line": 5, "description": "loop continues"},'
    '{"line": 6, "description": "return dp[3] = 3", "variables": {"result": 3}, "data_stru'
)
JS_STAIRS = ("var climbStairs = function(n) {\n    const dp = new Array(n + 1).fill(1);\n"
             "    for (let i = 2; i <= n; i++) dp[i] = dp[i - 1] + dp[i - 2];\n    return dp[n];\n};\n")
CPP = ("class Solution {\npublic:\n    int climbStairs(int n) {\n        vector<int> dp(n + 1, 1);\n"
       "        for (int i = 2; i <= n; i++) dp[i] = dp[i - 1] + dp[i - 2];\n        return dp[n];\n    }\n};\n")


async def test_cpp_two_phase_ai_dry_run_tolerates_sloppy_output(make_client) -> None:
    insight = json.dumps({"summary": "Bottom-up DP.", "complexity": {
        "time": {"best": "O(n)", "average": "O(n)", "worst": "O(n)", "explanation": "one loop"},
        "space": {"complexity": "O(n)", "explanation": "dp array"}}})  # no concepts/edge cases at all
    llm = FakeLLM(insight, dry_run=SLOPPY_TRACE)
    async with make_client(llm) as client:
        res = await client.post("/api/analyze/stream", json={  # JS: no native tracer → AI trace
            "code": JS_STAIRS, "language": "javascript", "problem": "70", "test_input": ["3"]})
    events = [line.split(": ", 1)[1] for line in res.text.splitlines() if line.startswith("event:")]
    stages = [json.loads(line[6:])["stage"] for line in res.text.splitlines()
              if line.startswith("data:") and '"stage"' in line and '"message"' in line]
    assert stages == ["static", "llm", "dryrun"]
    assert events.count("partial") == 2 and events[-2:] == ["result", "done"]
    final = json.loads([line for line in res.text.splitlines() if line.startswith("data:")][-2][6:])
    run = final["dry_run"]
    assert run["source"] == "llm" and run["input_example"] == "n = 3" and len(run["steps"]) == 4
    first, second, third = run["steps"][:3]
    assert first["line"] == 3 and first["description"].startswith("dp starts")
    assert first["data_structure_state"]["type"] == "array"
    assert first["data_structure_state"]["highlights"] == [{"target": 2, "color": "yellow", "label": ""}]
    assert second["data_structure_state"]["type"] == "matrix"
    assert third["data_structure_state"]["state"] == second["data_structure_state"]["state"]  # carried forward
    assert "Dry-run this javascript code" in llm.prompts[1] and "n = 3" in llm.prompts[1]
    assert final["summary"] == "Bottom-up DP." and final["complexity"]["source"] == "llm"
    assert not any("needs AI model" in w for w in final["warnings"])
    assert final["algorithm_name"] == "70. Climbing Stairs"


async def test_llm_omitting_fields_keeps_offline_explanations(make_client) -> None:
    async with make_client(FakeLLM(json.dumps({"summary": "Swaps neighbours."}))) as client:
        body = (await client.post("/api/analyze", json={"code": BUBBLE})).json()
    assert body["summary"] == "Swaps neighbours."
    assert body["key_concepts"] and body["edge_cases"] and body["optimizations"]  # not wiped


async def test_unusable_ai_trace_explains_itself(make_client) -> None:
    llm = FakeLLM(json.dumps({"summary": "x"}), dry_run="sorry, I cannot")
    async with make_client(llm) as client:
        body = (await client.post("/api/analyze", json={"code": JS_STAIRS, "language": "javascript"})).json()
    assert body["dry_run"]["steps"] == []
    assert any("didn't return a usable dry run" in w for w in body["warnings"])


async def test_explain_never_empty_offline(make_client) -> None:
    async with make_client() as client:
        body = (await client.post("/api/analyze", json={"code": CPP, "language": "cpp", "problem": "70"})).json()
    assert "Dynamic Programming" in [c["concept"] for c in body["key_concepts"]]
    assert body["edge_cases"] and body["summary"]


async def test_failed_ai_dry_run_is_not_cached(make_client) -> None:
    llm = FakeLLM(json.dumps({"summary": "x"}), dry_run="garbage")
    async with make_client(llm) as client:
        await client.post("/api/analyze", json={"code": JS_STAIRS, "language": "javascript"})
        llm.dry_run = SLOPPY_TRACE
        body = (await client.post("/api/analyze", json={"code": JS_STAIRS, "language": "javascript"})).json()
    assert len(body["dry_run"]["steps"]) == 4  # retried, not served from cache



GOOD_NODES = (  # "count good nodes" logic under #104's signature
    "class Solution {\n    int cnt = 0;\nprivate:\n    void F(TreeNode* curr, int prev) {\n"
    "        if (!curr)\n            return;\n        if (curr->val >= prev)\n            cnt++;\n"
    "        F(curr->left, max(curr->val, prev));\n        F(curr->right, max(curr->val, prev));\n    }\n"
    "public:\n    int maxDepth(TreeNode* root) {\n        F(root, root->val);\n        return cnt;\n    }\n};\n"
)


@pytest.mark.skipif(find_compiler() is None, reason="no C++ compiler")
async def test_cpp_native_trace_is_real_and_needs_no_ai(make_client) -> None:
    llm = FakeLLM(json.dumps({"summary": "Counts good nodes."}))
    async with make_client(llm) as client:
        body = (await client.post("/api/analyze", json={
            "code": GOOD_NODES, "language": "cpp", "problem": "104", "test_input": ["[3,1,4,3,null,1,5]"]})).json()
    run = body["dry_run"]
    assert run["source"] == "trace" and run["error"] is None
    assert len(llm.prompts) == 1  # only the insight call — no AI trace
    assert not any("AI model" in w for w in body["warnings"])
    trees = [s["data_structure_state"] for s in run["steps"] if s["data_structure_state"]]
    assert all(t["state"]["root"]["value"] == 3 for t in trees)  # whole tree even inside F()
    curr_targets = {h["target"] for t in trees for h in t["highlights"] if h["label"] == "curr"}
    assert len(curr_targets) >= 5  # the highlight walks the tree
    assert any(s["function"] == "F" and s["depth"] >= 2 for s in run["steps"])
    assert run["steps"][-1]["variables"]["cnt"] == "4"


@pytest.mark.skipif(find_compiler() is None, reason="no C++ compiler")
async def test_cpp_free_program_native_trace(make_client) -> None:
    prog = ("#include <iostream>\n#include <vector>\nusing namespace std;\nint main() {\n"
            "    vector<int> a = {3, 1, 2};\n    sort(a.begin(), a.end());\n"
            "    for (int x : a) cout << x << ' ';\n    return 0;\n}\n")
    async with make_client() as client:
        body = (await client.post("/api/analyze", json={"code": prog, "language": "cpp"})).json()
    run = body["dry_run"]
    assert run["source"] == "trace" and run["steps"][-1]["output_so_far"].startswith("1 2 3")
    first = next(s["data_structure_state"] for s in run["steps"] if s["data_structure_state"])
    assert first["type"] == "array"


async def test_chat_streams_plain_text_with_context(make_client) -> None:
    llm = FakeLLM("Because `dp[i]` depends on the two previous stairs.")
    async with make_client(llm) as client:
        res = await client.post("/api/chat/stream", json={
            "messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello!"},
                         {"role": "user", "content": "Why dp[i - 2]?"}],
            "code": CPP, "language": "cpp", "problem": "70", "context": "Current step: line 5, i = 3"})
    tokens = [json.loads(line[6:])["text"] for line in res.text.splitlines()
              if line.startswith("data:") and '"text"' in line]
    assert "".join(tokens) == "Because `dp[i]` depends on the two previous stairs."
    prompt = llm.prompts[0]
    assert llm.json_modes == [False]  # chat is prose, not JSON
    assert "70. Climbing Stairs" in prompt and "  5 |" in prompt and "line 5, i = 3" in prompt
    assert "Student: hi" in prompt and "Why dp[i - 2]?" in prompt


async def test_chat_without_model_explains(make_client) -> None:
    async with make_client() as client:
        res = await client.post("/api/chat/stream", json={"messages": [{"role": "user", "content": "help"}]})
    assert "event: error" in res.text and "isn't running" in res.text



async def test_rich_explanation_fields_are_merged(make_client) -> None:
    llm = FakeLLM(json.dumps({
        "summary": "Sorts by repeatedly swapping neighbours. Larger values bubble to the end.",
        "intuition": "Each pass pushes the largest remaining value to its final place.",
        "approach": ["Line 2: outer loop over passes", "Line 4: compare neighbours", "Line 5: swap if out of order"],
        "why_it_works": "After pass i the last i elements are sorted.",
        "common_mistakes": ["Off-by-one in the inner bound"],
    }))
    async with make_client(llm) as client:
        body = (await client.post("/api/analyze", json={"code": BUBBLE})).json()
        eli5 = (await client.post("/api/explain", json={"code": BUBBLE, "eli5": True})).json()
    assert body["intuition"].startswith("Each pass") and len(body["approach"]) == 3
    assert body["why_it_works"] and body["common_mistakes"] == ["Off-by-one in the inner bound"]
    assert body["edge_cases"]  # missing from the AI reply → offline values kept
    assert eli5["approach"][0].startswith("Line 2") and eli5["eli5"] is True
