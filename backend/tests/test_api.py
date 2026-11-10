import pytest
from fastapi.testclient import TestClient

from backend import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app_module.get_explainer.cache_clear()
    yield TestClient(app_module.app)
    app_module.get_explainer.cache_clear()


def test_list_doctors(client):
    res = client.get("/api/doctors")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 20 and body["doctors"][0]["rank"] == 1
    assert "Server-Timing" in res.headers


def test_explain_without_llm_uses_rules(client):
    res = client.get("/api/doctors/hcp-001/explain")
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "rules" and body["fallbackReason"] == "llm_not_configured"
    assert body["text"]


def test_unknown_doctor_returns_404(client):
    assert client.get("/api/doctors/nope/explain").status_code == 404
    assert client.get("/api/doctors/nope").status_code == 404


def test_health_reports_flags(client):
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "scoringVersion": "rules-v1", "flags": {"aiExplain": True}, "llmConfigured": False}
