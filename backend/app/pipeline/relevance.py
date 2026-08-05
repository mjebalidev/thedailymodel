from __future__ import annotations

import logging

from pydantic import BaseModel

from ..config import settings
from .llm import GeminiLLM
from .types import Candidate, RelevanceResult

log = logging.getLogger("pipeline.relevance")

# Heuristic vocabulary for the mock (no-LLM) fallback.
_AI_TERMS = [
    "ai", "a.i.", "artificial intelligence", "machine learning", " ml ", "llm",
    "language model", "gpt", "gemini", "claude", "openai", "anthropic", "deepmind",
    "mistral", "llama", "neural", "chatbot", "agent", "hugging face", "nvidia",
    "inference", "training", "fine-tun", "benchmark", "generative", "diffusion",
    "transformer", "dataset", "robot", "autonomous", "copilot", "multimodal",
]
_NOISE_TERMS = [
    "stock", "shares", "buy now", "dividend", "earnings call", "price target",
    "moratorium", "zoning", "horoscope", "recipe", "nfl", "box office",
]


class ScoredCandidate(BaseModel):
    candidate: Candidate
    keep: bool
    score: int
    reason: str


def _score_mock(candidates: list[Candidate]) -> list[ScoredCandidate]:
    out: list[ScoredCandidate] = []
    for c in candidates:
        text = f" {c.title} {c.snippet} {c.publisher} ".lower()
        ai_hits = sum(1 for t in _AI_TERMS if t in text)
        noise_hits = sum(1 for t in _NOISE_TERMS if t in text)
        # RSS feeds are curated AI sources → trust them more; web search is noisier.
        base = 50 if c.origin == "rss" else 20
        score = min(100, base + ai_hits * 15)
        if noise_hits and ai_hits < 2:
            score = max(0, score - 40)
        keep = score >= settings.relevance_min_score
        out.append(
            ScoredCandidate(
                candidate=c,
                keep=keep,
                score=score,
                reason=f"{c.origin}, ai_terms={ai_hits}, noise={noise_hits}",
            )
        )
    return out


def _build_prompt(candidates: list[Candidate]) -> str:
    lines = [
        "You are a relevance filter for a daily *AI* newspaper.",
        "For EACH candidate below, decide keep=true ONLY if it is genuinely about",
        "artificial intelligence / machine learning — AI research, models, products,",
        "the companies building them, AI policy/regulation, AI tools, or AI's impact",
        "on society. Give a relevance score 0-100 and a short reason.",
        "",
        "DROP as noise (keep=false, low score): generic stock/market tips, company",
        "earnings with no AI substance, local data-center zoning disputes, celebrity,",
        "sports, crypto price talk, listicles, and anything only tangentially 'AI'.",
        "",
        "Return one item per candidate, echoing its index.",
        "",
        "CANDIDATES:",
    ]
    for i, c in enumerate(candidates):
        lines.append(f"[{i}] {c.title} — {c.publisher}\n    {c.snippet[:220]}")
    return "\n".join(lines)


def _score_live(llm: GeminiLLM, candidates: list[Candidate]) -> list[ScoredCandidate]:
    result: RelevanceResult = llm.generate_structured(_build_prompt(candidates), RelevanceResult)
    by_index = {it.index: it for it in result.items}

    out: list[ScoredCandidate] = []
    for i, c in enumerate(candidates):
        it = by_index.get(i)
        if it is None:
            # LLM omitted this one — don't silently drop it.
            out.append(ScoredCandidate(candidate=c, keep=True, score=50, reason="not scored"))
            continue
        keep = it.keep and it.score >= settings.relevance_min_score
        out.append(
            ScoredCandidate(candidate=c, keep=keep, score=it.score, reason=it.reason.strip())
        )
    return out


def score_candidates(
    llm: GeminiLLM | None, candidates: list[Candidate]
) -> list[ScoredCandidate]:
    """Score every candidate for AI-news relevance (keeps all, annotates them)."""
    if not candidates:
        return []
    if llm is None:
        return _score_mock(candidates)
    try:
        return _score_live(llm, candidates)
    except Exception as exc:
        log.warning("Relevance LLM call failed, using heuristic: %s", exc)
        return _score_mock(candidates)


def filter_relevant(
    llm: GeminiLLM | None, candidates: list[Candidate]
) -> list[Candidate]:
    """Drop noisy candidates. Falls back to the full list if it would empty out."""
    if not settings.enable_relevance_filter or not candidates:
        return candidates

    scored = score_candidates(llm, candidates)
    kept: list[Candidate] = []
    for sc in scored:
        sc.candidate.relevance = sc.score
        if sc.keep:
            kept.append(sc.candidate)

    dropped = len(candidates) - len(kept)
    log.info("Relevance filter: kept %d, dropped %d (noise)", len(kept), dropped)

    # Safety net: never let the filter starve the edition.
    if not kept:
        log.warning("Relevance filter dropped everything — keeping original candidates.")
        return candidates
    return kept
