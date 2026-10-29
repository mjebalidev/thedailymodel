from sqlmodel import select

from app.models import CandidateRecord
from app.pipeline.editorial import DraftArticle, EditionDraft, SourceRef
from app.pipeline.orchestrator import purge_old_editions, save_candidates
from app.pipeline.types import Candidate
from tests.conftest import seed_edition


def _draft(*urls: str) -> EditionDraft:
    article = DraftArticle(
        rank=0, category="Research", importance=3, headline="h", dek="d", body="b",
        sources=[SourceRef(title="t", url=u) for u in urls],
    )
    return EditionDraft(title="t", intro="i", articles=[article])


def test_saves_dropped_kept_and_selected_candidates(session):
    noise = Candidate(title="Stock tips", url="https://x/noise", relevance=10, relevance_reason="noise")
    kept = Candidate(title="New model", url="https://x/kept", relevance=80)
    chosen = Candidate(title="Big launch", url="https://x/chosen", relevance=95, content="full text")

    save_candidates(session, "2026-08-06", [noise, kept, chosen], [kept, chosen], _draft(chosen.url))

    rows = {r.url: r for r in session.exec(select(CandidateRecord)).all()}
    assert (rows["https://x/noise"].kept, rows["https://x/noise"].selected) == (False, False)
    assert rows["https://x/noise"].relevance_reason == "noise"
    assert (rows["https://x/kept"].kept, rows["https://x/kept"].selected) == (True, False)
    assert (rows["https://x/chosen"].kept, rows["https://x/chosen"].selected) == (True, True)
    assert rows["https://x/chosen"].content == "full text"


def test_rerun_for_same_date_replaces_rows(session):
    c = Candidate(title="a", url="https://x/a")
    save_candidates(session, "2026-08-06", [c], [c], _draft())
    save_candidates(session, "2026-08-06", [c], [c], _draft())
    save_candidates(session, "2026-08-07", [c], [c], _draft())

    dates = sorted(r.edition_date for r in session.exec(select(CandidateRecord)).all())
    assert dates == ["2026-08-06", "2026-08-07"]


def test_retention_purge_keeps_the_corpus(session):
    seed_edition(session, "2026-06-01")
    c = Candidate(title="a", url="https://x/a")
    save_candidates(session, "2026-06-01", [c], [c], _draft())

    purge_old_editions(session, "2026-08-06")

    assert len(session.exec(select(CandidateRecord)).all()) == 1
