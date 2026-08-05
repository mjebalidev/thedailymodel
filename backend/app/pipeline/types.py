from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Candidate(BaseModel):
    """A raw article discovered by the research agent."""

    title: str
    url: str
    publisher: str = ""
    origin: str = "rss"  # "rss" | "web" — where the research agent found it
    snippet: str = ""
    published: datetime | None = None
    content: str = ""  # filled in by the scraper (main article text, truncated)
    relevance: int | None = None  # 0-100, set by the relevance filter

    @property
    def has_content(self) -> bool:
        return len(self.content) > 200


# ── Relevance filter ("noise elimination" agent) ─────────────────────────
class RelevanceItem(BaseModel):
    index: int = Field(description="The candidate index you are judging.")
    keep: bool = Field(description="True only if this is genuine AI/ML news.")
    score: int = Field(description="Relevance to AI news, 0-100.", ge=0, le=100)
    reason: str = Field(description="Short justification (a few words).")


class RelevanceResult(BaseModel):
    items: list[RelevanceItem]


# ── LLM structured outputs ───────────────────────────────────────────────
class SelectedStory(BaseModel):
    """Output of the analysis step for a single selected story."""

    source_urls: list[str] = Field(
        description="URLs from the candidate list that cover this story (1-3)."
    )
    category: str = Field(description="One of: Research, Products, Business, Policy, Tools, Society")
    importance: int = Field(description="1 (minor) to 5 (major) news value", ge=1, le=5)
    angle: str = Field(description="One sentence: why this matters today.")


class AnalysisResult(BaseModel):
    stories: list[SelectedStory]


class WrittenArticle(BaseModel):
    """Output of the editorial step for a single article."""

    ref: int = Field(description="The integer id of the story you were asked to write.")
    headline: str
    dek: str = Field(description="A one-sentence standfirst under the headline.")
    body: str = Field(description="2-4 short paragraphs, neutral journalistic tone, markdown.")


class WrittenEdition(BaseModel):
    edition_title: str = Field(description="A catchy masthead subtitle for today's edition.")
    intro: str = Field(description="A 2-3 sentence editor's note summarizing the day in AI.")
    articles: list[WrittenArticle]


# ── Translation agent (per-unit, to stay well under output limits) ────────
class TranslatedMeta(BaseModel):
    title: str = Field(description="Translated edition subtitle.")
    intro: str = Field(description="Translated editor's note.")


class TranslatedText(BaseModel):
    headline: str
    dek: str
    body: str = Field(description="Translated body; preserve markdown exactly.")
