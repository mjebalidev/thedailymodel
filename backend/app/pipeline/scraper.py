from __future__ import annotations

import logging

import httpx
import trafilatura

from .types import Candidate

log = logging.getLogger("pipeline.scraper")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AINewsBot/0.1; +https://example.com/bot) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_MAX_CHARS = 6000


def _extract(url: str) -> str:
    """Fetch a URL and extract clean main-article text via trafilatura.

    trafilatura is a lightweight, browser-free SOTA article extractor: it strips
    nav/ads/boilerplate and returns the core text — ideal for feeding an LLM.
    """
    try:
        with httpx.Client(
            headers=_HEADERS, timeout=15.0, follow_redirects=True
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        log.debug("fetch failed %s: %s", url, exc)
        return ""

    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
    except Exception as exc:
        log.debug("extract failed %s: %s", url, exc)
        return ""

    return (text or "").strip()[:_MAX_CHARS]


def enrich(candidates: list[Candidate]) -> list[Candidate]:
    """Fill in full article text for each candidate (best-effort, in place)."""
    enriched = 0
    for c in candidates:
        content = _extract(c.url)
        if content:
            c.content = content
            enriched += 1
        elif c.snippet:
            # Keep the RSS/search snippet as a minimal fallback.
            c.content = c.snippet
    log.info("Scraper: enriched %d/%d candidates with full text", enriched, len(candidates))
    return candidates
