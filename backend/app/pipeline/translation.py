from __future__ import annotations

import logging

from .editorial import DraftArticle, EditionDraft
from .llm import GeminiLLM
from .types import TranslatedMeta, TranslatedText

log = logging.getLogger("pipeline.translation")

_LANG_NAMES = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
}


def _language_name(code: str) -> str:
    return _LANG_NAMES.get(code, code)


def _meta_prompt(draft: EditionDraft, lang: str) -> str:
    return (
        f"Translate these two short newspaper strings into {_language_name(lang)}. "
        "Keep a neutral, journalistic tone; do not translate proper nouns / product names.\n\n"
        f"SUBTITLE: {draft.title}\n"
        f"EDITOR'S NOTE: {draft.intro}"
    )


def _article_prompt(a: DraftArticle, lang: str) -> str:
    return (
        f"Translate this news article into {_language_name(lang)}. "
        "Preserve markdown formatting exactly. Do NOT translate proper nouns, "
        "product names, company names or code. Keep a neutral, journalistic tone.\n\n"
        f"HEADLINE: {a.headline}\n"
        f"DEK: {a.dek}\n"
        f"BODY:\n{a.body}"
    )


def translate_edition(
    llm: GeminiLLM | None, draft: EditionDraft, target_langs: list[str]
) -> tuple[dict, list[dict]]:
    """Translate an edition into each target language, one unit per LLM call.

    Per-article calls keep every response small (no truncation) and let a single
    article failure degrade gracefully instead of losing the whole language.

    Returns:
        edition_i18n:  {lang: {"title", "intro"}}
        articles_i18n: list aligned to draft.articles, each {lang: {"headline","dek","body"}}
    """
    edition_i18n: dict = {}
    articles_i18n: list[dict] = [{} for _ in draft.articles]

    if llm is None or not target_langs or not draft.articles:
        if target_langs and llm is None:
            log.info("Translation skipped (mock mode) — serving base language only.")
        return edition_i18n, articles_i18n

    for lang in target_langs:
        try:
            meta = llm.generate_structured(_meta_prompt(draft, lang), TranslatedMeta)
            edition_i18n[lang] = {"title": meta.title.strip(), "intro": meta.intro.strip()}
        except Exception as exc:
            log.warning("Translation of edition meta -> %s failed: %s", lang, exc)

        ok = 0
        for i, a in enumerate(draft.articles):
            try:
                t = llm.generate_structured(_article_prompt(a, lang), TranslatedText)
                articles_i18n[i][lang] = {
                    "headline": t.headline.strip(),
                    "dek": t.dek.strip(),
                    "body": t.body.strip(),
                }
                ok += 1
            except Exception as exc:
                log.warning("Translation of article %d -> %s failed: %s", i, lang, exc)

        log.info("Translation: %s — %d/%d articles translated", lang, ok, len(draft.articles))

    return edition_i18n, articles_i18n
