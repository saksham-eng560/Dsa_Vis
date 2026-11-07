"""LLM backends behind one small async interface.

`LLMClient.stream()` yields text chunks; everything else (prompting, JSON
repair, merging) lives elsewhere, so swapping Ollama for any OpenAI-compatible
server is a configuration change.
"""

import json
import time
from collections.abc import AsyncIterator
from typing import Protocol

import httpx

from core.config import Settings


class LLMUnavailableError(RuntimeError):
    """Raised when no backend can serve a request."""


class LLMClient(Protocol):
    name: str
    model: str | None

    async def available(self) -> bool: ...

    def stream(self, system: str, prompt: str) -> AsyncIterator[str]: ...


async def complete(client: LLMClient, system: str, prompt: str) -> str:
    """Collect a full response from a streaming client."""
    return "".join([chunk async for chunk in client.stream(system, prompt)])


class OllamaClient:
    """Ollama `/api/chat` with JSON mode and token streaming."""

    name = "ollama"

    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http, self.s = http, settings
        self.model: str | None = settings.ollama_model
        self._ok_until = 0.0

    async def available(self) -> bool:
        if time.monotonic() < self._ok_until:
            return True
        try:
            res = await self.http.get(f"{self.s.ollama_base_url}/api/tags", timeout=2.0)
            ok = res.status_code == 200
        except httpx.HTTPError:
            ok = False
        self._ok_until = time.monotonic() + 30 if ok else 0.0
        return ok

    async def stream(self, system: str, prompt: str) -> AsyncIterator[str]:
        body = {
            "model": self.model,
            "stream": True,
            "format": "json",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "keep_alive": "30m",
            "options": {
                "temperature": self.s.llm_temperature,
                "num_predict": self.s.llm_max_tokens,
                "num_ctx": self.s.llm_num_ctx,
            },
        }
        url = f"{self.s.ollama_base_url}/api/chat"
        async with self.http.stream("POST", url, json=body, timeout=self.s.llm_timeout_s) as res:
            if res.status_code != 200:
                raise LLMUnavailableError(f"Ollama returned HTTP {res.status_code}")
            async for line in res.aiter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("error"):
                    raise LLMUnavailableError(str(data["error"]))
                if chunk := data.get("message", {}).get("content"):
                    yield chunk


class OpenAICompatClient:
    """Any OpenAI-compatible `/chat/completions` endpoint (SSE streaming)."""

    name = "openai"

    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http, self.s = http, settings
        self.model: str | None = settings.openai_model

    async def available(self) -> bool:
        return bool(self.s.openai_api_key)

    async def stream(self, system: str, prompt: str) -> AsyncIterator[str]:
        body = {
            "model": self.model,
            "stream": True,
            "temperature": self.s.llm_temperature,
            "max_tokens": self.s.llm_max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        headers = {"Authorization": f"Bearer {self.s.openai_api_key}"}
        url = f"{self.s.openai_base_url.rstrip('/')}/chat/completions"
        async with self.http.stream(
            "POST", url, json=body, headers=headers, timeout=self.s.llm_timeout_s
        ) as res:
            if res.status_code != 200:
                raise LLMUnavailableError(f"LLM endpoint returned HTTP {res.status_code}")
            async for line in res.aiter_lines():
                if not line.startswith("data:") or line.strip() == "data: [DONE]":
                    continue
                delta = json.loads(line[5:]).get("choices", [{}])[0].get("delta", {})
                if chunk := delta.get("content"):
                    yield chunk


class NullClient:
    """No LLM configured — the static pipeline still works."""

    name = "none"
    model: str | None = None

    async def available(self) -> bool:
        return False

    async def stream(self, system: str, prompt: str) -> AsyncIterator[str]:
        raise LLMUnavailableError("No LLM backend configured")
        yield ""  # pragma: no cover - makes this an async generator


class FallbackClient:
    """`auto` mode: first available backend wins (Ollama → OpenAI-compatible)."""

    name = "auto"

    def __init__(self, *clients: LLMClient) -> None:
        self.clients = clients
        self.model: str | None = clients[0].model if clients else None

    async def _pick(self) -> LLMClient | None:
        for client in self.clients:
            if await client.available():
                self.model = client.model
                return client
        return None

    async def available(self) -> bool:
        return await self._pick() is not None

    async def stream(self, system: str, prompt: str) -> AsyncIterator[str]:
        client = await self._pick()
        if client is None:
            raise LLMUnavailableError("No LLM backend is reachable")
        async for chunk in client.stream(system, prompt):
            yield chunk


def build_llm(settings: Settings, http: httpx.AsyncClient) -> LLMClient:
    """Factory used by the app lifespan."""
    if settings.llm_provider == "ollama":
        return OllamaClient(http, settings)
    if settings.llm_provider == "openai":
        return OpenAICompatClient(http, settings)
    if settings.llm_provider == "none":
        return NullClient()
    return FallbackClient(OllamaClient(http, settings), OpenAICompatClient(http, settings))
