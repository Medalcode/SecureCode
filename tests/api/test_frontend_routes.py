from pathlib import Path

from fastapi.testclient import TestClient

from securecode.api.app import app

client = TestClient(app)

def test_public_home_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert response.headers.get("cache-control") == "no-store, max-age=0"
    assert "/static/public/site.css?v=20261115-public-site" in response.text
    assert "Confianza técnica" in response.text
    assert 'href="/app"' in response.text
    assert '/static/public/securecode-mark.svg' in response.text
    assert "Borrador académico" not in response.text


def test_console_shell_remains_available_at_app_route():
    response = client.get("/app")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert response.headers.get("cache-control") == "no-store, max-age=0"
    assert 'href="/" class="brand-badge"' in response.text
    assert 'aria-label="Ir a la página de inicio de SecureCode"' in response.text
    assert "/static/css/app.css?v=20261111-admin-navigation-gate" in response.text
    assert "/static/js/app.js?v=20261118-management-report" in response.text
    assert "Enterprise Trial" in response.text
    assert "enterpriseTrialActivateForm" in response.text
    assert "SecureCode" in response.text
    assert "Evaluador de Controles" in response.text
    assert 'id="clientSettingsForm"' in response.text
    assert 'id="subscriptionConfirmPanel"' in response.text
    assert 'id="finopsPanel"' in response.text
    assert 'data-view="management-report" data-title="Informe de Gestión" hidden' in response.text
    assert 'id="managementReportPanel" hidden' in response.text
    assert 'id="btnDownloadManagementReport"' in response.text
    assert 'id="authErrorAlert"' not in response.text
    assert 'id="createUserForm"' in response.text
    assert 'id="newUserPasswordConfirm"' in response.text
    assert 'id="passwordResetModal"' in response.text
    assert 'id="newAdminAcknowledgement"' in response.text
    assert 'id="repositoryAuthorizationManagement"' in response.text
    assert 'id="repositoryAuthorizationForm"' in response.text
    assert 'data-view="admin" data-title="Consola de Administración" hidden' in response.text
    assert 'id="btnLogout" hidden' in response.text
    assert 'id="btnExportHistory" title="Exportar historial CSV" hidden' in response.text
    assert 'id="btnSubmitEval"' in response.text
    assert 'id="btnSubmitEval" disabled' not in response.text
    assert "Validación local verificada" in response.text


def test_public_information_and_legal_pages_are_available():
    for route in (
        "/nosotros",
        "/contacto",
        "/preguntas-frecuentes",
        "/legal/terminos",
        "/legal/privacidad",
        "/legal/cookies",
        "/legal/eula",
        "/legal/contratacion",
        "/legal/sla",
    ):
        response = client.get(route)
        assert response.status_code == 200
        assert '<meta name="viewport"' in response.text
        assert "SecureCode" in response.text
        if route.startswith("/legal/"):
            assert "Borrador académico" in response.text


def test_unknown_legal_page_returns_not_found():
    assert client.get("/legal/no-existe").status_code == 404


def test_public_site_has_responsive_stylesheet():
    stylesheet = Path("src/securecode/static/public/site.css").read_text(encoding="utf-8")
    assert "@media (max-width: 760px)" in stylesheet
    assert ".feature-grid, .content-grid, .contact-layout, .split-section, .public-footer" in stylesheet


def test_api_source_has_no_known_mojibake_markers():
    source = Path("src/securecode/api/app.py").read_text(encoding="utf-8")
    assert "Ã" not in source
    assert "Â" not in source


def test_admin_navigation_is_gated_by_the_server_validated_role():
    script = Path("src/securecode/static/js/app.js").read_text(encoding="utf-8")
    stylesheet = Path("src/securecode/static/css/app.css").read_text(encoding="utf-8")
    assert "function updateAdminAccess()" in script
    assert "return Boolean(state.token && state.accessRole === 'platform_admin');" in script
    assert "return Boolean(state.token && state.accessRole === 'organization_owner');" in script
    assert "const finopsNav = document.querySelector('.nav-item[data-view=\"usage\"]');" in script
    assert "const subscriptionNav = document.querySelector('.nav-item[data-view=\"subscription\"]');" in script
    assert "const settingsNav = document.querySelector('.nav-item[data-view=\"settings\"]');" in script
    assert "const managementReportNav = document.querySelector('.nav-item[data-view=\"management-report\"]');" in script
    assert "finopsNav.hidden = !ownerAllowed;" in script
    assert "subscriptionNav.hidden = !ownerAllowed;" in script
    assert "managementReportNav.hidden = !ownerAllowed;" in script
    assert "settingsNav.hidden = !authenticated;" in script
    assert "if (item.dataset.view === 'admin' && !isPlatformAdmin()) return;" in script
    assert "id=\"registrationForm\"" in Path("src/securecode/static/index.html").read_text(encoding="utf-8")
    assert "id=\"organizationPanel\"" in Path("src/securecode/static/index.html").read_text(encoding="utf-8")
    assert "function clearAuthenticatedSession()" in script
    assert "function resetVisitorEvaluationState()" in script
    assert "repoInput.value = '';" in script
    assert "setEvaluatorFeedback();" in script
    assert "state.organizationMembers = [];" in script
    assert "state.organizationAuthorizations = [];" in script
    assert "function updateHistoryAccess()" in script
    assert "function updateEvaluatorAccess()" in script
    assert "function loadManagementReport()" in script
    assert "'/api/v1/management-report'" in script
    assert "function downloadManagementReport()" in script
    assert """if (!state.token) {
        setEvaluatorFeedback('Inicia sesión para ejecutar una evaluación y guardar su evidencia.', 'neutral');
        openAuthModal();
        return;
      }""" in script
    assert """btnSubmit?.addEventListener('click', (event) => {
      if (state.token) return;
      event.preventDefault();
      setEvaluatorFeedback('Inicia sesión para ejecutar una evaluación y guardar su evidencia.', 'neutral');
      openAuthModal();
    });""" in script
    assert "localStorage.removeItem('securecode_history');" in script
    assert "['undefined', 'null'].includes(repoInput.value.trim().toLowerCase())" in script
    assert "function normalizeOptionalRepository(value)" in script
    assert "const defaultRepository = normalizeOptionalRepository(settings.default_repository);" in script
    assert ".nav-item[hidden]" in stylesheet
    assert "display: none !important;" in stylesheet

def test_analyst_password_reset_modal_replaces_prompt():
    """El restablecimiento usa un modal accesible, nunca window.prompt()."""
    script = Path("src/securecode/static/js/app.js").read_text(encoding="utf-8")
    html = Path("src/securecode/static/index.html").read_text(encoding="utf-8")
    assert "prompt(" not in script
    assert 'id="passwordResetModal"' in html
    assert 'id="passwordResetStrategyGroup"' in html
    assert 'id="resetStrategyGenerate"' in html
    assert 'id="resetStrategyDefined"' in html
    assert 'name="resetPasswordStrategy"' in html
    assert 'id="passwordResetPasswordFieldGroup"' in html
    assert 'id="passwordResetGenerateNote"' in html
    assert "Generar contraseña segura" in html
    assert "Definir contraseña" in html
    assert "El sistema crea una y la muestra una sola vez" in html
    assert "Se muestra una sola vez. Entrégala por un canal seguro." in html
    assert "function updatePasswordResetVisibility()" in script
    assert "const generateTemp = target.scope === 'organization'" in script
    assert ("const payload = generateTemp\n"
            "        ? { generate_temp: true }\n"
            "        : { password: document.getElementById('resetUserPassword').value };") in script
    assert "openOrganizationPasswordPanel(target.username, tempPassword)" in script
    assert 'id="orgPasswordCopyBtn"' in html


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
