import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Article
from ..schemas import ArticleResponse
from ..security import get_current_user
from ..worker import fetch_and_process_news

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[ArticleResponse])
def get_articles(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Get articles, newest first, with a bounded page size."""
    safe_limit = min(max(limit, 1), 100)
    return (
        db.query(Article)
        .order_by(Article.published_at.desc(), Article.created_at.desc())
        .offset(max(skip, 0))
        .limit(safe_limit)
        .all()
    )


@router.post("/fetch")
def fetch_news(current_user: str = Depends(get_current_user)):
    """Load deterministic demo articles or queue an optional live-news fetch."""
    mode = os.getenv("NEWS_MODE", "demo").lower()
    if mode != "live":
        from ..services.news_fetcher import fetch_and_store_articles

        return fetch_and_store_articles()

    result = fetch_and_process_news.delay()
    return {
        "message": "Live news fetch queued. Check the worker logs for progress.",
        "task_id": result.id,
        "mode": "live",
    }


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a single article by ID."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/classify")
def classify_articles(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Classify every article that does not have a category."""
    from ..services.classifier import classify_article

    unclassified = db.query(Article).filter(Article.category.is_(None)).all()
    if not unclassified:
        return {"message": "All articles are already classified!", "classified": 0}

    classified_count = 0
    for article in unclassified:
        text = f"{article.title or ''}. {article.description or ''}".strip()
        if text:
            article.category = classify_article(text)
            classified_count += 1

    db.commit()
    return {
        "classified": classified_count,
        "total_unclassified_articles_found": len(unclassified),
    }
