"""Shared fixtures. Environment is pinned BEFORE any app import so the cached
Settings object (and the engine built from it) point at a throwaway database,
regardless of what a local .env contains."""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp(prefix='tdm-test-')}/test.db"
os.environ["USE_MOCK_LLM"] = "true"
os.environ["GEMINI_API_KEY"] = ""
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["RETENTION_DAYS"] = "30"
os.environ["LANGUAGES"] = "en,fr,de"
os.environ["TRIGGER_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, delete  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Article, Edition  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db() -> None:
    init_db()


@pytest.fixture()
def session(_db: None):
    """A session on an empty database (tables wiped before each test)."""
    with Session(engine) as s:
        s.exec(delete(Article))
        s.exec(delete(Edition))
        s.commit()
        yield s


@pytest.fixture()
def client(session: Session):
    with TestClient(app) as c:
        yield c


def seed_edition(session: Session, date: str, n_articles: int = 2, **kwargs) -> Edition:
    edition = Edition(date=date, title=f"Edition {date}", **kwargs)
    session.add(edition)
    session.commit()
    session.refresh(edition)
    for i in range(n_articles):
        session.add(Article(edition_id=edition.id, rank=i, headline=f"Headline {i} of {date}"))
    session.commit()
    return edition
