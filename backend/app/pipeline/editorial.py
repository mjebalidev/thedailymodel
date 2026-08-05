from __future__ import annotations

import logging

from pydantic import BaseModel

from .analysis import Story
from .llm import GeminiLLM
from .types import WrittenEdition

log = logging.getLogger("pipeline.editorial")


class SourceRef(BaseModel):
    title: str
    url: str
    publisher: str = ""


class DraftArticle(BaseModel):
    rank: int
    category: str
    importance: int
    headline: str
    dek: str
    body: str
    sources: list[SourceRef]


class EditionDraft(BaseModel):
    title: str
    intro: str
    articles: list[DraftArticle]


def _sources_for(story: Story) -> list[SourceRef]:
    return [
        SourceRef(title=c.title, url=c.url, publisher=c.publisher) for c in story.candidates
    ]


def _write_mock(stories: list[Story]) -> EditionDraft:
    articles: list[DraftArticle] = []
    for rank, story in enumerate(stories):
        c = story.primary
        text = c.content or c.snippet or c.title
        # Split extracted text into a couple of short paragraphs.
        paras = [p.strip() for p in text.split("\n") if p.strip()][:3]
        body = "\n\n".join(paras) if paras else text[:600]
        articles.append(
            DraftArticle(
                rank=rank,
                category=story.category,
                importance=story.importance,
                headline=c.title,
                dek=story.angle,
                body=body,
                sources=_sources_for(story),
            )
        )
    intro = (
        "Today's AI briefing, assembled automatically from labs, media and research feeds. "
        f"{len(articles)} stories selected."
    )
    return EditionDraft(title="The Daily Model", intro=intro, articles=articles)


def _build_prompt(stories: list[Story]) -> str:
    lines = [
        "You are writing today's edition of a daily AI newspaper.",
        "Write a short editor's note (intro) and one article per story below.",
        "Tone: neutral, factual, journalistic. Do NOT invent facts beyond the sources.",
        "For each article echo back its integer `ref`. Body: 2-4 short markdown paragraphs.",
        "",
        "STORIES:",
    ]
    for i, story in enumerate(stories):
        c = story.primary
        content = "\n".join(cc.content or cc.snippet for cc in story.candidates)[:4000]
        lines.append(
            f"### ref {i} — category: {story.category} — angle: {story.angle}\n"
            f"Headline source: {c.title} ({c.publisher})\n"
            f"Content:\n{content}\n"
        )
    return "\n".join(lines)


def _write_live(llm: GeminiLLM, stories: list[Story]) -> EditionDraft:
    written: WrittenEdition = llm.generate_structured(_build_prompt(stories), WrittenEdition)
    by_ref = {w.ref: w for w in written.articles}

    articles: list[DraftArticle] = []
    for rank, story in enumerate(stories):
        w = by_ref.get(rank)
        if w is None:
            # LLM skipped this story — fall back to the raw candidate.
            c = story.primary
            articles.append(
                DraftArticle(
                    rank=rank,
                    category=story.category,
                    importance=story.importance,
                    headline=c.title,
                    dek=story.angle,
                    body=(c.content or c.snippet)[:600],
                    sources=_sources_for(story),
                )
            )
            continue
        articles.append(
            DraftArticle(
                rank=rank,
                category=story.category,
                importance=story.importance,
                headline=w.headline.strip() or story.primary.title,
                dek=w.dek.strip() or story.angle,
                body=w.body.strip(),
                sources=_sources_for(story),
            )
        )
    title = written.edition_title.strip() or "The Daily Model"
    intro = written.intro.strip()
    log.info("Editorial (Gemini): wrote %d articles", len(articles))
    return EditionDraft(title=title, intro=intro, articles=articles)


def write_edition(llm: GeminiLLM | None, stories: list[Story]) -> EditionDraft:
    if not stories:
        return EditionDraft(
            title="The Daily Model",
            intro="No AI news could be gathered for today's edition.",
            articles=[],
        )
    if llm is None:
        return _write_mock(stories)
    try:
        return _write_live(llm, stories)
    except Exception as exc:
        log.warning("Editorial LLM call failed, using mock: %s", exc)
        return _write_mock(stories)
