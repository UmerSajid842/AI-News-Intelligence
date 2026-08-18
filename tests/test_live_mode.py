from datetime import datetime

import pytest

from backend.app import worker
from backend.app.database import SessionLocal
from backend.app.models import Article


def test_live_mode_requires_api_key(monkeypatch):
    monkeypatch.setenv("NEWS_MODE", "live")
    monkeypatch.delenv("NEWS_API_KEY", raising=False)

    with pytest.raises(worker.LiveNewsConfigurationError, match="NEWS_API_KEY"):
        worker.validate_live_configuration()


def test_invalid_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("NEWS_MODE", "staging")

    with pytest.raises(worker.LiveNewsConfigurationError, match="NEWS_MODE"):
        worker.get_news_mode()


def test_provider_timestamp_is_normalized_to_utc():
    parsed = worker.parse_provider_timestamp("2026-08-18T12:30:00+02:00")

    assert parsed == datetime(2026, 8, 18, 10, 30, 0)


def test_authenticated_live_fetch_without_key_returns_service_unavailable(client, monkeypatch):
    monkeypatch.setenv("NEWS_MODE", "live")
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    login_response = client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "test-password"},
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/articles/fetch",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "NEWS_API_KEY" in response.json()["detail"]


def test_live_provider_ingestion_is_duplicate_safe(monkeypatch):
    monkeypatch.setenv("NEWS_MODE", "live")
    monkeypatch.setenv("NEWS_API_KEY", "test-provider-key")
    monkeypatch.setenv("NEWS_PROVIDER_URL", "https://provider.example.test/headlines")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "articles": [
                    {
                        "title": "Live provider headline",
                        "description": "A provider response used only for tests.",
                        "content": "Test content",
                        "source": {"name": "Test Provider"},
                        "url": "https://provider.example.test/article-1",
                        "publishedAt": "2026-08-18T12:30:00Z",
                    }
                ]
            }

    requested = {}
    queued = []

    def fake_get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(worker.requests, "get", fake_get)
    monkeypatch.setattr(worker.process_article, "delay", lambda article_id: queued.append(article_id))

    first = worker.fetch_and_process_news()
    second = worker.fetch_and_process_news()

    assert requested["url"] == "https://provider.example.test/headlines"
    assert requested["params"]["apiKey"] == "test-provider-key"
    assert requested["timeout"] == 15
    assert first["saved"] == 1
    assert first["queued"] == 1
    assert second["saved"] == 0
    assert second["queued"] == 0
    assert len(queued) == 1

    db = SessionLocal()
    article = db.query(Article).one()
    assert article.source == "Test Provider"
    assert article.published_at == datetime(2026, 8, 18, 12, 30, 0)
    db.close()
