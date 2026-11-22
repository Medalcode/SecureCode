import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.api.normative_transparency import (
    CONTROL_METADATA,
    SCOPE_WARNING,
    format_condition,
    load_canonical_rules,
)
from securecode.engine.evaluator import (
    evaluate_gh001,
    evaluate_gh002,
    evaluate_gh003,
    get_rules_directory,
)
from securecode.engine.types import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.models.rules import RuleDefinition

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[2]
STYLESHEET = REPO_ROOT / "src" / "securecode" / "static" / "public" / "site.css"
PHASE_ONE_DOCS = (
    REPO_ROOT / "docs" / "compliance" / "NIST-800-53-TRACEABILITY.md",
    REPO_ROOT / "docs" / "compliance" / "CONTROL-FICHES.md",
)


@pytest.fixture
def private_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_db_session, None)


def test_public_transparency_routes_are_available_without_authentication():
    for route in ("/", "/controles", "/alcance"):
        response = client.get(route)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert response.headers.get("cache-control") == "no-store, max-age=0"
        assert '<meta name="color-scheme" content="light dark">' in response.text
        assert 'href="/static/public/site.css?v=20261120-normative-transparency"' in response.text
        assert 'class="skip-link"' in response.text
        assert '<nav class="public-nav" aria-label="Navegación principal">' in response.text
        assert '<main id="contenido">' in response.text


def test_home_communicates_framework_and_no_certification():
    home = client.get("/").text
    assert "Seguridad verificable para repositorios GitHub" in home
    assert "SecureCode evalúa automáticamente configuraciones técnicas de seguridad en repositorios GitHub mediante controles específicos alineados con objetivos seleccionados de NIST SP 800-53 Rev. 5." in home
    assert "Nuestro marco de referencia" in home
    assert "NIST SP 800-53 Rev. 5 es el marco de referencia principal" in home
    assert "NIST SP 800-53A Rev. 5 orienta metodológicamente la evaluación" in home
    assert "no representan una certificación ni una evaluación integral de NIST" in home
    assert "Metodología de evaluación" in home


def test_public_controls_match_canonical_rules():
    controls = client.get("/controles").text
    rules = load_canonical_rules()
    assert set(rules) == set(CONTROL_METADATA)

    for control_id, definition in rules.items():
        condition = format_condition(definition.condition)
        assert control_id in controls
        assert str(definition.rule_id) in controls
        assert f"Regla v{definition.version}" in controls
        assert condition in controls
        assert CONTROL_METADATA[control_id]["name"] in controls
        assert CONTROL_METADATA[control_id]["limitations"] in controls

        raw_path = get_rules_directory() / f"{control_id}.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        raw_definition = RuleDefinition(**raw)
        assert format_condition(raw_definition.condition) == condition
        for document in PHASE_ONE_DOCS:
            if document.exists():
                assert condition in document.read_text(encoding="utf-8")


def test_nist_alignment_is_explicitly_partial():
    home = client.get("/").text
    controls = client.get("/controles").text
    scope = client.get("/alcance").text
    combined = (home + controls + scope).lower()
    assert "correspondencia parcial" in combined
    assert "no equivale a FAIL" in home + controls
    assert "no certifica" in combined
    assert "no sustituye" in combined
    assert "umbral de dos aprobaciones es política de securecode" in combined


def test_status_meanings_are_visible_and_unknown_is_not_fail():
    controls = client.get("/controles").text
    assert "La evidencia disponible demuestra que se cumplen las condiciones de la regla evaluada." in controls
    assert "La evidencia disponible demuestra el incumplimiento de al menos una condición determinante de la regla." in controls
    assert "La evidencia disponible no permite establecer el resultado." in controls
    assert "UNKNOWN no equivale a FAIL" in controls
    assert "PASS no significa que un repositorio esté completamente seguro" in controls


def test_scope_and_exclusions_are_visible_before_contracting():
    home = client.get("/").text
    scope = client.get("/alcance").text
    assert SCOPE_WARNING in home
    assert SCOPE_WARNING in scope
    assert "Qué hace SecureCode y qué no hace" in home
    assert "antes de cualquier acción de contratación o suscripción" in scope
    assert "/legal/contratacion" in scope
    assert "Auditoría integral de ciberseguridad" in scope


def test_public_stylesheet_supports_dark_theme_mobile_and_keyboard():
    stylesheet = STYLESHEET.read_text(encoding="utf-8")
    assert "@media (prefers-color-scheme: dark)" in stylesheet
    assert "@media (max-width: 760px)" in stylesheet
    assert "a:focus-visible" in stylesheet
    assert ".control-grid" in stylesheet
    assert ".scope-grid" in stylesheet


def test_private_apis_remain_protected(private_client):
    for route in (
        "/api/v1/system/overview",
        "/api/v1/admin/users",
        "/api/v1/evaluations/history",
        "/api/v1/evaluations/00000000-0000-0000-0000-000000000000/report.pdf",
        "/api/v1/settings",
        "/api/v1/auth/me",
        "/api/v1/management-report",
        "/api/v1/enterprise-trial",
    ):
        assert private_client.get(route).status_code == 401


def test_login_register_and_console_remain_available(private_client):
    assert private_client.get("/app").status_code == 200
    assert private_client.post("/api/v1/auth/token", json={}).status_code == 422
    assert private_client.post("/api/v1/auth/register", json={}).status_code == 422


def test_gh_evaluations_have_no_regression():
    assert evaluate_gh001(GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)) == EvaluationStatus.PASS
    assert evaluate_gh002(GH002Evidence(default_branch="main", protection_enabled=True)) == EvaluationStatus.PASS
    assert evaluate_gh003(GH003Evidence(branch="main", required_signatures_enabled=True)) == EvaluationStatus.PASS
