from __future__ import annotations

from pydantic import BaseModel


# ── API response models ──────────────────────────────────────────────────
class SourceOut(BaseModel):
    title: str
    url: str
    publisher: str = ""


class ArticleOut(BaseModel):
    id: int
    rank: int
    category: str
    headline: str
    dek: str
    body: str
    importance: int
    sources: list[SourceOut]


class EditionSummary(BaseModel):
    id: int
    date: str
    title: str
    intro: str
    status: str
    model: str
    article_count: int


class EditionOut(EditionSummary):
    lang: str = "en"
    available_languages: list[str] = []
    articles: list[ArticleOut]


class TriggerResult(BaseModel):
    status: str
    date: str
    edition_id: int | None = None
    article_count: int = 0
    candidate_count: int = 0
    model: str = ""
    detail: str = ""
