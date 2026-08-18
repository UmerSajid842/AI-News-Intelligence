from datetime import datetime

from ..database import SessionLocal
from ..models import Article
from .classifier import classify_article


def fetch_and_store_articles():
    """Insert deterministic demo fixtures for local development and portfolio demos."""
    db = SessionLocal()
    saved = 0

    # These fixtures are intentionally labeled and do not represent live news.
    dummy_articles = [
        {
            "title": "OpenAI Announces GPT-5 Release Date",
            "description": "The company plans to launch the next generation model in early 2025.",
            "content": "Full story here...",
            "source": "TechCrunch",
            "url": "https://techcrunch.com/openai-gpt5",
            "published_at": datetime.now()
        },
        {
            "title": "Microsoft Acquires AI Cybersecurity Startup",
            "description": "Deal valued at $2.5 billion to strengthen Azure security.",
            "content": "Full story here...",
            "source": "Reuters",
            "url": "https://reuters.com/microsoft-acquires",
            "published_at": datetime.now()
        },
        {
            "title": "Tesla Stock Falls After Delivery Miss",
            "description": "Elon Musk's company missed Q4 expectations by 10%.",
            "content": "Full story here...",
            "source": "Bloomberg",
            "url": "https://bloomberg.com/tesla-stock",
            "published_at": datetime.now()
        }
    ]

    for art_data in dummy_articles:
        # Check if URL already exists to avoid duplicates
        existing = db.query(Article).filter(Article.url == art_data["url"]).first()
        if existing:
            continue

        # Classify the article using the AI pipeline
        text = (art_data["title"] or "") + ". " + (art_data.get("description") or "")
        art_data["category"] = classify_article(text) if text.strip() else "General"

        article = Article(**art_data)
        db.add(article)
        saved += 1

    db.commit()
    db.close()
    return {
        "saved": saved,
        "mode": "demo",
        "message": "Demo fixtures inserted and classified locally. Live ingestion requires NEWS_MODE=live and NEWS_API_KEY.",
    }
