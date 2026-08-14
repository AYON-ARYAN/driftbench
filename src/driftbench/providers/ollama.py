"""Local Ollama adapter. No credentials, no network beyond localhost."""
from __future__ import annotations

import httpx

from driftbench.providers.base import ModelResponse, ProviderError


class OllamaProvider:
    def __init__(
        self,
        model: str,
        host: str = "http://127.0.0.1:11434",
        timeout: float = 300.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.model_id = f"ollama:{model}"
        self._host = host.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def complete(self, system: str, user: str, seed: int) -> ModelResponse:
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"seed": seed, "temperature": 0.0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            resp = self._client.post(f"{self._host}/api/chat", json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"ollama request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"ollama returned {resp.status_code}: {resp.text[:200]}")

        body = resp.json()
        return ModelResponse(
            text=body.get("message", {}).get("content", ""),
            prompt_tokens=body.get("prompt_eval_count", 0),
            completion_tokens=body.get("eval_count", 0),
        )
