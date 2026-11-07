"""Robust extraction of a JSON object from (possibly malformed) LLM output."""

import json
import re
from typing import Any

_FENCE_RX = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_TRAILING_COMMA_RX = re.compile(r",\s*([}\]])")


def extract_json(text: str) -> dict[str, Any] | None:
    """Best-effort parse of the first JSON object in `text`.

    Handles code fences, leading/trailing prose, trailing commas and output
    truncated mid-object (closes open brackets). Returns None if hopeless.
    """
    if not text:
        return None
    fenced = _FENCE_RX.search(text)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    if start < 0:
        return None
    candidate = text[start:]
    for attempt in (candidate, _close_brackets(candidate)):
        cleaned = _TRAILING_COMMA_RX.sub(r"\1", attempt)
        end = cleaned.rfind("}")
        for chunk in (cleaned, cleaned[: end + 1] if end >= 0 else cleaned):
            try:
                value = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    return None


def _scan(text: str) -> tuple[list[str], bool, int]:
    """Return (pending closers, ends inside string, index after last safe cut)."""
    stack: list[str] = []
    in_string = escaped = False
    last_safe = 0
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
            last_safe = i + 1
        elif ch in "}]" and stack:
            stack.pop()
            last_safe = i + 1
        elif ch == ",":
            last_safe = i
    return stack, in_string, last_safe


def _close_brackets(text: str) -> str:
    """Cut a truncated response at the last complete value and close brackets."""
    stack, in_string, last_safe = _scan(text)
    if not stack and not in_string:
        return text
    trimmed = text[:last_safe].rstrip().rstrip(",")
    pending, _, _ = _scan(trimmed)
    return trimmed + "".join(reversed(pending))
