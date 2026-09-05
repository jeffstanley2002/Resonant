from __future__ import annotations

from scripts import demo_smoke


def test_demo_smoke_accepts_full_workflow(monkeypatch) -> None:
    def request_json(method, url, headers=None, payload=None):
        if url.endswith("/health"):
            return {"status": "ok"}
        if url.endswith("/ready"):
            return {"status": "ready"}
        if url.endswith("/agent/matches"):
            return {
                "run_id": "run_test",
                "mode": "demo",
                "status": "succeeded",
                "stages": [],
                "matches": [
                    {
                        "job": {
                            "external_id": "job_1",
                            "title": "AI Engineer",
                            "company": "SignalWorks",
                            "url": "https://example.com/job",
                        },
                        "fit_score": 94,
                    }
                ],
                "telemetry": {"estimated_cost_usd": 0, "job_cache_hit": False},
            }
        if url.endswith("/saved-jobs"):
            return {
                "external_job_id": payload["external_job_id"],
                "title": payload["title"],
                "company": payload["company"],
                "job_url": payload["job_url"],
            }
        if url.endswith("/feedback"):
            return {"status": "accepted"}
        raise AssertionError(url)

    monkeypatch.setattr(demo_smoke, "request_json", request_json)
    monkeypatch.setattr(
        demo_smoke,
        "upload_resume",
        lambda _url, _path, _headers: {
            "resume_id": "resume_test",
            "summary": "AI engineer with Python, FastAPI, and LangGraph.",
            "ai_status": "succeeded",
            "skills": [{"name": "Python"}, {"name": "FastAPI"}, {"name": "LangGraph"}],
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        ["demo_smoke.py", "--api", "http://127.0.0.1:8000"],
    )

    assert demo_smoke.main() == 0


def test_demo_smoke_rejects_empty_matches(monkeypatch) -> None:
    monkeypatch.setattr(demo_smoke, "request_json", lambda *_args, **_kwargs: {"status": "ok"})
    monkeypatch.setattr(
        demo_smoke,
        "upload_resume",
        lambda _url, _path, _headers: {
            "resume_id": "resume_test",
            "summary": "AI engineer with Python, FastAPI, and LangGraph.",
            "ai_status": "succeeded",
            "skills": [{"name": "Python"}, {"name": "FastAPI"}, {"name": "LangGraph"}],
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        ["demo_smoke.py", "--api", "http://127.0.0.1:8000", "--skip-write-actions"],
    )

    assert demo_smoke.main() == 1


def test_demo_smoke_builds_auth_headers() -> None:
    assert demo_smoke.auth_headers("token", "csrf", "turnstile") == {
        "Authorization": "Bearer token",
        "X-CSRF-Token": "csrf",
        "X-Turnstile-Token": "turnstile",
    }
