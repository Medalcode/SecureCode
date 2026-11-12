"""Tests for the local-only performance measurement protocol."""

import json
from types import SimpleNamespace

import pytest

from scripts import measure_local_performance as measurement


def test_fixed_local_urls_reject_remote_targets():
    with pytest.raises(ValueError, match="fixed local endpoint"):
        measurement._require_local_url("https://example.invalid", measurement.LOCAL_API, "API URL")


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg2://user:pass@db.example.com:5432/securecode_test",
        "postgresql+psycopg2://user:pass@127.0.0.1:5432/securecode",
        "postgresql+psycopg2://user:pass@127.0.0.1:6543/securecode_test",
    ],
)
def test_database_guard_rejects_nonlocal_or_non_test_databases(monkeypatch, database_url):
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(ValueError, match="local PostgreSQL|securecode_test"):
        measurement._require_test_database_url()


def test_measurement_writes_observations_and_summary_without_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@127.0.0.1:5432/securecode_test")
    monkeypatch.setenv("SECURECODE_PERF_USERNAME", "test-user")
    monkeypatch.setenv("SECURECODE_PERF_PASSWORD", "test-password")
    monkeypatch.setattr(
        measurement,
        "_parse_args",
        lambda: SimpleNamespace(
            output_dir=tmp_path,
            evaluations_per_control=1,
            api_pid=None,
            api_base_url=measurement.LOCAL_API,
            mock_base_url=measurement.LOCAL_MOCK,
        ),
    )
    monkeypatch.setattr(measurement, "_authenticate", lambda *args: "opaque-token")
    monkeypatch.setattr(
        measurement,
        "_database_sizes",
        lambda *args: {"evaluation_records": 10, "evidence_records": 20},
    )
    monkeypatch.setattr(measurement, "_process_snapshot", lambda *args: {"rss_bytes": None})
    request_counts = iter([4, 22])
    monkeypatch.setattr(measurement, "_simulator_request_count", lambda *args: next(request_counts))
    monkeypatch.setattr(measurement, "_request_json", lambda *args, **kwargs: (200, b"{}"))
    monkeypatch.setattr(measurement, "_git_commit", lambda: "test-commit")

    assert measurement.main() == 0

    observations = (tmp_path / "observations.csv").read_text(encoding="utf-8").splitlines()
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert len(observations) == 10
    assert summary["total_observations"] == 9
    assert summary["successful_observations"] == 9
    assert summary["mock_request_delta"] == 18
    assert "test-password" not in (tmp_path / "summary.json").read_text(encoding="utf-8")
