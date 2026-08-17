"""Provider registry. Credentials come from the environment, never from the repo."""
from __future__ import annotations

from driftbench.providers.base import ModelProvider, ModelResponse, ProviderError
from driftbench.providers.ollama import OllamaProvider
from driftbench.providers.gemini import GeminiProvider

__all__ = ["ModelProvider", "ModelResponse", "ProviderError", "get_provider"]


def get_provider(spec: str) -> ModelProvider:
    """Build a provider from a spec string like 'ollama:qwen2.5-coder:7b' or 'gemini:gemini-1.5-flash'."""
    prefix, _, model = spec.partition(":")
    if not model:
        raise ProviderError(f"malformed provider spec: {spec!r}")
    if prefix == "ollama":
        return OllamaProvider(model)
    if prefix == "gemini":
        return GeminiProvider(model)
    raise ProviderError(f"unknown provider {prefix!r} in spec {spec!r}")
