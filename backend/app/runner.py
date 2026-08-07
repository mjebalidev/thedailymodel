from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from sqlmodel import Session

from .db import engine
from .pipeline.orchestrator import run_pipeline

log = logging.getLogger("runner")

_lock = threading.Lock()
_thread: threading.Thread | None = None
_state: dict = {
    "status": "idle",  # idle | running | done | error
    "started_at": None,
    "finished_at": None,
    "date": None,
    "edition_id": None,
    "article_count": 0,
    "candidate_count": 0,
    "model": "",
    "detail": "",
}


def get_status() -> dict:
    return dict(_state)


def is_running() -> bool:
    return _state["status"] == "running"


def _worker(date_str: str | None) -> None:
    try:
        with Session(engine) as session:
            edition = run_pipeline(session, date_str)
            _state.update(
                status="done",
                finished_at=datetime.now(timezone.utc).isoformat(),
                date=edition.date,
                edition_id=edition.id,
                article_count=len(edition.articles),
                candidate_count=edition.candidate_count,
                model=edition.model,
                detail="Edition generated.",
            )
    except Exception as exc:
        log.exception("pipeline run failed")
        # The status endpoint is public: expose the error class only, never the
        # raw message (it may carry internal paths, provider responses, etc.).
        _state.update(
            status="error",
            finished_at=datetime.now(timezone.utc).isoformat(),
            detail=f"Pipeline failed ({type(exc).__name__}) — see server logs.",
        )


def start(date_str: str | None = None) -> dict:
    """Kick off a pipeline run in a background thread if none is active."""
    global _thread
    with _lock:
        if is_running():
            return get_status()
        _state.update(
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=None,
            date=date_str,
            edition_id=None,
            article_count=0,
            candidate_count=0,
            model="",
            detail="Pipeline running…",
        )
        _thread = threading.Thread(target=_worker, args=(date_str,), daemon=True)
        _thread.start()
    return get_status()
