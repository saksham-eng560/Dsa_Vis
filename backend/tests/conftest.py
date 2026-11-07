"""Shared fixtures: settings, a scripted fake LLM, and an ASGI test client."""

from collections.abc import AsyncIterator

import httpx
import pytest

from core.config import Settings
from main import create_app


class FakeLLM:
    """Scripted LLM: streams `response` in small chunks."""

    name = "fake"
    model = "fake-model"

    def __init__(self, response: str = "", available: bool = True) -> None:
        self.response = response
        self._available = available
        self.prompts: list[str] = []

    async def available(self) -> bool:
        return self._available

    async def stream(self, system: str, prompt: str) -> AsyncIterator[str]:
        self.prompts.append(prompt)
        for i in range(0, len(self.response), 7):
            yield self.response[i : i + 7]


@pytest.fixture
def settings() -> Settings:
    return Settings(llm_provider="none", rate_limit_per_minute=1000, sandbox_timeout_s=3)


@pytest.fixture
def make_client(settings: Settings):
    """Factory: `async with make_client(llm) as client:`."""

    def factory(llm: FakeLLM | None = None, cfg: Settings | None = None):
        app = create_app(cfg or settings, llm or FakeLLM(available=False))
        return _Client(app)

    return factory


class _Client:
    def __init__(self, app) -> None:
        self.app = app

    async def __aenter__(self) -> httpx.AsyncClient:
        self._lifespan = self.app.router.lifespan_context(self.app)
        await self._lifespan.__aenter__()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        return self.client

    async def __aexit__(self, *exc) -> None:
        await self.client.aclose()
        await self._lifespan.__aexit__(*exc)
