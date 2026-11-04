"""Non-destructive smoke verification for a deployed SecureCode candidate.

The runner receives all credentials through environment variables so neither the
command line nor the generated artifact contain password or token values.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def request_json(url: str, method: str = "GET", payload: dict | None = None, headers: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    merged_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        merged_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, method=method, headers=merged_headers)
    with urlopen(request, timeout=20) as response:
        return response.status, json.loads(response.read().decode("utf-8")), dict(response.headers)


def main() -> None:
    base_url = os.environ.get("SECURECODE_CANDIDATE_URL", "").rstrip("/")
    username = os.environ.get("SMOKE_USERNAME", "")
    password = os.environ.get("SMOKE_PASSWORD", "")
    if not all([base_url, username, password]):
        print("SECURECODE_CANDIDATE_URL, SMOKE_USERNAME and SMOKE_PASSWORD are required.", file=sys.stderr)
        sys.exit(2)
    if not base_url.startswith("https://"):
        print("Candidate URL must use HTTPS.", file=sys.stderr)
        sys.exit(2)

    results = {"candidate_url": base_url, "timestamp_utc": datetime.now(timezone.utc).isoformat(), "checks": {}}
    try:
        status, health, headers = request_json(f"{base_url}/health")
        results["checks"]["health"] = status == 200 and health.get("status") == "ok"
        results["checks"]["security_headers"] = headers.get("X-Content-Type-Options") == "nosniff"

        login_body = urlencode({"username": username, "password": password}).encode("utf-8")
        login_request = Request(f"{base_url}/api/v1/auth/token", data=login_body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        with urlopen(login_request, timeout=20) as response:
            token = json.loads(response.read().decode("utf-8"))["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        _, profile, _ = request_json(f"{base_url}/api/v1/auth/me", headers=auth_headers)
        _, history, _ = request_json(f"{base_url}/api/v1/evaluations/history?limit=1", headers=auth_headers)
        results["checks"]["authenticated_profile"] = profile.get("username") == username and profile.get("active") is True
        results["checks"]["authorized_history"] = isinstance(history.get("evaluations"), list)
    except (HTTPError, URLError, KeyError, ValueError) as error:
        results["error"] = type(error).__name__

    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/candidate_smoke_validation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if not all(results["checks"].values()) or "error" in results:
        sys.exit(1)


if __name__ == "__main__":
    main()
