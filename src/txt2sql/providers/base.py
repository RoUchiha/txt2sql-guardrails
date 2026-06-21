"""Provider abstraction. The seam that makes generation testable offline."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Anything that can turn a prompt into text. Real providers wrap an SDK;
    the MockProvider returns deterministic, scripted output for tests/demo."""

    async def generate(self, prompt: str) -> str: ...
