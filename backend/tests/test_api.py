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
