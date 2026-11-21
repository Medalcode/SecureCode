import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import (
    Base,
    Organization,
    ServiceDocumentAcceptance,
    User,
)
from securecode.api import app as app_module
from securecode.api import service_document_manifest as manifest_module
from securecode.api import service_documents as service_documents_module
from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.api.service_document_manifest import (
    EXPECTED_MANIFEST_SHA256,
    MANIFEST_PATH,
    load_document_manifest,
    manifest_sha256,
)
from securecode.api.service_documents import (
    ACCEPTANCE_TYPE,
    PACKAGE_ID,
    PACKAGE_VERSION,
    OnboardingPackage,
    current_onboarding_package,
)


@pytest.fixture
def client_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def _registration_payload(organization: str, username: str, **overrides) -> dict:
    payload = {
        "organization_name": organization,
        "username": username,
        "password": "OwnerPassword#2026",
        "password_confirmation": "OwnerPassword#2026",
        "accepted_document_package_id": PACKAGE_ID,
        "accepted_document_package_version": PACKAGE_VERSION,
        "accepted_document_package_sha256": current_onboarding_package().sha256,
        "acceptance_confirmed": True,
    }
    payload.update(overrides)
    return payload


def test_document_package_is_versioned_and_hashable():
    package = current_onboarding_package()
    assert package.package_id == PACKAGE_ID
    assert package.version == PACKAGE_VERSION
    assert [document.document_id for document in package.documents] == ["SERVICE_TERMS", "TECHNICAL_SCOPE"]
    assert all(len(document.sha256) == 64 for document in package.documents)
    assert len(package.sha256) == 64
    assert package.as_dict() == current_onboarding_package().as_dict()


def test_current_package_and_console_contract_are_public(client_session):
    client, _ = client_session
    package = current_onboarding_package()
    response = client.get("/api/v1/service-documents/current")
    assert response.status_code == 200
    assert response.json() == package.as_dict()

    html = client.get("/app").text
    assert 'id="registrationAcceptance"' in html
    assert 'id="registrationAcceptance" required' in html
    assert "<a href=\"/legal/terminos\"" in html
    assert "<a href=\"/alcance\"" in html
    assert PACKAGE_VERSION in html
    assert "Borrador académico" not in html or "revisión jurídica" in html

    script = (Path(__file__).resolve().parents[2] / "src/securecode/static/js/app.js").read_text(encoding="utf-8")
    assert "fetch('/api/v1/service-documents/current')" in script
    assert "accepted_document_package_id: serviceDocumentPackage.package_id" in script
    assert "accepted_document_package_version: serviceDocumentPackage.version" in script
    assert "accepted_document_package_sha256: serviceDocumentPackage.sha256" in script
    assert "acceptance_confirmed: Boolean(acceptance?.checked)" in script


def test_registration_requires_explicit_acceptance(client_session):
    client, session = client_session
    payload = _registration_payload("Acceptance Required", "owner@required.test")
    payload.pop("acceptance_confirmed")
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert session.query(ServiceDocumentAcceptance).count() == 0
    assert session.query(User).count() == 0
    assert session.query(Organization).count() == 0


def test_registration_rejects_tampered_package_identity_and_digest(client_session):
    client, session = client_session
    for field, value in (
        ("accepted_document_package_id", "OTHER-PACKAGE"),
        ("accepted_document_package_version", "1999-01-01.1"),
        ("accepted_document_package_sha256", "0" * 64),
    ):
        response = client.post("/api/v1/auth/register", json=_registration_payload(
            f"Tampered {field}", f"owner-{field.lower()}@test.example", **{field: value}
        ))
        assert response.status_code == 422
    assert session.query(ServiceDocumentAcceptance).count() == 0
    assert session.query(User).count() == 0


def test_registration_records_verifiable_acceptance_history(client_session):
    client, session = client_session
    package = current_onboarding_package()
    response = client.post("/api/v1/auth/register", json=_registration_payload("Auditable Org", "owner@audit.test"))
    assert response.status_code == 201

    records = session.query(ServiceDocumentAcceptance).order_by(ServiceDocumentAcceptance.document_id.asc()).all()
    assert len(records) == len(package.documents)
    assert [record.document_id for record in records] == ["SERVICE_TERMS", "TECHNICAL_SCOPE"]
    assert all(str(record.organization_id) == response.json()["organization_id"] for record in records)
    assert all(record.user_id is not None for record in records)
    assert all(record.package_id == PACKAGE_ID for record in records)
    assert all(record.package_version == PACKAGE_VERSION for record in records)
    assert all(record.acceptance_type == ACCEPTANCE_TYPE for record in records)
    utc_now = datetime.now(UTC)
    assert all(abs((utc_now - record.accepted_at.replace(tzinfo=UTC)).total_seconds()) < 60 for record in records)
    assert [record.document_sha256 for record in records] == [document.sha256 for document in package.documents]
    assert all(record.package_sha256 == package.sha256 for record in records)

    token = client.post("/api/v1/auth/token", data={
        "username": "owner@audit.test", "password": "OwnerPassword#2026",
    }).json()["access_token"]
    history = client.get("/api/v1/organization/service-acceptances", headers={"Authorization": f"Bearer {token}"})
    assert history.status_code == 200
    assert {item["document_id"] for item in history.json()} == {"SERVICE_TERMS", "TECHNICAL_SCOPE"}
    assert all(item["organization_id"] == response.json()["organization_id"] for item in history.json())


def test_acceptance_history_is_owner_only_and_tenant_isolated(client_session):
    client, _ = client_session
    first = client.post("/api/v1/auth/register", json=_registration_payload("First Org", "owner@first.test"))
    second = client.post("/api/v1/auth/register", json=_registration_payload("Second Org", "owner@second.test"))
    assert first.status_code == second.status_code == 201

    def _token(username: str, password: str = "OwnerPassword#2026") -> str:
        return client.post("/api/v1/auth/token", data={
            "username": username, "password": password,
        }).json()["access_token"]

    first_headers = {"Authorization": f"Bearer {_token('owner@first.test')}"}
    second_headers = {"Authorization": f"Bearer {_token('owner@second.test')}"}
    first_history = client.get("/api/v1/organization/service-acceptances", headers=first_headers)
    second_history = client.get("/api/v1/organization/service-acceptances", headers=second_headers)
    assert first_history.status_code == second_history.status_code == 200
    assert {item["organization_id"] for item in first_history.json()} == {first.json()["organization_id"]}
    assert {item["organization_id"] for item in second_history.json()} == {second.json()["organization_id"]}

    analyst = client.post("/api/v1/organization/members", headers=first_headers, json={
        "username": "analyst@first.test", "password": "AnalystPassword#2026",
    })
    assert analyst.status_code == 201
    analyst_headers = {"Authorization": f"Bearer {_token('analyst@first.test', 'AnalystPassword#2026')}"}
    assert client.get("/api/v1/organization/service-acceptances", headers=analyst_headers).status_code == 403
    assert client.post("/api/v1/organization/service-acceptances", headers=analyst_headers, json={
        "acceptance_confirmed": True,
    }).status_code == 405
    assert client.patch("/api/v1/organization/service-acceptances", headers=first_headers, json={
        "acceptance_confirmed": False,
    }).status_code == 405
    assert client.delete("/api/v1/organization/service-acceptances", headers=first_headers).status_code == 405
    assert client.get("/api/v1/organization/service-acceptances").status_code == 401


def test_new_document_version_is_rejected_without_invalidating_existing_session(client_session, monkeypatch):
    client, session = client_session
    registered = client.post("/api/v1/auth/register", json=_registration_payload("Stable Org", "owner@stable.test"))
    assert registered.status_code == 201
    current = current_onboarding_package()
    future = OnboardingPackage(PACKAGE_ID, "2099-01-01.1", current.documents)
    monkeypatch.setattr(app_module, "current_onboarding_package", lambda: future)

    token = client.post("/api/v1/auth/token", data={
        "username": "owner@stable.test", "password": "OwnerPassword#2026",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/api/v1/organization/service-acceptances", headers=headers).status_code == 200

    rejected = client.post("/api/v1/auth/register", json=_registration_payload(
        "Future Org", "owner@future.test",
        accepted_document_package_version=PACKAGE_VERSION,
    ))
    assert rejected.status_code == 422
    assert session.query(ServiceDocumentAcceptance).count() == len(current.documents)
    assert all(record.package_version == PACKAGE_VERSION for record in session.query(ServiceDocumentAcceptance).all())


def test_service_document_manifest_hash_matches_trusted_reference():
    manifest = load_document_manifest()
    assert manifest["package_id"] == PACKAGE_ID
    assert manifest["version"] == PACKAGE_VERSION
    assert manifest["sha256"] == current_onboarding_package().sha256
    assert manifest_sha256(manifest) == EXPECTED_MANIFEST_SHA256


def test_document_content_alteration_is_detected(monkeypatch):
    title, body = service_documents_module.LEGAL_CONTENT["terminos"]
    monkeypatch.setitem(
        service_documents_module.LEGAL_CONTENT,
        "terminos",
        (title, body.replace("académica", "alterada")),
    )
    with pytest.raises(RuntimeError, match="trusted manifest"):
        current_onboarding_package()


def test_manifest_alteration_is_detected(tmp_path, monkeypatch):
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["version"] = "2099-01-01.1"
    altered = tmp_path / "altered.manifest.json"
    altered.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(manifest_module, "MANIFEST_PATH", altered)
    with pytest.raises(RuntimeError, match="trusted reference"):
        load_document_manifest()
