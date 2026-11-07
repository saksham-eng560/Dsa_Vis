"""LLM clients parse their wire formats correctly (mocked HTTP)."""

import json

import httpx
import pytest

from core.config import Settings
from core.llm_engine import (
    FallbackClient,
    LLMUnavailableError,
    NullClient,
    OllamaClient,
    OpenAICompatClient,
    complete,
)


def _http(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_ollama_streams_ndjson() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        body = json.loads(req.content)
        assert body["format"] == "json" and body["stream"] is True
        lines = [json.dumps({"message": {"content": c}}) for c in ('{"a"', ": 1}")] + [json.dumps({"done": True})]
        return httpx.Response(200, text="\n".join(lines))

    async with _http(handler) as http:
        client = OllamaClient(http, Settings())
        assert await client.available()
        assert await complete(client, "s", "p") == '{"a": 1}'


async def test_openai_streams_sse() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"] == "Bearer k"
        chunks = [f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}" for c in ("he", "llo")]
        return httpx.Response(200, text="\n\n".join([*chunks, "data: [DONE]"]))

    async with _http(handler) as http:
        client = OpenAICompatClient(http, Settings(openai_api_key="k"))
        assert await complete(client, "s", "p") == "hello"


async def test_fallback_skips_unavailable_backends() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/api/tags":
            raise httpx.ConnectError("down")
        return httpx.Response(200, text='data: {"choices": [{"delta": {"content": "ok"}}]}')

    async with _http(handler) as http:
        cfg = Settings(openai_api_key="k")
        client = FallbackClient(OllamaClient(http, cfg), OpenAICompatClient(http, cfg))
        assert await complete(client, "s", "p") == "ok"
        assert client.model == cfg.openai_model


async def test_null_client_raises() -> None:
    assert not await NullClient().available()
    with pytest.raises(LLMUnavailableError):
        await complete(NullClient(), "s", "p")
