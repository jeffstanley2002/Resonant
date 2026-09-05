"""Smoke-test local or deployed Resonant URLs."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api", required=True, help="API base URL, for example https://api.onrender.com"
    )
    parser.add_argument("--web", required=True, help="Web URL, for example https://app.vercel.app")
    args = parser.parse_args()

    api = args.api.rstrip("/")
    web = args.web.rstrip("/")

    health = request_json(f"{api}/health")
    if health.get("status") != "ok":
        print(f"ERROR: API health failed: {health}")
        return 1

    readiness = request_json(f"{api}/ready")
    if readiness.get("status") != "ready":
        print(f"ERROR: API readiness failed: {readiness}")
        return 1

    web_status, web_headers = request_head(web)
    if web_status >= 400:
        print(f"ERROR: frontend returned HTTP {web_status}")
        return 1

    required_headers = ["x-frame-options", "x-content-type-options", "referrer-policy"]
    missing = [header for header in required_headers if header not in web_headers]
    if missing:
        print(f"ERROR: frontend missing security headers: {', '.join(missing)}")
        return 1

    print(json.dumps({"api": "ok", "web": "ok", "security_headers": "ok"}))
    return 0


def request_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def request_head(url: str) -> tuple[int, dict[str, str]]:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        return exc.code, {key.lower(): value for key, value in exc.headers.items()}


if __name__ == "__main__":
    sys.exit(main())
