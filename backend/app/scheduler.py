from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from . import runner

log = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """Start the daily cron that triggers a new edition, if enabled."""
    global _scheduler
    if not settings.enable_scheduler:
        log.info("Scheduler disabled (ENABLE_SCHEDULER=false).")
        return
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        lambda: runner.start(),
        CronTrigger(hour=settings.daily_cron_hour, minute=settings.daily_cron_minute),
        id="daily-edition",
        replace_existing=True,
    )
    _scheduler.start()
    log.info(
        "Scheduler started: daily edition at %02d:%02d UTC",
        settings.daily_cron_hour,
        settings.daily_cron_minute,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
