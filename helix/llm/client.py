from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: str


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> LLMResponse:
        ...
