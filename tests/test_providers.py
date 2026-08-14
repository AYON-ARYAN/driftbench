import httpx
import pytest
from driftbench.providers import get_provider, ProviderError
from driftbench.providers.base import ModelResponse
from driftbench.providers.ollama import OllamaProvider


def _transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ollama_returns_text_and_token_counts():
    def handler(request):
        assert request.url.path == "/api/chat"
        body = httpx.Response(200, json={
            "message": {"content": "### FILE: a.py\n```\nX=1\n```"},
            "prompt_eval_count": 11,
            "eval_count": 7,
        })
        return body

    provider = OllamaProvider("qwen2.5-coder:7b", client=_transport(handler))
    resp = provider.complete("sys", "user", seed=0)
    assert isinstance(resp, ModelResponse)
    assert "### FILE: a.py" in resp.text
    assert (resp.prompt_tokens, resp.completion_tokens) == (11, 7)


def test_ollama_sends_seed_and_model():
    seen = {}

    def handler(request):
        import json
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "x"}})

    OllamaProvider("qwen2.5-coder:7b", client=_transport(handler)).complete("s", "u", seed=3)
    assert seen["model"] == "qwen2.5-coder:7b"
    assert seen["options"]["seed"] == 3
    assert seen["stream"] is False
    assert [m["role"] for m in seen["messages"]] == ["system", "user"]


def test_ollama_missing_token_counts_default_to_zero():
    handler = lambda request: httpx.Response(200, json={"message": {"content": "x"}})
    resp = OllamaProvider("m", client=_transport(handler)).complete("s", "u", seed=0)
    assert (resp.prompt_tokens, resp.completion_tokens) == (0, 0)


def test_ollama_http_error_becomes_provider_error():
    handler = lambda request: httpx.Response(500, text="boom")
    with pytest.raises(ProviderError, match="500"):
        OllamaProvider("m", client=_transport(handler)).complete("s", "u", seed=0)


def test_model_id_is_the_full_spec():
    assert OllamaProvider("qwen2.5-coder:7b").model_id == "ollama:qwen2.5-coder:7b"


def test_get_provider_builds_ollama():
    assert get_provider("ollama:qwen2.5-coder:7b").model_id == "ollama:qwen2.5-coder:7b"


def test_get_provider_rejects_unknown_prefix():
    with pytest.raises(ProviderError, match="unknown provider"):
        get_provider("mystery:model")
