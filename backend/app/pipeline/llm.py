from __future__ import annotations

import json
import logging
from typing import TypeVar

from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import settings

log = logging.getLogger("pipeline.llm")

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Non-recoverable failure after exhausting the fallback chain."""


class _ModelUnavailable(Exception):
    """This specific model can't be used (404 / not found / no access) — skip it."""


class _TransientError(Exception):
    """Temporary failure (rate limit / 5xx / overloaded) — retry, then try next model."""


class _DailyQuotaExhausted(Exception):
    """Per-day quota is gone until the provider's daily reset — no retry can
    succeed within this run, so the model is skipped for the rest of it."""


# Substrings used to classify provider errors when a status code isn't exposed.
_UNAVAILABLE_HINTS = (
    "not found", "404", "does not exist", "not supported", "permission",
    "403", "unsupported", "no access", "invalid model",
)
_TRANSIENT_HINTS = (
    "429", "rate", "quota", "resource_exhausted", "resource exhausted",
    "500", "502", "503", "unavailable", "overloaded", "timeout", "deadline",
)


def _is_daily_quota(msg: str) -> bool:
    """Gemini per-day quota violations carry a quotaId like
    GenerateRequestsPerDayPerProjectPerModel-FreeTier; per-minute ones say PerMinute."""
    return "perday" in msg


def _classify(exc: Exception) -> Exception:
    """Map a provider exception to _ModelUnavailable / _DailyQuotaExhausted /
    _TransientError. Unknown errors count as transient so the chain falls through."""
    msg = str(exc).lower()
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code in (404, 403, 400):
        return _ModelUnavailable(str(exc))
    if code == 429 and _is_daily_quota(msg):
        return _DailyQuotaExhausted(str(exc))
    if code in (429, 500, 502, 503, 504):
        return _TransientError(str(exc))

    if any(h in msg for h in _UNAVAILABLE_HINTS):
        return _ModelUnavailable(str(exc))
    if any(h in msg for h in _TRANSIENT_HINTS):
        if _is_daily_quota(msg):
            return _DailyQuotaExhausted(str(exc))
        return _TransientError(str(exc))
    return _TransientError(str(exc))


class GeminiLLM:
    """google-genai wrapper with structured output and a model fallback chain.

    Tries models in order (smartest → most available). A model that is missing,
    access-denied or out of daily quota is skipped for the rest of the process;
    transient errors are retried a few times, then the next model is tried. Once every model has
    failed, raises LLMError so the caller can fall back to the deterministic mock.
    """

    def __init__(self, api_key: str, models: list[str]) -> None:
        from google import genai  # imported lazily so mock-only runs need no SDK

        self._client = genai.Client(api_key=api_key)
        self._models = models or ["gemini-flash-latest"]
        # Individually-dead models: 404 / no access, or per-DAY quota exhausted
        # (dead until the provider's daily reset, i.e. for this whole process).
        # A per-minute 429 on a working model must NOT disqualify it, and a good
        # model is never skipped because a *different* model in the chain is dead.
        self._dead: set[str] = set()
        self._last_error: str = ""  # real reason of the most recent failure
        self.last_model: str = ""  # the model that produced the most recent success

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(_TransientError),
    )
    def _call_one(self, model: str, prompt: str, schema: type[T]) -> T:
        try:
            resp = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                    "temperature": 0.4,
                },
            )
        except Exception as exc:
            raise _classify(exc) from exc

        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, schema):
            return parsed
        text = getattr(resp, "text", "") or ""
        try:
            return schema.model_validate(json.loads(text))
        except Exception as exc:
            # A malformed body is worth one retry, then move on.
            raise _TransientError(f"unparseable response from {model}: {exc}") from exc

    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        for model in self._models:
            if model in self._dead:
                continue
            try:
                result = self._call_one(model, prompt, schema)
                self.last_model = model
                return result
            except _ModelUnavailable as exc:
                log.warning("LLM: model %s unavailable, skipping permanently: %r", model, exc)
                self._dead.add(model)  # only THIS model, not the ones before it
                self._last_error = f"{model}: {exc}"
            except _DailyQuotaExhausted as exc:
                log.warning(
                    "LLM: model %s daily quota exhausted, skipping for this run: %r",
                    model, exc,
                )
                self._dead.add(model)
                self._last_error = f"{model}: {exc}"
            except _TransientError as exc:
                # Transient (429/5xx): try the next model for THIS call, but keep
                # this model eligible — it will be retried first on the next call.
                log.warning("LLM: model %s transient failure, trying next: %r", model, exc)
                self._last_error = f"{model}: {exc}"
        raise LLMError(
            f"all models exhausted ({', '.join(self._models)}): "
            f"{self._last_error or 'no usable models'}"
        )


def get_llm() -> GeminiLLM | None:
    """Return a live LLM client, or None when running in mock mode."""
    if not settings.llm_is_live:
        log.info("LLM: mock mode (no GEMINI_API_KEY or USE_MOCK_LLM=true)")
        return None
    try:
        return GeminiLLM(settings.gemini_api_key, settings.gemini_model_list)
    except Exception as exc:
        log.warning("LLM: failed to init Gemini, falling back to mock: %s", exc)
        return None
