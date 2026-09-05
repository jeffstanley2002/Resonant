"""Exercise the deployed or local Resonant API with safe demo data."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_RESUME = ROOT / "examples" / "resume_ai_engineer.txt"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, help="API base URL")
    parser.add_argument("--resume", default=str(DEFAULT_RESUME), help="Safe sample resume path")
    parser.add_argument("--target-role", default="AI Engineer")
    parser.add_argument("--location", default="Singapore")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--token", default=os.environ.get("JOBMATCH_BEARER_TOKEN", ""))
    parser.add_argument("--csrf-token", default=os.environ.get("JOBMATCH_CSRF_TOKEN", ""))
    parser.add_argument("--turnstile-token", default=os.environ.get("JOBMATCH_TURNSTILE_TOKEN", ""))
    parser.add_argument(
        "--skip-write-actions",
        action="store_true",
        help="Skip saved-job and feedback writes for read-only smoke checks",
    )
    args = parser.parse_args()

    api = args.api.rstrip("/")
    headers = auth_headers(args.token, args.csrf_token, args.turnstile_token)
    resume_path = pathlib.Path(args.resume)

    try:
        health = request_json("GET", f"{api}/health")
        ready = request_json("GET", f"{api}/ready")
        analysis = upload_resume(f"{api}/resumes/analyze", resume_path, headers)
        matches = request_json(
            "POST",
            f"{api}/agent/matches",
            headers=headers,
            payload={
                "resume_id": analysis["resume_id"],
                "target_role": args.target_role,
                "location": args.location,
                "limit": args.limit,
            },
        )
        validate_smoke_payload(health, ready, analysis, matches)

        write_status = {"saved_job": "skipped", "feedback": "skipped"}
        if not args.skip_write_actions:
            top_match = matches["matches"][0]
            saved = request_json(
                "POST",
                f"{api}/saved-jobs",
                headers=headers,
                payload={
                    "external_job_id": top_match["job"]["external_id"],
                    "title": top_match["job"]["title"],
                    "company": top_match["job"]["company"],
                    "job_url": top_match["job"]["url"],
                },
            )
            feedback = request_json(
                "POST",
                f"{api}/feedback",
                headers=headers,
                payload={"run_id": matches["run_id"], "rating": 5},
            )
            if saved.get("external_job_id") != top_match["job"]["external_id"]:
                raise SmokeError("saved job response did not echo the selected job")
            if feedback.get("status") != "accepted":
                raise SmokeError("feedback was not accepted")
            write_status = {"saved_job": "ok", "feedback": "ok"}

        top_match = matches["matches"][0]
        telemetry = matches.get("telemetry", {})
        print(
            json.dumps(
                {
                    "api": "ok",
                    "readiness": ready["status"],
                    "resume": "ok",
                    "skills": len(analysis["skills"]),
                    "matches": len(matches["matches"]),
                    "top_fit_score": top_match["fit_score"],
                    "mode": matches["mode"],
                    "status": matches["status"],
                    "model": telemetry.get("model"),
                    "provider": telemetry.get("provider"),
                    "model_latency_ms": telemetry.get("model_latency_ms"),
                    "estimated_cost_usd": telemetry.get("estimated_cost_usd"),
                    "input_tokens": telemetry.get("input_tokens"),
                    "output_tokens": telemetry.get("output_tokens"),
                    "llm_attempts": telemetry.get("llm_attempts"),
                    "model_fallback": telemetry.get("model_fallback"),
                    "stages": matches.get("stages", []),
                    "job_cache_hit": telemetry.get("job_cache_hit"),
                    **write_status,
                },
                sort_keys=True,
            )
        )
        return 0
    except (OSError, SmokeError, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}")
        return 1


def auth_headers(token: str, csrf_token: str, turnstile_token: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
    if turnstile_token:
        headers["X-Turnstile-Token"] = turnstile_token
    return headers


def request_json(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None
    request_headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def upload_resume(url: str, path: pathlib.Path, headers: dict[str, str]) -> dict[str, Any]:
    if not path.exists():
        raise SmokeError(f"resume fixture does not exist: {path}")

    boundary = f"resonant-{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(path.name)[0] or "text/plain"
    content = path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n').encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    request_headers = {
        **headers,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def resume_facts(analysis: dict[str, Any]) -> str:
    skills = ", ".join(skill["name"] for skill in analysis.get("skills", [])[:16])
    return f"{analysis.get('summary', '')}\nSkills: {skills}"


def validate_smoke_payload(
    health: dict[str, Any],
    ready: dict[str, Any],
    analysis: dict[str, Any],
    matches: dict[str, Any],
) -> None:
    if health.get("status") != "ok":
        raise SmokeError(f"API health failed: {health}")
    if ready.get("status") != "ready":
        raise SmokeError(f"API readiness failed: {ready}")
    if not analysis.get("resume_id") or len(analysis.get("skills", [])) < 3:
        raise SmokeError("resume analysis did not return enough skills")
    if analysis.get("ai_status") != "succeeded":
        raise SmokeError(f"resume AI analysis did not succeed: {analysis.get('warnings', [])}")
    if matches.get("status") not in {"succeeded", "partial"}:
        raise SmokeError(f"AI matching did not succeed: {matches.get('error_message')}")
    if not matches.get("matches"):
        raise SmokeError("matching did not return any jobs")
    if "resume_text" in matches.get("telemetry", {}):
        raise SmokeError("telemetry leaked resume text")
    top_score = matches["matches"][0].get("fit_score")
    if not isinstance(top_score, int) or top_score < 0 or top_score > 100:
        raise SmokeError("top fit score is outside the expected range")


class SmokeError(Exception):
    """Raised when the smoke target responds but fails a product invariant."""


if __name__ == "__main__":
    sys.exit(main())
