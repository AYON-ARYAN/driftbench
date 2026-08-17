import httpx
import pytest
from driftbench.providers.base import ModelResponse
from driftbench.providers.gemini import GeminiProvider
from driftbench.providers import get_provider, ProviderError


def _transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_gemini_returns_text_and_token_counts():
    def handler(request):
        assert request.url.path == "/v1beta/models/gemini-1.5-flash:generateContent"
        assert "key=mock-key" in request.url.query.decode()
        body = httpx.Response(200, json={
            "candidates": [
                {"content": {"parts": [{"text": "### FILE: a.py\n```\nX=1\n```"}]}}
            ],
            "usageMetadata": {
                "promptTokenCount": 15,
                "candidatesTokenCount": 23,
            }
        })
        return body

    provider = GeminiProvider("gemini-1.5-flash", api_key="mock-key", client=_transport(handler))
    resp = provider.complete("sys", "user", seed=0)
    assert isinstance(resp, ModelResponse)
    assert "### FILE: a.py" in resp.text
    assert (resp.prompt_tokens, resp.completion_tokens) == (15, 23)


def test_gemini_sends_system_instruction_and_seed():
    seen = {}

    def handler(request):
        import json
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "x"}]}}]
        })

    GeminiProvider("gemini-1.5-flash", api_key="mock-key", client=_transport(handler)).complete("s", "u", seed=7)
    assert seen["systemInstruction"]["parts"][0]["text"] == "s"
    assert seen["contents"][0]["parts"][0]["text"] == "u"
    assert seen["generationConfig"]["temperature"] == 0.0


def test_gemini_http_error_becomes_provider_error():
    handler = lambda request: httpx.Response(500, text="boom")
    with pytest.raises(ProviderError, match="500"):
        GeminiProvider("gemini-1.5-flash", api_key="mock-key", client=_transport(handler)).complete("s", "u", seed=0)


def test_model_id_is_the_full_spec():
    assert GeminiProvider("gemini-1.5-flash", api_key="mock-key").model_id == "gemini:gemini-1.5-flash"
