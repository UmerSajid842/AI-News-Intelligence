from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    url = Column(String(500), unique=True, index=True)
    published_at = Column(DateTime, nullable=True)
    category = Column(String(100), nullable=True)   # Will be filled by AI later
    created_at = Column(DateTime, default=datetime.utcnow)