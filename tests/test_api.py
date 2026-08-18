from backend.app.database import SessionLocal
from backend.app.models import Article
from backend.app.services.classifier import classify_article
from backend.app.services.news_fetcher import fetch_and_store_articles


def login(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "test-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_article_list_and_detail(client):
    assert client.get("/api/articles/").json() == []

    result = fetch_and_store_articles()
    assert result["saved"] == 3
    assert result["mode"] == "demo"

    listing = client.get("/api/articles/?limit=100")
    assert listing.status_code == 200
    articles = listing.json()
    assert len(articles) == 3
    assert all(article["id"] for article in articles)

    detail = client.get(f"/api/articles/{articles[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["url"]


def test_demo_fetch_is_duplicate_safe():
    first = fetch_and_store_articles()
    second = fetch_and_store_articles()

    assert first["saved"] == 3
    assert second["saved"] == 0
    assert SessionLocal().query(Article).count() == 3


def test_classifier_uses_deterministic_fallback():
    assert classify_article("A new OpenAI model improves artificial intelligence") == "Artificial Intelligence"
    assert classify_article("The company reported stronger stock market earnings") == "Finance"
    assert classify_article("A topic with no known terms") == "General"


def test_auth_success_and_failure(client):
    successful = client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "test-password"},
    )
    assert successful.status_code == 200
    assert successful.json()["token_type"] == "bearer"

    failed = client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "wrong-password"},
    )
    assert failed.status_code == 401


def test_protected_routes_require_jwt(client):
    assert client.post("/api/articles/fetch").status_code == 401
    assert client.post("/api/articles/classify").status_code == 401


def test_authenticated_demo_fetch_and_classification(client):
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    fetch_response = client.post("/api/articles/fetch", headers=headers)
    assert fetch_response.status_code == 200
    assert fetch_response.json()["mode"] == "demo"

    db = SessionLocal()
    article = db.query(Article).first()
    article.category = None
    db.commit()
    db.close()

    classify_response = client.post("/api/articles/classify", headers=headers)
    assert classify_response.status_code == 200
    assert classify_response.json()["classified"] == 1
