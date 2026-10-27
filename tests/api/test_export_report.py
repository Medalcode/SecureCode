import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["JWT_ALGORITHM"] = "HS256"

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from securecode.api.app import app
from securecode.api.dependencies import get_current_user
from securecode.api.security import create_access_token, hash_password
from securecode.application.pdf_generator import generate_audit_report_pdf

class DummyUser:
    def __init__(self, id, username, password_hash, active):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.active = active

mock_user_id = uuid4()
mock_user = DummyUser(
    id=mock_user_id,
    username="auditor@empresa.com",
    password_hash=hash_password("Password123!"),
    active=True
)

def test_export_report_pdf_generator_pure():
    pdf = generate_audit_report_pdf(
        control="GH-001 Revisión por pares",
        repository="acme-corp/payment-gateway (main)",
        verdict="PASS (CONFORME)",
        integrity_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        evaluation_id="eval_9f8a2b3c",
        auditor="auditor@empresa.com"
    )
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-1.4")
    assert b"SECURECODE" in pdf
    assert b"INACAP" in pdf

def test_export_report_endpoint_unauthorized():
    app.dependency_overrides.clear()
    client = TestClient(app)
    resp = client.post("/api/v1/evaluations/export", json={
        "evaluated_control": "GH-001",
        "repository": "acme/repo",
        "verdict": "PASS",
        "integrity_hash": "e3b0c442",
        "email": "auditor@empresa.com"
    })
    assert resp.status_code == 401

def test_export_report_endpoint_authorized():
    client = TestClient(app)
    token = create_access_token(str(mock_user_id))

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        resp = client.post(
            "/api/v1/evaluations/export",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "evaluation_id": "eval_9f8a2b3c",
                "evaluated_control": "GH-001 Revisión por pares",
                "repository": "acme-corp/payment-gateway (main)",
                "verdict": "PASS (CONFORME)",
                "integrity_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "generate_pdf": True,
                "email": "auditor@empresa.com"
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["title"] == "EXPORTAR REPORTE DE AUDITORÍA"
        assert "auditor@empresa.com" in data["message"]
        assert data["dispatch_id"].startswith("DSP-")
        assert len(data["integrity_signature"]) == 64
    finally:
        app.dependency_overrides.clear()

def test_download_pdf_endpoint():
    client = TestClient(app)
    resp = client.get(
        "/api/v1/evaluations/pdf?control=GH-001&repository=acme-corp/payment-gateway&verdict=PASS&integrity_hash=e3b0c442&evaluation_id=eval_9f8a2b3c"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-1.4")

