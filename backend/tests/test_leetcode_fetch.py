"""Live LeetCode fetching (GraphQL mocked) and HTML/example parsing."""

import json
from pathlib import Path

import httpx
import pytest

from core.lc_problem import LeetCodeClient, ProblemNotFoundError, html_to_text, parse_example_outputs

CLASSIC_HTML = (
    "<p>Given an array <code>nums</code> of size 10<sup>4</sup>&nbsp;&lt;tricky&gt;.</p>"
    '<p><strong class="example">Example 1:</strong></p><pre><strong>Input:</strong> nums = [1,2], k = 1\n'
    "<strong>Output:</strong> [2]\n<strong>Explanation:</strong> because.</pre>"
    '<p><strong class="example">Example 2:</strong></p><pre><strong>Input:</strong> nums = [3], k = 1\n'
    "<strong>Output:</strong> [3]</pre><p><strong>Constraints:</strong></p><ul><li><code>1 &lt;= k</code></li></ul>"
)
BLOCK_HTML = (
    "<p>Count things.</p><p><strong>Example 1:</strong></p><div class=\"example-block\">"
    "<p><strong>Input:</strong> <span class=\"example-io\">s = \"ab\"</span></p>"
    "<p><strong>Output:</strong> <span class=\"example-io\">true</span></p></div>"
)
QUESTION = {
    "questionFrontendId": "9999", "title": "Top K Thing", "titleSlug": "top-k-thing", "difficulty": "Medium",
    "isPaidOnly": False, "content": CLASSIC_HTML, "exampleTestcaseList": ["[1,2]\n1", "[3]\n1"],
    "metaData": json.dumps({"name": "topK", "params": [{"name": "nums", "type": "integer[]"},
                                                       {"name": "k", "type": "integer"}],
                            "return": {"type": "integer[]"}}),
    "topicTags": [{"name": "Heap"}], "codeSnippets": [{"langSlug": "python3", "code": "class Solution:\n    pass"}],
}


def test_html_to_text_and_outputs() -> None:
    text = html_to_text(CLASSIC_HTML)
    assert "10^4 <tricky>" in text and "• 1 <= k" in text and "<" not in text.replace("<tricky>", "").replace("<=", "")
    assert parse_example_outputs(text) == ["[2]", "[3]"]
    assert parse_example_outputs(html_to_text(BLOCK_HTML)) == ["true"]


def _client(tmp_path: Path, handler) -> tuple[LeetCodeClient, list[str]]:
    calls: list[str] = []

    def wrapped(req: httpx.Request) -> httpx.Response:
        calls.append(json.loads(req.content)["query"].split("{")[1].split("(")[0].strip())
        return handler(json.loads(req.content))

    http = httpx.AsyncClient(transport=httpx.MockTransport(wrapped))
    return LeetCodeClient(http, tmp_path), calls


async def test_fetch_by_id_then_cache(tmp_path: Path) -> None:
    def handler(body: dict) -> httpx.Response:
        if "questionList" in body["query"]:
            return httpx.Response(200, json={"data": {"problemsetQuestionList": {"questions": [
                {"questionFrontendId": "99999", "titleSlug": "other"},
                {"questionFrontendId": "9999", "titleSlug": "top-k-thing"}]}}})
        return httpx.Response(200, json={"data": {"question": QUESTION}})

    client, calls = _client(tmp_path, handler)
    p = await client.get("9999")
    assert (p.title, p.function_name, p.source, p.tags) == ("Top K Thing", "topK", "leetcode", ["Heap"])
    assert [e.expected for e in p.examples] == ["[2]", "[3]"] and p.examples[0].input == ["[1,2]", "1"]
    assert "Example 1" not in p.description and "Constraints" in p.description
    assert p.starter_code.startswith("class Solution")
    assert len(calls) == 2
    assert (await client.get("9999")).slug == "top-k-thing" and len(calls) == 2  # served from disk cache


async def test_premium_and_network_errors(tmp_path: Path) -> None:
    paid = {**QUESTION, "isPaidOnly": True, "content": None}
    client, _ = _client(tmp_path, lambda b: httpx.Response(200, json={"data": {"question": paid}}))
    with pytest.raises(ProblemNotFoundError, match="premium"):
        await client.get("top-k-thing")

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    offline = LeetCodeClient(httpx.AsyncClient(transport=httpx.MockTransport(down)), tmp_path / "x")
    with pytest.raises(ProblemNotFoundError, match="Couldn't reach"):
        await offline.get("some-new-problem")
    assert (await offline.get("1")).title == "Two Sum"  # bundled problems work offline


async def test_live_search(tmp_path: Path) -> None:
    hits = [{"questionFrontendId": "887", "title": "Super Egg Drop", "titleSlug": "super-egg-drop",
             "difficulty": "Hard", "paidOnly": False},
            {"questionFrontendId": "1", "title": "Locked", "titleSlug": "locked", "difficulty": "Easy",
             "paidOnly": True}]
    payload = {"data": {"problemsetQuestionList": {"questions": hits}}}
    client, _ = _client(tmp_path, lambda b: httpx.Response(200, json=payload))
    assert [s.slug for s in await client.search("egg")] == ["super-egg-drop"]


def test_catalog_search() -> None:
    from core.lc_problem import search_catalog

    assert search_catalog("2")[0].id == "20"  # number prefix
    assert [s.slug for s in search_catalog("tree")][:1] == ["binary-tree-inorder-traversal"]
    assert search_catalog("zzz") == []


async def test_stale_cache_without_cpp_starter_is_refreshed(tmp_path: Path) -> None:
    from core.lc_problem import from_graphql

    stale = from_graphql(QUESTION).model_copy(update={"starter_code_cpp": ""})
    (tmp_path / "top-k-thing.json").write_text(stale.model_dump_json())
    snippets = [{"langSlug": "python3", "code": "class Solution: pass"},
                {"langSlug": "cpp", "code": "class Solution {\npublic:\n};"}]
    fresh = {**QUESTION, "codeSnippets": snippets}
    client, calls = _client(tmp_path, lambda b: httpx.Response(200, json={"data": {"question": fresh}}))
    p = await client.get("top-k-thing")
    assert p.starter_code_cpp.startswith("class Solution {") and len(calls) == 1
    assert (await client.get("top-k-thing")).starter_code_cpp and len(calls) == 1  # re-cached

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    (tmp_path / "top-k-thing.json").write_text(stale.model_dump_json())
    offline = LeetCodeClient(httpx.AsyncClient(transport=httpx.MockTransport(down)), tmp_path)
    assert "vector<int> topK(vector<int>& nums, int k)" in (await offline.get("top-k-thing")).starter_code_cpp
