"""Deterministic tests for the web-search resilience logic (no network)."""

import pytest

from app.pipeline import discovery


class _FakeDDGS:
    """Stand-in for ddgs.DDGS whose news() yields a scripted sequence of
    results per call — so we can drive retry/fallback behavior offline."""

    def __init__(self, news_sequence=None, text_result=None, news_raises=False):
        self._news_seq = list(news_sequence or [])
        self._text_result = text_result or []
        self._news_raises = news_raises
        self.news_calls = 0
        self.text_calls = 0
        self.last_backend = None

    def news(self, query, **kwargs):
        self.news_calls += 1
        self.last_backend = kwargs.get("backend")
        if self._news_raises:
            raise RuntimeError("news endpoint down")
        return self._news_seq.pop(0) if self._news_seq else []

    def text(self, query, **kwargs):
        self.text_calls += 1
        return self._text_result


def test_uses_configured_multi_backend(monkeypatch):
    monkeypatch.setattr(discovery.settings, "web_search_backends", "duckduckgo, bing, yahoo")
    fake = _FakeDDGS(news_sequence=[[{"title": "t", "url": "u"}]])
    discovery._search_one(fake, "ai news")
    assert fake.last_backend == "duckduckgo, bing, yahoo"


@pytest.fixture()
def _no_backoff(monkeypatch):
    """Skip tenacity's real exponential sleep so retry tests stay fast."""
    monkeypatch.setattr(discovery._search_one.retry, "sleep", lambda *_: None)


def test_retries_empty_then_succeeds(_no_backoff):
    # First call returns [] (throttled), second returns real results.
    fake = _FakeDDGS(news_sequence=[[], [{"title": "t", "url": "u"}]])
    results = discovery._search_one(fake, "ai news")
    assert len(results) == 1
    assert fake.news_calls == 2  # retried once


def test_persistent_empty_raises_after_retries(_no_backoff):
    fake = _FakeDDGS(news_sequence=[[], [], []])
    with pytest.raises(RuntimeError):
        discovery._search_one(fake, "ai news")
    assert fake.news_calls == 3  # stop_after_attempt(3)


def test_falls_back_to_text_when_news_errors():
    fake = _FakeDDGS(news_raises=True, text_result=[{"title": "t", "href": "u"}])
    results = discovery._search_one(fake, "ai news")
    assert results == [{"title": "t", "href": "u"}]
    assert fake.text_calls == 1


def test_from_web_search_skips_failing_query_and_keeps_going(monkeypatch):
    # Query 1 fails after retries; queries 2 & 3 succeed — discovery still returns.
    monkeypatch.setattr(discovery, "WEB_SEARCH_QUERIES", ["q1", "q2", "q3"])
    monkeypatch.setattr(discovery.settings, "enable_web_search", True)

    class _DDGSCtx:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(discovery, "DDGS", lambda: _DDGSCtx(), raising=False)

    def fake_search(ddgs, query):
        if query == "q1":
            raise RuntimeError("throttled")
        return [{"title": f"Title {query}", "url": f"https://ex.com/{query}"}]

    monkeypatch.setattr(discovery, "_search_one", fake_search)
    # DDGS is imported inside the function; inject it into the module namespace.
    import sys
    monkeypatch.setitem(sys.modules, "ddgs", type(sys)("ddgs"))
    sys.modules["ddgs"].DDGS = lambda: _DDGSCtx()

    out = discovery._from_web_search()
    urls = {c.url for c in out}
    assert urls == {"https://ex.com/q2", "https://ex.com/q3"}
