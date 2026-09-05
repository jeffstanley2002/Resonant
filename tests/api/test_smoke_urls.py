from __future__ import annotations

from scripts import smoke_urls


def test_smoke_helpers_accept_required_security_headers(monkeypatch) -> None:
    def request_json(url: str) -> dict[str, str]:
        if url.endswith("/ready"):
            return {"status": "ready"}
        return {"status": "ok"}

    monkeypatch.setattr(smoke_urls, "request_json", request_json)
    monkeypatch.setattr(
        smoke_urls,
        "request_head",
        lambda _url: (
            200,
            {
                "x-frame-options": "DENY",
                "x-content-type-options": "nosniff",
                "referrer-policy": "strict-origin-when-cross-origin",
            },
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["smoke_urls.py", "--api", "https://api.example.com", "--web", "https://web.example.com"],
    )

    assert smoke_urls.main() == 0


def test_smoke_helpers_reject_failed_readiness(monkeypatch) -> None:
    monkeypatch.setattr(
        smoke_urls,
        "request_json",
        lambda url: {"status": "not_ready"} if url.endswith("/ready") else {"status": "ok"},
    )
    monkeypatch.setattr(
        smoke_urls,
        "request_head",
        lambda _url: (
            200,
            {
                "x-frame-options": "DENY",
                "x-content-type-options": "nosniff",
                "referrer-policy": "strict-origin-when-cross-origin",
            },
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["smoke_urls.py", "--api", "https://api.example.com", "--web", "https://web.example.com"],
    )

    assert smoke_urls.main() == 1


def test_smoke_helpers_reject_missing_security_header(monkeypatch) -> None:
    monkeypatch.setattr(
        smoke_urls,
        "request_json",
        lambda url: {"status": "ready"} if url.endswith("/ready") else {"status": "ok"},
    )
    monkeypatch.setattr(
        smoke_urls,
        "request_head",
        lambda _url: (200, {"x-frame-options": "DENY"}),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["smoke_urls.py", "--api", "https://api.example.com", "--web", "https://web.example.com"],
    )

    assert smoke_urls.main() == 1
