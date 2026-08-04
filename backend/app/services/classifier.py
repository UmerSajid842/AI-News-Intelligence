from functools import lru_cache
import os


CATEGORIES = [
    "Technology",
    "Finance",
    "Healthcare",
    "Sports",
    "Politics",
    "Artificial Intelligence",
    "Cybersecurity",
    "Startups",
    "Energy",
    "Education",
    "Mergers and Acquisitions",
    "Automotive",
    "Space",
]


KEYWORD_MAP = {
    "Artificial Intelligence": ["ai", "artificial intelligence", "llm", "model", "chatgpt", "openai"],
    "Cybersecurity": ["security", "cyber", "ransomware", "breach", "hack"],
    "Finance": ["stock", "market", "earnings", "investor", "trading", "revenue"],
    "Healthcare": ["health", "medical", "clinic", "hospital", "drug", "pharma"],
    "Sports": ["sport", "league", "match", "game", "season", "tournament"],
    "Politics": ["election", "senate", "congress", "policy", "government", "president"],
    "Energy": ["oil", "gas", "solar", "battery", "electric", "energy"],
    "Automotive": ["car", "vehicle", "tesla", "ev", "automotive"],
    "Space": ["space", "rocket", "satellite", "nasa", "launch"],
}


@lru_cache(maxsize=1)
def _load_classifier():
    if os.getenv("ENABLE_HF_CLASSIFIER", "").lower() not in {"1", "true", "yes"}:
        return None

    try:
        from transformers import pipeline

        return pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,
        )
    except Exception:
        return None


def classify_article(text):
    """Returns the most relevant category for an article."""
    normalized_text = (text or "").strip()
    if len(normalized_text) < 5:
        return "General"

    classifier = _load_classifier()
    if classifier is not None:
        try:
            result = classifier(normalized_text, CATEGORIES)
            return result["labels"][0]
        except Exception:
            pass

    lowered_text = normalized_text.lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(keyword in lowered_text for keyword in keywords):
            return category

    return "General"
