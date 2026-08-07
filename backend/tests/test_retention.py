import pytest
from sqlmodel import select

from app.models import Article, Edition
from app.pipeline.orchestrator import purge_old_editions
from tests.conftest import seed_edition


def test_purges_editions_older_than_window(session):
    # RETENTION_DAYS=30 (conftest); today=2026-08-06 -> cutoff 2026-07-07.
    seed_edition(session, "2026-06-01", n_articles=3)
    seed_edition(session, "2026-07-10", n_articles=2)
    seed_edition(session, "2026-08-06", n_articles=1)

    assert purge_old_editions(session, "2026-08-06") == 1

    dates = sorted(e.date for e in session.exec(select(Edition)).all())
    assert dates == ["2026-07-10", "2026-08-06"]


def test_articles_are_deleted_with_their_edition(session):
    seed_edition(session, "2026-06-01", n_articles=3)
    seed_edition(session, "2026-08-06", n_articles=1)

    purge_old_editions(session, "2026-08-06")

    assert len(session.exec(select(Article)).all()) == 1


def test_zero_or_negative_days_disables_retention(session):
    seed_edition(session, "2020-01-01")
    assert purge_old_editions(session, "2026-08-06", days=0) == 0
    assert purge_old_editions(session, "2026-08-06", days=-5) == 0
    assert len(session.exec(select(Edition)).all()) == 1


def test_purge_is_idempotent(session):
    seed_edition(session, "2026-06-01")
    seed_edition(session, "2026-08-06")
    assert purge_old_editions(session, "2026-08-06") == 1
    assert purge_old_editions(session, "2026-08-06") == 0


def test_malformed_today_raises(session):
    with pytest.raises(ValueError):
        purge_old_editions(session, "not-a-date")
