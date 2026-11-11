from pathlib import Path

from fastapi.testclient import TestClient
from securecode.api.app import app

client = TestClient(app)

def test_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert response.headers.get("cache-control") == "no-store, max-age=0"
    assert "/static/css/app.css?v=20261111-admin-navigation-gate" in response.text
    assert "SecureCode" in response.text
    assert "Evaluador de Controles" in response.text
    assert 'id="clientSettingsForm"' in response.text
    assert 'id="subscriptionConfirmPanel"' in response.text
    assert 'id="finopsPanel"' in response.text
    assert 'id="authErrorAlert"' not in response.text
    assert 'id="createUserForm"' in response.text
    assert 'id="newUserPasswordConfirm"' in response.text
    assert 'id="passwordResetModal"' in response.text
    assert 'id="newAdminAcknowledgement"' in response.text
    assert 'id="repositoryAuthorizationManagement"' in response.text
    assert 'id="repositoryAuthorizationForm"' in response.text
    assert 'data-view="admin" data-title="Consola de Administración" hidden' in response.text
    assert "Validación local verificada" in response.text


def test_admin_navigation_is_gated_by_the_server_validated_role():
    script = Path("src/securecode/static/js/app.js").read_text(encoding="utf-8")
    stylesheet = Path("src/securecode/static/css/app.css").read_text(encoding="utf-8")
    assert "function updateAdminAccess()" in script
    assert "return Boolean(state.token && state.accessRole === 'admin');" in script
    assert "if (item.dataset.view === 'admin' && !isAdministrator()) return;" in script
    assert ".nav-item[hidden]" in stylesheet
    assert "display: none !important;" in stylesheet

def test_rules_catalog_endpoint():
    response = client.get("/api/v1/rules")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert isinstance(data["rules"], list)
    rule_ids = [r.get("control_id") for r in data["rules"]]
    assert "GH-001" in rule_ids
    assert "GH-002" in rule_ids
    assert "GH-003" in rule_ids
    assert data["active_controls"] == len(data["rules"])
    assert data["catalog_version"] == "1"

def test_system_overview_endpoint():
    response = client.get("/api/v1/system/overview")
    assert response.status_code == 401
