from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ArticleBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    url: str
    published_at: Optional[datetime] = None

class ArticleCreate(ArticleBase):
    pass

class ArticleResponse(ArticleBase):
    id: int
    category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True   # Allows conversion from SQLAlchemy model