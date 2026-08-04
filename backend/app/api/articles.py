from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Article
from ..schemas import ArticleCreate, ArticleResponse
from ..worker import fetch_and_process_news

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[ArticleResponse])
def get_articles(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Get all articles, newest first."""
    articles = db.query(Article).order_by(Article.published_at.desc()).offset(skip).limit(limit).all()
    return articles

@router.post("/fetch")
def fetch_news():
    """Kick off a real NewsAPI fetch and return immediately."""
    result = fetch_and_process_news.delay()
    return {
        "message": "Fetching real news started! Check the Celery worker logs for progress.",
        "task_id": result.id,
    }

@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a single article by ID."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
@router.post("/classify")
def classify_articles(db: Session = Depends(get_db)):
    """
    Runs the AI classifier on all articles that don't have a category yet.
    """
    from ..services.classifier import classify_article
    
    # Get all articles without a category
    unclassified = db.query(Article).filter(Article.category.is_(None)).all()
    
    if not unclassified:
        return {"message": "All articles are already classified!", "classified": 0}
    
    classified_count = 0
    for art in unclassified:
        # Combine title and description for better context
        text = (art.title or "") + ". " + (art.description or "")
        
        if text.strip():
            art.category = classify_article(text)
            classified_count += 1
    
    db.commit()
    
    return {
        "classified": classified_count,
        "total_unclassified_articles_found": len(unclassified)
    }