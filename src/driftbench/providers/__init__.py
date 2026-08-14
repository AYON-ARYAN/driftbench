"""Provider registry. Credentials come from the environment, never from the repo."""
from __future__ import annotations

from driftbench.providers.base import ModelProvider, ModelResponse, ProviderError
from driftbench.providers.ollama import OllamaProvider

__all__ = ["ModelProvider", "ModelResponse", "ProviderError", "get_provider"]


def get_provider(spec: str) -> ModelProvider:
    """Build a provider from a spec string like 'ollama:qwen2.5-coder:7b'."""
    prefix, _, model = spec.partition(":")
    if not model:
        raise ProviderError(f"malformed provider spec: {spec!r}")
    if prefix == "ollama":
        return OllamaProvider(model)
    raise ProviderError(f"unknown provider {prefix!r} in spec {spec!r}")
