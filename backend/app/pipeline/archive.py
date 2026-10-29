from __future__ import annotations

import heapq
import logging
import math
from array import array

from pydantic import BaseModel
from sqlmodel import Session, select

from ..config import settings
from ..models import Article, Edition
from .analysis import Story
from .llm import GeminiLLM

log = logging.getLogger("pipeline.archive")


class PastArticle(BaseModel):
    """An already-published article offered to the editor as previous coverage."""

    id: int
    date: str
    headline: str
    dek: str
    similarity: float


def article_text(a: Article) -> str:
    return f"{a.headline}\n{a.dek}\n{a.body}"[:4000]


def story_text(story: Story) -> str:
    c = story.primary
    return f"{c.title}\n{story.angle}\n{(c.content or c.snippet)[:1500]}"


def _normalize(vec: list[float]) -> list[float]:
    # Gemini only normalizes full-size vectors; truncated ones must be scaled
    # here so a dot product is the cosine similarity.
    norm = math.sqrt(math.sumprod(vec, vec)) or 1.0
    return [v / norm for v in vec]


def pack(vec: list[float]) -> bytes:
    return array("f", _normalize(vec)).tobytes()


def unpack(blob: bytes) -> array:
    vec = array("f")
    vec.frombytes(blob)
    return vec


def find_related(
    llm: GeminiLLM | None, session: Session, stories: list[Story], before_date: str
) -> list[list[PastArticle]]:
    """For each story, the closest articles published before `before_date`.

    Brute-force cosine over the whole archive: a few thousand vectors take
    well under a second, so no vector index is needed yet. Retrieval is
    optional, so any failure yields no related articles rather than an error.
    """
    empty: list[list[PastArticle]] = [[] for _ in stories]
    if llm is None or not settings.enable_related or not stories:
        return empty

    rows = session.exec(
        select(Article.id, Article.headline, Article.dek, Article.embedding, Edition.date)
        .join(Edition)
        .where(Edition.date < before_date, Article.embedding.is_not(None))
    ).all()
    if not rows:
        return empty
    try:
        queries = llm.embed([story_text(s) for s in stories])
    except Exception as exc:
        log.warning("Archive retrieval skipped, embedding failed: %s", exc)
        return empty

    archive = [(r, unpack(r.embedding)) for r in rows]
    result: list[list[PastArticle]] = []
    for q in queries:
        q = _normalize(q)
        best = heapq.nlargest(
            settings.related_per_story,
            ((math.sumprod(q, vec), r) for r, vec in archive),
            key=lambda pair: pair[0],
        )
        result.append(
            [
                PastArticle(id=r.id, date=r.date, headline=r.headline, dek=r.dek, similarity=sim)
                for sim, r in best
                if sim >= settings.related_min_similarity
            ]
        )
    log.info(
        "Archive: %d past article(s) offered across %d stories (archive size %d)",
        sum(len(r) for r in result), len(stories), len(archive),
    )
    return result


def embed_articles(llm: GeminiLLM | None, session: Session, articles: list[Article]) -> int:
    """Store an embedding on each article that has none. Returns how many were stored."""
    todo = [a for a in articles if a.embedding is None]
    if llm is None or not todo:
        return 0
    try:
        vectors = llm.embed([article_text(a) for a in todo])
    except Exception as exc:
        log.warning("Article embedding failed, will be retried by `cli embed`: %s", exc)
        return 0
    for a, vec in zip(todo, vectors):
        a.embedding = pack(vec)
        session.add(a)
    session.commit()
    return len(todo)
