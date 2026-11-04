from fastapi.testclient import TestClient

from securecode.api.app import app


def test_security_headers_are_present_on_public_routes():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
