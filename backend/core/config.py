"""Application settings loaded from environment variables / `.env`.

Every tunable lives here so modules never read `os.environ` directly; this keeps
configuration injectable in tests (construct `Settings(...)` with overrides).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration for CodeLens."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM -----------------------------------------------------------------
    llm_provider: Literal["auto", "ollama", "openai", "none"] = "auto"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096
    llm_timeout_s: float = 120.0

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # --- App -----------------------------------------------------------------
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    debug: bool = False

    # --- Limits --------------------------------------------------------------
    max_code_chars: int = 20_000
    rate_limit_per_minute: int = 30
    cache_size: int = 128

    # --- Sandbox -------------------------------------------------------------
    sandbox_timeout_s: float = 5.0
    sandbox_memory_mb: int = 256
    trace_max_steps: int = 400

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow `CORS_ORIGINS=a,b` as a comma-separated string."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings singleton (overridable via FastAPI dependency overrides)."""
    return Settings()
