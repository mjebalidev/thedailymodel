from __future__ import annotations

import secrets as _secrets

from fastapi import APIRouter, Header, HTTPException

from ..config import settings
from .. import runner

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _check_secret(provided: str | None) -> None:
    """Constant-time check of the X-Trigger-Secret header.

    An empty TRIGGER_SECRET leaves the endpoint open (local dev only). In
    production the secret is set, so only CI (with the secret) can trigger.
    """
    expected = settings.trigger_secret
    if not expected:
        return
    if not provided or not _secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing trigger secret.")


@router.post("/trigger")
def trigger(
    date: str | None = None,
    x_trigger_secret: str | None = Header(default=None),
) -> dict:
    """Start a daily-edition generation run (manual button or external cron).

    Runs asynchronously; poll GET /api/pipeline/status for progress.
    """
    _check_secret(x_trigger_secret)
    if runner.is_running():
        return {"accepted": False, **runner.get_status()}
    return {"accepted": True, **runner.start(date)}


@router.get("/status")
def status() -> dict:
    return runner.get_status()
