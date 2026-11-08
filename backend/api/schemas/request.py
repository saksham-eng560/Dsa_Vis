"""Pydantic request models with input validation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Language = Literal["auto", "python", "javascript", "typescript", "cpp", "java", "go", "rust"]

# Hard ceiling; the configurable `max_code_chars` is enforced in the service.
_ABSOLUTE_MAX = 100_000


class CodeRequest(BaseModel):
    """Base body shared by every analysis endpoint."""

    code: str = Field(min_length=1, max_length=_ABSOLUTE_MAX)
    language: Language = "auto"
    entry_call: str | None = Field(
        default=None,
        max_length=500,
        description="Optional Python expression used to drive the dry run, e.g. `sort([3,1,2])`.",
    )

    @field_validator("code")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Reject whitespace-only input and normalise line endings."""
        if not value.strip():
            raise ValueError("code must not be blank")
        return value.replace("\r\n", "\n").replace("\t", "    ")


class AnalyzeRequest(CodeRequest):
    """Body for `/api/analyze` — `use_llm=False` forces the static pipeline only.

    With `problem` (LeetCode id/slug/URL) the dry run executes `Solution` on
    `test_input` (LeetCode format, one value per line; default: example 1).
    """

    use_llm: bool = True
    problem: str | None = Field(default=None, max_length=200)
    test_input: list[str] | None = Field(default=None, max_length=20)


class ExplainRequest(CodeRequest):
    """Body for `/api/explain`."""

    eli5: bool = False
