from app import runner
from app.api import pipeline as pipeline_api


def test_trigger_rejects_missing_or_wrong_secret(client):
    assert client.post("/api/pipeline/trigger").status_code == 401
    assert (
        client.post("/api/pipeline/trigger", headers={"X-Trigger-Secret": "wrong"}).status_code
        == 401
    )


def test_trigger_accepts_correct_secret(client, monkeypatch):
    monkeypatch.setattr(
        pipeline_api.runner, "start", lambda date=None: {"status": "running", "date": date}
    )
    resp = client.post("/api/pipeline/trigger", headers={"X-Trigger-Secret": "test-secret"})
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True


def test_status_is_public(client):
    body = client.get("/api/pipeline/status").json()
    assert "status" in body


def test_failed_run_exposes_only_the_error_class(monkeypatch):
    def boom(session, date_str):
        raise RuntimeError("secret internal path /data/ai_news.db exploded")

    monkeypatch.setattr(runner, "run_pipeline", boom)
    runner._worker("2026-08-06")

    state = runner.get_status()
    assert state["status"] == "error"
    assert "RuntimeError" in state["detail"]
    assert "secret internal path" not in state["detail"]
