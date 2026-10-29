import json

from sqlmodel import select

from app.models import Article
from app.pipeline import archive, editorial
from app.pipeline.analysis import Story
from app.pipeline.archive import PastArticle
from app.pipeline.types import Candidate, WrittenArticle, WrittenEdition
from tests.conftest import seed_edition

# Toy 3-d "embeddings": the topic word in a text picks its direction.
_TOPICS = {"robot": [1.0, 0.0, 0.0], "chip": [0.0, 1.0, 0.0], "policy": [0.0, 0.0, 1.0]}


class FakeLLM:
    def __init__(self, written: WrittenEdition | None = None) -> None:
        self.written = written

    def embed(self, texts):
        return [next(v for k, v in _TOPICS.items() if k in t.lower()) for t in texts]

    def generate_structured(self, prompt, schema):
        return self.written


def _story(title: str) -> Story:
    return Story(category="Research", importance=3, angle=title,
                 candidates=[Candidate(title=title, url=f"https://x/{title}")])


def _seed(session, date: str, headline: str) -> Article:
    edition = seed_edition(session, date, n_articles=0)
    article = Article(edition_id=edition.id, headline=headline, embedding=archive.pack(
        _TOPICS[next(k for k in _TOPICS if k in headline.lower())]))
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


def test_finds_past_articles_on_the_same_subject(session):
    robot = _seed(session, "2026-08-01", "Robot arm learns to fold laundry")
    _seed(session, "2026-08-02", "New chip doubles inference speed")

    related = archive.find_related(FakeLLM(), session, [_story("Robot startup raises")], "2026-08-06")

    assert [p.id for p in related[0]] == [robot.id]


def test_ignores_same_day_and_later_articles(session):
    _seed(session, "2026-08-06", "Robot today")
    _seed(session, "2026-08-07", "Robot tomorrow")

    related = archive.find_related(FakeLLM(), session, [_story("Robot news")], "2026-08-06")

    assert related == [[]]


def test_no_retrieval_in_mock_mode(session):
    _seed(session, "2026-08-01", "Robot arm")
    assert archive.find_related(None, session, [_story("Robot")], "2026-08-06") == [[]]


def test_embed_articles_fills_only_missing_vectors(session):
    edition = seed_edition(session, "2026-08-01", n_articles=0)
    done = Article(edition_id=edition.id, headline="Chip", embedding=b"keep")
    todo = Article(edition_id=edition.id, headline="Policy update")
    session.add_all([done, todo])
    session.commit()

    assert archive.embed_articles(FakeLLM(), session, [done, todo]) == 1

    stored = {a.headline: a.embedding for a in session.exec(select(Article)).all()}
    assert stored["Chip"] == b"keep"
    assert list(archive.unpack(stored["Policy update"])) == [0.0, 0.0, 1.0]


def test_editor_cannot_cite_ids_it_was_not_offered():
    stories = [_story("Robot a"), _story("Chip b")]
    related = [
        [PastArticle(id=7, date="2026-08-01", headline="h", dek="d", similarity=0.9)],
        [PastArticle(id=8, date="2026-08-02", headline="h", dek="d", similarity=0.9)],
    ]
    written = WrittenEdition(edition_title="t", intro="i", articles=[
        WrittenArticle(ref=0, headline="a", dek="d", body="b", related_ids=[7, 7, 8, 99]),
        WrittenArticle(ref=1, headline="b", dek="d", body="b"),
    ])

    draft = editorial.write_edition(FakeLLM(written), stories, related)

    assert [a.related_ids for a in draft.articles] == [[7], []]


def test_api_resolves_related_articles_in_the_requested_language(session, client):
    past = _seed(session, "2026-08-01", "Robot arm")
    past.i18n_json = json.dumps({"fr": {"headline": "Bras robot"}})
    session.add(past)
    today = seed_edition(session, "2026-08-06", n_articles=0)
    session.add(Article(edition_id=today.id, headline="Robot follow-up",
                        related_json=json.dumps([past.id, 12345])))
    session.commit()

    body = client.get("/api/editions/2026-08-06?lang=fr").json()

    assert body["articles"][0]["related"] == [
        {"id": past.id, "date": "2026-08-01", "headline": "Bras robot"}
    ]
