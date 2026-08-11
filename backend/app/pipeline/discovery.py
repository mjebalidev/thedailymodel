from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from .sources import RSS_FEEDS, WEB_SEARCH_QUERIES
from .types import Candidate

log = logging.getLogger("pipeline.discovery")


def _normalize_url(url: str) -> str:
    """Strip query/fragment and trailing slash so we can dedupe reliably."""
    try:
        p = urlparse(url.strip())
        path = p.path.rstrip("/") or "/"
        return urlunparse((p.scheme, p.netloc.lower(), path, "", "", ""))
    except Exception:
        return url.strip()


def _entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def _clean(text: str) -> str:
    # feedparser summaries can contain HTML; trafilatura handles full pages later,
    # here we just want a short plain-ish snippet.
    import re

    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()[:400]


def _from_rss() -> list[Candidate]:
    out: list[Candidate] = []
    for publisher, feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:  # pragma: no cover - network variability
            log.warning("RSS parse failed for %s: %s", publisher, exc)
            continue
        for entry in parsed.entries[:30]:
            url = entry.get("link")
            title = entry.get("title")
            if not url or not title:
                continue
            out.append(
                Candidate(
                    title=_clean(title),
                    url=url,
                    publisher=publisher,
                    origin="rss",
                    snippet=_clean(entry.get("summary", "")),
                    published=_entry_datetime(entry),
                )
            )
    log.info("RSS discovery: %d raw entries", len(out))
    return out


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _search_one(ddgs, query: str) -> list[dict]:
    """Run one query across several news backends, retrying transient throttles.

    Querying multiple backends (config.web_search_backends) means a single
    engine being rate-limited from the datacenter IP no longer zeros out the
    run. An empty result set is treated as a transient throttle and retried a
    couple of times with backoff — this is the '1 result then it recovers'
    failure mode. Falls back to text search if the news endpoint errors out.
    """
    backends = settings.web_search_backends
    try:
        results = ddgs.news(
            query, region="wt-wt", timelimit="d", max_results=15, backend=backends
        )
    except Exception:
        results = ddgs.text(query, timelimit="d", max_results=15, backend=backends)
    if not results:
        raise RuntimeError(f"empty web-search result for {query!r} (likely throttled)")
    return results


def _from_web_search() -> list[Candidate]:
    if not settings.enable_web_search:
        return []
    try:
        from ddgs import DDGS
    except Exception as exc:  # pragma: no cover
        log.warning("ddgs not available: %s", exc)
        return []

    out: list[Candidate] = []
    with DDGS() as ddgs:
        for query in WEB_SEARCH_QUERIES:
            try:
                results = _search_one(ddgs, query)
            except Exception as exc:  # pragma: no cover - network variability
                log.warning("web search failed for %r after retries: %s", query, exc)
                continue
            for r in results:
                url = r.get("url") or r.get("href")
                title = r.get("title")
                if not url or not title:
                    continue
                published = None
                if r.get("date"):
                    try:
                        published = datetime.fromisoformat(
                            str(r["date"]).replace("Z", "+00:00")
                        )
                    except Exception:
                        published = None
                out.append(
                    Candidate(
                        title=_clean(title),
                        url=url,
                        publisher=_clean(r.get("source", "Web")),
                        origin="web",
                        snippet=_clean(r.get("body", "")),
                        published=published,
                    )
                )
    log.info("Web search discovery: %d raw entries", len(out))
    return out


def discover_candidates() -> list[Candidate]:
    """Gather and dedupe recent AI-news candidates from RSS + web search."""
    raw = _from_rss() + _from_web_search()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=settings.lookback_hours)
    future_limit = now + timedelta(hours=6)  # small skew tolerance
    seen: set[str] = set()
    deduped: list[Candidate] = []
    for c in raw:
        if c.published:
            # Future-dated items have unreliable metadata (bad feed parsing);
            # keep the item but distrust its date so it can't top the ranking.
            if c.published > future_limit:
                c.published = None
            # Drop clearly-old items (undated ones are kept — many blogs omit dates).
            elif c.published < cutoff:
                continue
        key = _normalize_url(c.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    # Recent first; undated items sink to the bottom.
    deduped.sort(key=lambda c: c.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    result = deduped[: settings.max_candidates]
    log.info("Discovery: %d candidates after dedupe/cutoff", len(result))
    return result
