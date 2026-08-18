from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from .database import Base, engine
from .api import articles, auth

# Create database tables (creates news.db file automatically)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI News Intelligence API", version="1.0")

# Register the routers
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])


@app.get("/")
def root():
    return {"message": "AI News Intelligence API is running!"}
