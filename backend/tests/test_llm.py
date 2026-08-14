import pytest
from pydantic import BaseModel

from app.pipeline.llm import (
    GeminiLLM,
    LLMError,
    _classify,
    _DailyQuotaExhausted,
    _ModelUnavailable,
    _TransientError,
    get_llm,
)


class _Out(BaseModel):
    text: str


def _chain(models: list[str]) -> GeminiLLM:
    """A GeminiLLM without the real client (bypasses __init__/network)."""
    llm = object.__new__(GeminiLLM)
    llm._models = models
    llm._dead = set()
    llm._last_error = ""
    llm.last_model = ""
    return llm


class _CodedError(Exception):
    def __init__(self, code: int, msg: str = ""):
        super().__init__(msg or f"error {code}")
        self.code = code


# Shape of the real Gemini free-tier daily-quota 429 (seen in prod 2026-08-14).
_DAILY_QUOTA_MSG = (
    "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
    "generativelanguage.googleapis.com/generate_content_free_tier_requests, "
    "quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"
)
_MINUTE_QUOTA_MSG = (
    "429 RESOURCE_EXHAUSTED. quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
)


def test_classify_by_status_code():
    assert isinstance(_classify(_CodedError(404)), _ModelUnavailable)
    assert isinstance(_classify(_CodedError(403)), _ModelUnavailable)
    assert isinstance(_classify(_CodedError(429)), _TransientError)
    assert isinstance(_classify(_CodedError(503)), _TransientError)


def test_classify_by_message_and_unknown_default():
    assert isinstance(_classify(Exception("model not found")), _ModelUnavailable)
    assert isinstance(_classify(Exception("RESOURCE_EXHAUSTED: quota")), _TransientError)
    # Unknown errors stay transient so the chain still advances.
    assert isinstance(_classify(Exception("something odd")), _TransientError)


def test_classify_daily_vs_minute_quota():
    # Per-day quota: dead until the provider's daily reset -> skip for the run.
    assert isinstance(_classify(_CodedError(429, _DAILY_QUOTA_MSG)), _DailyQuotaExhausted)
    assert isinstance(_classify(Exception(_DAILY_QUOTA_MSG)), _DailyQuotaExhausted)
    # Per-minute quota: waiting helps -> stays transient (retried, not poisoned).
    assert isinstance(_classify(_CodedError(429, _MINUTE_QUOTA_MSG)), _TransientError)
    assert isinstance(_classify(Exception(_MINUTE_QUOTA_MSG)), _TransientError)


def test_daily_quota_marks_model_dead_for_the_run():
    llm = _chain(["flash", "flash-lite"])
    calls: list[str] = []

    def fake_call(model, prompt, schema):
        calls.append(model)
        if model == "flash":
            raise _DailyQuotaExhausted(_DAILY_QUOTA_MSG)
        return _Out(text=model)

    llm._call_one = fake_call
    assert llm.generate_structured("p", _Out).text == "flash-lite"
    assert "flash" in llm._dead
    # Next call goes straight to the fallback — no wasted retries on flash.
    llm.generate_structured("p", _Out)
    assert calls == ["flash", "flash-lite", "flash-lite"]


def test_unavailable_model_is_skipped_permanently():
    llm = _chain(["dead-model", "good-model"])
    calls: list[str] = []

    def fake_call(model, prompt, schema):
        calls.append(model)
        if model == "dead-model":
            raise _ModelUnavailable("404")
        return _Out(text="ok")

    llm._call_one = fake_call
    assert llm.generate_structured("p", _Out).text == "ok"
    assert llm.last_model == "good-model"
    assert "dead-model" in llm._dead

    # Second call goes straight to the good model.
    llm.generate_structured("p", _Out)
    assert calls == ["dead-model", "good-model", "good-model"]


def test_transient_failure_does_not_poison_the_model():
    llm = _chain(["primary", "backup"])
    fail_once = {"primary": True}

    def fake_call(model, prompt, schema):
        if fail_once.pop(model, False):
            raise _TransientError("429")
        return _Out(text=model)

    llm._call_one = fake_call
    # First call: primary rate-limited -> backup answers.
    assert llm.generate_structured("p", _Out).text == "backup"
    # Primary stays eligible and is preferred again on the next call.
    assert llm.generate_structured("p", _Out).text == "primary"
    assert llm._dead == set()


def test_exhausted_chain_raises_llm_error():
    llm = _chain(["a", "b"])

    def fake_call(model, prompt, schema):
        raise _TransientError("503")

    llm._call_one = fake_call
    with pytest.raises(LLMError):
        llm.generate_structured("p", _Out)


def test_get_llm_returns_none_in_mock_mode():
    # conftest pins USE_MOCK_LLM=true / empty GEMINI_API_KEY.
    assert get_llm() is None
