"""HTTP-level tests with a scripted LLM injected through the app factory."""

import json

from core.config import Settings
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
    assert "dry_run" not in llm.prompts[0].split("Respond with JSON")[1]  # not requested for Python


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
    assert steps[1]["data_structure_state"] is None


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
