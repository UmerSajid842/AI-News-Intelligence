import os
from datetime import datetime

import requests
from celery import Celery

from .database import SessionLocal
from .models import Article
from .services.classifier import classify_article

celery_app = Celery(
    "worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.autodiscover_tasks(["app"])


@celery_app.task(name="app.worker.process_article")
def process_article(article_id: int):
    """Run the article intelligence pipeline in the background."""
    db = SessionLocal()
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        db.close()
        return {"error": "Article not found"}

    if not article.category:
        text = (article.title or "") + ". " + (article.description or "")
        if text.strip():
            article.category = classify_article(text)

    db.commit()
    db.close()
    return {
        "status": "processed",
        "article_id": article_id,
        "category": article.category,
    }


@celery_app.task(name="app.worker.fetch_and_process_news")
def fetch_and_process_news():
    """Fetch real headlines from NewsAPI and queue AI processing for each article."""
    news_api_key = os.getenv("NEWS_API_KEY")

    # Fallback to dummy data when no API key is configured
    if not news_api_key:
        from .services.news_fetcher import fetch_and_store_articles
        return fetch_and_store_articles()

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "us",
        "apiKey": news_api_key,
        "pageSize": 10,
    }

    response = requests.get(url, params=params, timeout=15)
    if response.status_code != 200:
        return {"error": response.text}

    data = response.json()
    articles_data = data.get("articles", [])

    db = SessionLocal()
    saved = 0

    for art_data in articles_data:
        title = art_data.get("title")
        article_url = art_data.get("url")
        if not title or not article_url:
            continue

        existing = db.query(Article).filter(Article.url == article_url).first()
        if existing:
            continue

        published_at = None
        if art_data.get("publishedAt"):
            try:
                published_at = datetime.strptime(art_data["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                published_at = None

        article = Article(
            title=title,
            description=art_data.get("description"),
            content=art_data.get("content"),
            source=art_data.get("source", {}).get("name", "Unknown"),
            url=article_url,
            published_at=published_at,
        )
        db.add(article)
        db.commit()
        db.refresh(article)

        process_article.delay(article.id)
        saved += 1

    db.close()
    return {
        "saved": saved,
        "message": f"Fetched {len(articles_data)} articles, queued {saved} for AI processing.",
    }
