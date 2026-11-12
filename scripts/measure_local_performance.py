"""Collect reproducible local performance and resource observations.

This tool intentionally refuses non-local HTTP and database targets. It records
observations only; it does not estimate cloud invoices or alter financial data.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import quantiles
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import psutil
from sqlalchemy import create_engine, text

CONTROLS = ("gh-001", "gh-002", "gh-003")
PROFILES = ("small", "medium", "large")
LOCAL_API = "http://127.0.0.1:8000"
LOCAL_MOCK = "http://127.0.0.1:8001"


@dataclass(frozen=True)
class Observation:
    control: str
    profile: str
    sequence: int
    status_code: int
    elapsed_ms: float
    response_bytes: int
    error: str
    captured_at_utc: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evaluations-per-control", type=int, default=100)
    parser.add_argument("--api-pid", type=int)
    parser.add_argument("--api-base-url", default=LOCAL_API)
    parser.add_argument("--mock-base-url", default=LOCAL_MOCK)
    return parser.parse_args()


def _require_local_url(value: str, expected: str, label: str) -> str:
    parsed = urlsplit(value)
    if value.rstrip("/") != expected or parsed.hostname != "127.0.0.1":
        raise ValueError(f"{label} must be the fixed local endpoint {expected}.")
    return value.rstrip("/")


def _require_test_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    parsed = urlsplit(database_url)
    if not database_url or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("DATABASE_URL must point to local PostgreSQL.")
    if parsed.port not in {None, 5432} or not parsed.path.rstrip("/").endswith("securecode_test"):
        raise ValueError("DATABASE_URL must target the local securecode_test database.")
    return database_url


def _read_secret_environment(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"{name} must be configured for local measurements.")
    return value


def _request_json(url: str, payload: dict[str, str] | None = None, token: str | None = None) -> tuple[int, bytes]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()
    except URLError as error:
        raise RuntimeError(f"Local endpoint unavailable: {error.reason}") from error


def _authenticate(api_base_url: str, username: str, password: str) -> str:
    request = Request(
        f"{api_base_url}/api/v1/auth/token",
        data=urlencode({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"Local login failed with HTTP {error.code}.") from error
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Local login response did not include an access token.")
    return access_token


def _database_sizes(database_url: str) -> dict[str, int | None]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT relname, pg_total_relation_size(oid) "
                    "FROM pg_class WHERE relname IN ('evaluation_records', 'evidence_records')"
                )
            ).all()
    finally:
        engine.dispose()
    sizes = {name: size for name, size in rows}
    return {name: sizes.get(name) for name in ("evaluation_records", "evidence_records")}


def _process_snapshot(api_pid: int | None) -> dict[str, int | float | None]:
    if api_pid is None:
        return {"cpu_user_seconds": None, "cpu_system_seconds": None, "rss_bytes": None}
    process = psutil.Process(api_pid)
    cpu = process.cpu_times()
    return {"cpu_user_seconds": cpu.user, "cpu_system_seconds": cpu.system, "rss_bytes": process.memory_info().rss}


def _simulator_request_count(mock_base_url: str) -> int:
    status, body = _request_json(f"{mock_base_url}/__metrics")
    if status != 200:
        raise RuntimeError(f"Local mock metrics failed with HTTP {status}.")
    return int(json.loads(body.decode("utf-8"))["repository_requests"])


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _percentile_95(values: list[float]) -> float | None:
    if len(values) < 2:
        return values[0] if values else None
    return quantiles(values, n=100, method="inclusive")[94]


def main() -> int:
    args = _parse_args()
    if args.evaluations_per_control < 1:
        raise ValueError("--evaluations-per-control must be at least 1.")
    api_base_url = _require_local_url(args.api_base_url, LOCAL_API, "API URL")
    mock_base_url = _require_local_url(args.mock_base_url, LOCAL_MOCK, "mock URL")
    database_url = _require_test_database_url()
    username = _read_secret_environment("SECURECODE_PERF_USERNAME")
    password = _read_secret_environment("SECURECODE_PERF_PASSWORD")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    token = _authenticate(api_base_url, username, password)
    before = {
        "database_bytes": _database_sizes(database_url),
        "process": _process_snapshot(args.api_pid),
        "mock_requests": _simulator_request_count(mock_base_url),
    }
    observations: list[Observation] = []
    for profile in PROFILES:
        for control in CONTROLS:
            endpoint = f"{api_base_url}/api/v1/evaluations/{control}"
            payload = {"owner": "Medalcode", "repository": "securecode", "branch": "main"}
            for sequence in range(1, args.evaluations_per_control + 1):
                started = time.perf_counter()
                try:
                    status, body = _request_json(endpoint, payload, token)
                    error = ""
                except RuntimeError as error_value:
                    status, body, error = 0, b"", str(error_value)
                observations.append(
                    Observation(
                        control=control,
                        profile=profile,
                        sequence=sequence,
                        status_code=status,
                        elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
                        response_bytes=len(body),
                        error=error,
                        captured_at_utc=datetime.now(UTC).isoformat(),
                    )
                )

    after = {
        "database_bytes": _database_sizes(database_url),
        "process": _process_snapshot(args.api_pid),
        "mock_requests": _simulator_request_count(mock_base_url),
    }
    csv_path = args.output_dir / "observations.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=Observation.__annotations__.keys())
        writer.writeheader()
        writer.writerows(asdict(observation) for observation in observations)
    summary = {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "commit": _git_commit(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "scope": {"controls": CONTROLS, "profiles": PROFILES, "evaluations_per_control": args.evaluations_per_control},
        "before": before,
        "after": after,
        "mock_request_delta": after["mock_requests"] - before["mock_requests"],
        "total_observations": len(observations),
        "successful_observations": sum(item.status_code == 200 for item in observations),
        "error_observations": sum(item.status_code != 200 for item in observations),
        "latency_p95_ms": _percentile_95([item.elapsed_ms for item in observations]),
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {csv_path} and {args.output_dir / 'summary.json'}")
    return 0 if summary["error_observations"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
