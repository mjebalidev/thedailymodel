from __future__ import annotations

import logging
import re

from pydantic import BaseModel

from ..config import settings
from .llm import GeminiLLM
from .types import AnalysisResult, Candidate

log = logging.getLogger("pipeline.analysis")

CATEGORIES = ["Research", "Products", "Business", "Policy", "Tools", "Society"]

_CATEGORY_KEYWORDS = {
    "Research": ["arxiv", "paper", "benchmark", "研究", "study", "model card", "sota"],
    "Policy": ["regulation", "eu ai act", "law", "policy", "senate", "governance", "ban"],
    "Business": ["funding", "raise", "valuation", "acquire", "ipo", "revenue", "startup"],
    "Tools": ["open source", "sdk", "library", "framework", "api", "release", "github"],
    "Society": ["job", "ethic", "bias", "art", "deepfake", "safety", "society"],
    "Products": ["launch", "app", "feature", "chatbot", "assistant", "product"],
}


class Story(BaseModel):
    """A selected, categorized story with its supporting sources."""

    category: str
    importance: int
    angle: str
    candidates: list[Candidate]

    @property
    def primary(self) -> Candidate:
        return self.candidates[0]


def _guess_category(text: str) -> str:
    text = text.lower()
    best, score = "Products", 0
    for cat, kws in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in text)
        if hits > score:
            best, score = cat, hits
    return best


def _analyze_mock(candidates: list[Candidate]) -> list[Story]:
    """Deterministic heuristic selection when no LLM is available."""
    seen_titles: list[str] = []
    stories: list[Story] = []
    for c in candidates:
        norm = re.sub(r"[^a-z0-9 ]", "", c.title.lower())
        # crude near-duplicate guard: skip if it shares a long prefix with a kept title
        if any(norm[:40] and norm[:40] == t[:40] for t in seen_titles):
            continue
        seen_titles.append(norm)
        text = f"{c.title} {c.snippet}"
        importance = 5 if any(k in c.publisher.lower() for k in ("openai", "deepmind", "google")) else 3
        stories.append(
            Story(
                category=_guess_category(text),
                importance=importance,
                angle=(c.snippet[:140] or c.title),
                candidates=[c],
            )
        )
        if len(stories) >= settings.max_articles:
            break
    log.info("Analysis (mock): selected %d stories", len(stories))
    return stories


def _build_prompt(candidates: list[Candidate]) -> str:
    lines = [
        "You are the news editor of a daily AI newspaper.",
        "Below are candidate articles discovered today. Select the most newsworthy",
        f"stories (at most {settings.max_articles}). Cluster articles that cover the",
        "SAME event into one story (list their URLs together). Assign a category",
        f"(one of: {', '.join(CATEGORIES)}), an importance 1-5, and a one-sentence angle.",
        "Only use URLs that appear in the list below.",
        "",
        "CANDIDATES:",
    ]
    for i, c in enumerate(candidates):
        lines.append(
            f"[{i}] {c.title} — {c.publisher}\n"
            f"    url: {c.url}\n"
            f"    summary: {(c.content or c.snippet)[:300]}"
        )
    return "\n".join(lines)


def _analyze_live(llm: GeminiLLM, candidates: list[Candidate]) -> list[Story]:
    by_url = {c.url: c for c in candidates}
    result: AnalysisResult = llm.generate_structured(_build_prompt(candidates), AnalysisResult)

    stories: list[Story] = []
    for s in result.stories:
        resolved = [by_url[u] for u in s.source_urls if u in by_url]
        if not resolved:
            continue  # drop hallucinated / empty selections
        category = s.category if s.category in CATEGORIES else _guess_category(resolved[0].title)
        stories.append(
            Story(
                category=category,
                importance=max(1, min(5, s.importance)),
                angle=s.angle.strip(),
                candidates=resolved,
            )
        )
    stories.sort(key=lambda s: s.importance, reverse=True)
    stories = stories[: settings.max_articles]
    log.info("Analysis (Gemini): selected %d stories", len(stories))
    return stories


def analyze(llm: GeminiLLM | None, candidates: list[Candidate]) -> list[Story]:
    if not candidates:
        return []
    if llm is None:
        return _analyze_mock(candidates)
    try:
        stories = _analyze_live(llm, candidates)
        return stories or _analyze_mock(candidates)
    except Exception as exc:
        log.warning("Analysis LLM call failed, using mock: %s", exc)
        return _analyze_mock(candidates)
