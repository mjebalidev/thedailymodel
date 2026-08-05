from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..models import Edition
from ..schemas import ArticleOut, EditionOut, EditionSummary, SourceOut

router = APIRouter(prefix="/api/editions", tags=["editions"])


def _edition_i18n(e: Edition) -> dict:
    return json.loads(e.i18n_json or "{}")


def _available_languages(e: Edition) -> list[str]:
    return [settings.base_language, *_edition_i18n(e).keys()]


def _to_summary(e: Edition, lang: str) -> EditionSummary:
    tr = _edition_i18n(e).get(lang, {})
    return EditionSummary(
        id=e.id,
        date=e.date,
        title=tr.get("title") or e.title,
        intro=tr.get("intro") or e.intro,
        status=e.status,
        model=e.model,
        article_count=len(e.articles),
    )


def _to_out(e: Edition, lang: str) -> EditionOut:
    articles = []
    for a in sorted(e.articles, key=lambda a: a.rank):
        tr = json.loads(a.i18n_json or "{}").get(lang, {})
        articles.append(
            ArticleOut(
                id=a.id,
                rank=a.rank,
                category=a.category,
                headline=tr.get("headline") or a.headline,
                dek=tr.get("dek") or a.dek,
                body=tr.get("body") or a.body,
                importance=a.importance,
                sources=[SourceOut(**s) for s in json.loads(a.sources_json or "[]")],
            )
        )
    return EditionOut(
        **_to_summary(e, lang).model_dump(),
        lang=lang,
        available_languages=_available_languages(e),
        articles=articles,
    )


@router.get("", response_model=list[EditionSummary])
def list_editions(
    lang: str = Query(default=None),
    session: Session = Depends(get_session),
) -> list[EditionSummary]:
    lang = (lang or settings.base_language).lower()
    editions = session.exec(select(Edition).order_by(Edition.date.desc())).all()
    return [_to_summary(e, lang) for e in editions]


@router.get("/latest", response_model=EditionOut)
def latest_edition(
    lang: str = Query(default=None),
    session: Session = Depends(get_session),
) -> EditionOut:
    lang = (lang or settings.base_language).lower()
    edition = session.exec(select(Edition).order_by(Edition.date.desc())).first()
    if edition is None:
        raise HTTPException(status_code=404, detail="No edition has been generated yet.")
    return _to_out(edition, lang)


@router.get("/{date}", response_model=EditionOut)
def get_edition(
    date: str,
    lang: str = Query(default=None),
    session: Session = Depends(get_session),
) -> EditionOut:
    lang = (lang or settings.base_language).lower()
    edition = session.exec(select(Edition).where(Edition.date == date)).first()
    if edition is None:
        raise HTTPException(status_code=404, detail=f"No edition for {date}.")
    return _to_out(edition, lang)
