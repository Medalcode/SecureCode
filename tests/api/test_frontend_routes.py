from fastapi.testclient import TestClient
from securecode.api.app import app

client = TestClient(app)

def test_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "SecureCode" in response.text
    assert "Evaluador de Controles" in response.text

def test_rules_catalog_endpoint():
    response = client.get("/api/v1/rules")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert isinstance(data["rules"], list)
    rule_ids = [r.get("control_id") for r in data["rules"]]
    assert "GH-001" in rule_ids
    assert "GH-002" in rule_ids

def test_system_overview_endpoint():
    response = client.get("/api/v1/system/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["ci_metrics"]["tests_passing"] == 95
    assert data["ci_metrics"]["coverage_pct"] == 89.5
    assert "performance" in data
    assert data["performance"]["p95_latency_ms"] == 200
