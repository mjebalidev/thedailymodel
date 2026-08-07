import json

from tests.conftest import seed_edition


def test_empty_archive(client):
    assert client.get("/api/editions").json() == []
    assert client.get("/api/editions/latest").status_code == 404
    assert client.get("/api/editions/2026-01-01").status_code == 404


def test_list_is_newest_first_with_article_counts(session, client):
    seed_edition(session, "2026-08-01", n_articles=3)
    seed_edition(session, "2026-08-03", n_articles=1)
    seed_edition(session, "2026-08-02", n_articles=0)

    body = client.get("/api/editions").json()
    assert [(e["date"], e["article_count"]) for e in body] == [
        ("2026-08-03", 1),
        ("2026-08-02", 0),
        ("2026-08-01", 3),
    ]


def test_latest_returns_full_edition_with_ranked_articles(session, client):
    seed_edition(session, "2026-08-01")
    seed_edition(session, "2026-08-03", n_articles=3)

    body = client.get("/api/editions/latest").json()
    assert body["date"] == "2026-08-03"
    assert [a["rank"] for a in body["articles"]] == [0, 1, 2]


def test_get_by_date(session, client):
    seed_edition(session, "2026-08-01")
    assert client.get("/api/editions/2026-08-01").json()["date"] == "2026-08-01"


def test_translations_and_fallback(session, client):
    edition = seed_edition(
        session,
        "2026-08-01",
        n_articles=0,
        i18n_json=json.dumps({"fr": {"title": "Édition du jour", "intro": "Bonjour"}}),
    )

    fr = client.get("/api/editions/latest", params={"lang": "fr"}).json()
    assert fr["title"] == "Édition du jour"
    assert sorted(fr["available_languages"]) == ["en", "fr"]

    # Unknown language falls back to the base (English) content.
    es = client.get("/api/editions/latest", params={"lang": "es"}).json()
    assert es["title"] == edition.title


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["llm"] == "mock"
