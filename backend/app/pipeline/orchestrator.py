from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from ..models import Article, Edition
from ..config import settings
from . import analysis, discovery, editorial, relevance, scraper, translation
from .llm import get_llm

log = logging.getLogger("pipeline")


def run_pipeline(session: Session, date_str: str | None = None) -> Edition:
    """Full daily workflow: discover -> scrape -> analyze -> write -> persist.

    Idempotent per day: re-running for the same date replaces that edition.
    """
    # Normalize (and validate) the requested date up front — a malformed date
    # would otherwise produce a bogus edition and break retention math.
    date_str = date.fromisoformat(
        date_str or datetime.now(timezone.utc).date().isoformat()
    ).isoformat()
    log.info("=== Pipeline start for %s ===", date_str)

    llm = get_llm()

    # 1. Research agent — discover candidate articles.
    candidates = discovery.discover_candidates()

    # 2. Relevance agent — drop the noise before spending time scraping.
    candidates = relevance.filter_relevant(llm, candidates)

    # 3. Scrape full article text of the relevant ones (best-effort, browser-free).
    scraper.enrich(candidates)

    # 4 & 5. Analysis + editorial (Gemini, or deterministic mock).
    stories = analysis.analyze(llm, candidates)
    draft = editorial.write_edition(llm, stories)

    # 6. Translation agent — render the edition into the other languages.
    target_langs = settings.target_languages if settings.enable_translation else []
    edition_i18n, articles_i18n = translation.translate_edition(llm, draft, target_langs)

    # Label the edition with the model that actually produced it (llm.last_model
    # is empty if every model in the chain failed and we fell back to the mock).
    model_label = llm.last_model if (llm is not None and llm.last_model) else "mock"

    # 6. Persist — replace any existing edition for this date.
    existing = session.exec(select(Edition).where(Edition.date == date_str)).first()
    if existing is not None:
        session.delete(existing)
        session.commit()

    edition = Edition(
        date=date_str,
        title=draft.title,
        intro=draft.intro,
        status="published" if draft.articles else "failed",
        model=model_label,
        candidate_count=len(candidates),
        i18n_json=json.dumps(edition_i18n, ensure_ascii=False),
    )
    session.add(edition)
    session.commit()
    session.refresh(edition)

    for i, a in enumerate(draft.articles):
        session.add(
            Article(
                edition_id=edition.id,
                rank=a.rank,
                category=a.category,
                headline=a.headline,
                dek=a.dek,
                body=a.body,
                importance=a.importance,
                sources_json=json.dumps([s.model_dump() for s in a.sources]),
                i18n_json=json.dumps(articles_i18n[i], ensure_ascii=False),
            )
        )
    session.commit()
    session.refresh(edition)

    # 7. Retention — keep the archive (and the DB) bounded.
    purged = purge_old_editions(session, date_str)
    if purged:
        log.info("retention: purged %d edition(s) older than %d days", purged, settings.retention_days)

    log.info(
        "=== Pipeline done for %s: %d articles from %d candidates (%s) ===",
        date_str,
        len(draft.articles),
        len(candidates),
        model_label,
    )
    return edition


def purge_old_editions(session: Session, today: str, days: int | None = None) -> int:
    """Delete editions dated more than `days` before `today` (0/negative = keep all).

    Articles are removed with their edition via the relationship cascade.
    Returns the number of editions purged.
    """
    days = settings.retention_days if days is None else days
    if days <= 0:
        return 0
    cutoff = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
    old = session.exec(select(Edition).where(Edition.date < cutoff)).all()
    for e in old:
        session.delete(e)
    if old:
        session.commit()
    return len(old)
