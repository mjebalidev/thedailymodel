from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Edition(SQLModel, table=True):
    """One daily newspaper edition."""

    id: Optional[int] = Field(default=None, primary_key=True)
    # ISO date string "YYYY-MM-DD" — one edition per day.
    date: str = Field(index=True, unique=True)
    title: str
    intro: str = ""  # editor's note / summary of the day
    status: str = Field(default="published")  # draft | published | failed
    model: str = ""  # which LLM produced it (or "mock")
    candidate_count: int = 0
    # {lang: {"title": ..., "intro": ...}} for non-base languages (base = English).
    i18n_json: str = "{}"
    created_at: datetime = Field(default_factory=_utcnow)

    articles: List["Article"] = Relationship(
        back_populates="edition",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "Article.rank"},
    )


class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    edition_id: int = Field(foreign_key="edition.id", index=True)

    rank: int = 0  # 0 = lead story
    category: str = "General"
    headline: str
    dek: str = ""  # subtitle / standfirst
    body: str = ""  # rewritten editorial body (markdown)
    importance: int = 3  # 1..5
    sources_json: str = "[]"  # JSON list of {title, url, publisher}
    # {lang: {"headline": ..., "dek": ..., "body": ...}} for non-base languages.
    i18n_json: str = "{}"
    # JSON list of past Article ids this article references.
    related_json: str = "[]"
    # Normalized float32 vector of headline + dek + body, for archive retrieval.
    embedding: Optional[bytes] = None

    edition: Optional[Edition] = Relationship(back_populates="articles")


class CandidateRecord(SQLModel, table=True):
    """Every candidate a run discovered, kept or dropped, as a raw corpus.

    Not linked to Edition by foreign key so the retention purge never touches it.
    """

    __tablename__ = "candidate"

    id: Optional[int] = Field(default=None, primary_key=True)
    edition_date: str = Field(index=True)
    url: str = Field(index=True)
    title: str
    publisher: str = ""
    origin: str = "rss"
    snippet: str = ""
    published: Optional[datetime] = None
    content: str = ""
    relevance: Optional[int] = None
    relevance_reason: str = ""
    # Passed the relevance filter / ended up as a source of a published article.
    kept: bool = False
    selected: bool = False
