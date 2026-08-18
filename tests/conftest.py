import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("AUTHJWT_SECRET_KEY", "test-only-secret-key-with-at-least-32-bytes")
os.environ.setdefault("DEMO_USER", "test-admin")
os.environ.setdefault("DEMO_PASSWORD", "test-password")
os.environ.setdefault("NEWS_MODE", "demo")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENABLE_HF_CLASSIFIER", "false")

import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, engine
from backend.app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
