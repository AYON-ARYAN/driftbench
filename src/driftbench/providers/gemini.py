"""Google Gemini model provider using direct HTTP request endpoints."""
from __future__ import annotations

import os
from pathlib import Path
import httpx

from driftbench.providers.base import ModelResponse, ProviderError


class GeminiProvider:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        timeout: float = 300.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.model_id = f"gemini:{model}"
        
        # Load API Key securely
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            key_file = Path("/Users/ayonaryan/Downloads/LINKEDIN/.gemini_api_key")
            if key_file.exists():
                api_key = key_file.read_text().strip()
                
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=timeout)

    def complete(self, system: str, user: str, seed: int) -> ModelResponse:
        if not self._api_key:
            raise ProviderError("Gemini API key not found. Ensure GEMINI_API_KEY env var or .gemini_api_key file is set.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self._api_key}"
        
        payload = {
            "systemInstruction": {
                "parts": [{"text": system}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user}]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "seed": seed
            }
        }
        
        try:
            resp = self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini API request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"Gemini API returned {resp.status_code}: {resp.text[:200]}")

        body = resp.json()
        
        # Parse Response
        try:
            candidates = body.get("candidates", [])
            if not candidates:
                raise ProviderError("Gemini API returned no candidates.")
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            usage = body.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Failed to parse Gemini API response: {exc}. Body: {body}") from exc

        return ModelResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
