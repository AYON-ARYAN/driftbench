"""Provider-agnostic model interface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ProviderError(Exception):
    """The provider could not produce a completion."""


class ModelProvider(Protocol):
    model_id: str

    def complete(self, system: str, user: str, seed: int) -> ModelResponse:
        ...
