import httpx
import pytest

from backend.llm import LLMClient, LLMConfig, LLMError


def make_client(handler, attempts=3):
    cfg = LLMConfig("openai", "test-key", "test-model", max_attempts=attempts)
    sleeps: list[float] = []
    client = LLMClient(cfg, transport=httpx.MockTransport(handler), sleep=sleeps.append)
    return client, sleeps


def ok_body(text="hello"):
    return {"choices": [{"message": {"content": text}}]}


def test_retries_on_429_then_succeeds_and_honours_retry_after():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "1.5"})
        return httpx.Response(200, json=ok_body("done"))

    client, sleeps = make_client(handler)
    res = client.complete("sys", "user")
    assert res.text == "done" and res.attempts == 2
    assert sleeps == [1.5]


def test_does_not_retry_on_401():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(401)

    client, _ = make_client(handler)
    with pytest.raises(LLMError) as err:
        client.complete("sys", "user")
    assert err.value.reason == "http_401" and calls["n"] == 1


def test_gives_up_after_max_attempts_on_timeouts():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client, sleeps = make_client(handler, attempts=3)
    with pytest.raises(LLMError) as err:
        client.complete("sys", "user")
    assert err.value.reason == "timeout" and err.value.attempts == 3
    assert len(sleeps) == 2 and all(s <= client.config.max_delay_s for s in sleeps)
