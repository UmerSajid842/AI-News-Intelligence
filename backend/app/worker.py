import logging
import os
from datetime import datetime, timezone

import requests
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

from .database import SessionLocal
from .models import Article
from .services.classifier import classify_article

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)
celery_app.autodiscover_tasks(["app"])


class LiveNewsConfigurationError(RuntimeError):
    """Raised when live ingestion is requested without a complete configuration."""


def get_news_mode() -> str:
    """Return a validated ingestion mode; demo remains the safe default."""
    mode = os.getenv("NEWS_MODE", "demo").strip().lower()
    if mode not in {"demo", "live"}:
        raise LiveNewsConfigurationError("NEWS_MODE must be either 'demo' or 'live'.")
    return mode


def validate_live_configuration() -> tuple[str, str]:
    """Return the provider URL and key required for live ingestion."""
    api_key = os.getenv("NEWS_API_KEY", "").strip()
    if not api_key:
        raise LiveNewsConfigurationError(
            "Live mode requires NEWS_API_KEY. Keep NEWS_MODE=demo until the key is configured."
        )
    provider_url = os.getenv(
        "NEWS_PROVIDER_URL", "https://newsapi.org/v2/top-headlines"
    ).strip()
    if not provider_url.startswith(("https://", "http://")):
        raise LiveNewsConfigurationError("NEWS_PROVIDER_URL must be an HTTP(S) URL.")
    return provider_url, api_key


def parse_provider_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 provider timestamp into a naive UTC datetime for SQLite."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


@celery_app.task(name="app.worker.process_article")
def process_article(article_id: int):
    """Run the article intelligence pipeline in the background."""
    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return {"error": "Article not found"}

        if not article.category:
            text = f"{article.title or ''}. {article.description or ''}".strip()
            if text:
                article.category = classify_article(text)

        db.commit()
        return {
            "status": "processed",
            "article_id": article_id,
            "category": article.category,
        }
    finally:
        db.close()


@celery_app.task(name="app.worker.fetch_and_process_news")
def fetch_and_process_news():
    """Fetch live headlines and queue classification, or run deterministic demo mode."""
    mode = get_news_mode()
    if mode == "demo":
        from .services.news_fetcher import fetch_and_store_articles

        return fetch_and_store_articles()

    provider_url, api_key = validate_live_configuration()
    params = {"country": "us", "apiKey": api_key, "pageSize": 10}

    try:
        response = requests.get(provider_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.exception("Live news provider request failed")
        return {
            "mode": "live",
            "saved": 0,
            "error": "News provider request failed. Check the worker logs and provider configuration.",
        }
    except ValueError:
        logger.exception("Live news provider returned invalid JSON")
        return {
            "mode": "live",
            "saved": 0,
            "error": "News provider returned an invalid response.",
        }

    articles_data = data.get("articles", [])
    if not isinstance(articles_data, list):
        return {"mode": "live", "saved": 0, "error": "News provider returned an invalid article list."}

    db = SessionLocal()
    saved = 0
    queued = 0
    new_article_ids: list[int] = []
    try:
        for art_data in articles_data:
            if not isinstance(art_data, dict):
                continue

            title = (art_data.get("title") or "").strip()
            article_url = (art_data.get("url") or "").strip()
            if not title or not article_url:
                continue

            if db.query(Article).filter(Article.url == article_url).first():
                continue

            source_data = art_data.get("source") or {}
            article = Article(
                title=title,
                description=art_data.get("description"),
                content=art_data.get("content"),
                source=source_data.get("name") or "Unknown",
                url=article_url,
                published_at=parse_provider_timestamp(art_data.get("publishedAt")),
            )
            db.add(article)
            db.flush()
            new_article_ids.append(article.id)
            saved += 1

        db.commit()

        # Queue only newly inserted articles after the insert transaction succeeds.
        for article_id in new_article_ids:
            try:
                process_article.delay(article_id)
                queued += 1
            except Exception:
                logger.exception("Could not queue classification for article %s", article_id)

        return {
            "mode": "live",
            "fetched": len(articles_data),
            "saved": saved,
            "queued": queued,
            "message": f"Fetched {len(articles_data)} provider articles, saved {saved}, and queued {queued} for classification.",
        }
    finally:
        db.close()
