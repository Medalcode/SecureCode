import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from securecode.api.app import app

client = TestClient(app)

def test_get_test_bench_cases():
    resp = client.get("/api/v1/test-bench/cases")
    assert resp.status_code == 200
    data = resp.json()
    assert "cases" in data
    assert data["total"] >= 9
    assert "GH-001" in data["controls"]
    assert "GH-002" in data["controls"]

def test_get_test_bench_cases_filtered():
    resp = client.get("/api/v1/test-bench/cases?control=GH-001")
    assert resp.status_code == 200
    data = resp.json()
    for case in data["cases"]:
        assert case["control_id"] == "GH-001"

def test_run_test_bench_case_pass():
    resp = client.post("/api/v1/test-bench/run", json={
        "case_id": "GT-GH001-01"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "GT-GH001-01"
    assert data["expected_status"] == "PASS"
    assert data["actual_status"] == "PASS"
    assert data["matched"] is True
    assert data["execution_time_ms"] > 0
    assert len(data["integrity_hash"]) == 64

def test_run_test_bench_case_fail():
    resp = client.post("/api/v1/test-bench/run", json={
        "case_id": "GT-GH001-02"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["expected_status"] == "FAIL"
    assert data["actual_status"] == "FAIL"
    assert data["matched"] is True

def test_run_test_bench_case_unknown():
    resp = client.post("/api/v1/test-bench/run", json={
        "case_id": "GT-GH001-05"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["expected_status"] == "UNKNOWN"
    assert data["actual_status"] == "UNKNOWN"
    assert data["matched"] is True

def test_run_test_bench_case_not_found():
    resp = client.post("/api/v1/test-bench/run", json={
        "case_id": "GT-NON-EXISTENT"
    })
    assert resp.status_code == 404
