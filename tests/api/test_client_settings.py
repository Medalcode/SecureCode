from uuid import uuid4

import pytest
from fastapi import HTTPException

from securecode.adapters.postgres.models import UserAuditEvent, UserSettings
from securecode.api.app import (
    ClientSettingsUpdateRequest,
    get_client_settings,
    update_client_settings,
)


class UserStub:
    def __init__(self):
        self.id = uuid4()
        self.username = "auditor@example.com"


class QueryStub:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *_):
        return self

    def first(self):
        return self.result


class SessionStub:
    def __init__(self, result=None):
        self.query_stub = QueryStub(result)
        self.added = []
        self.commits = 0

    def query(self, *_):
        return self.query_stub

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def refresh(self, _):
        return None


def test_get_settings_returns_safe_defaults_before_first_save():
    response = get_client_settings(SessionStub(), UserStub())

    assert response["default_branch"] == "main"
    assert response["timezone"] == "America/Santiago"
    assert response["default_repository"] is None


def test_user_can_persist_own_safe_client_settings_with_audit_event():
    user = UserStub()
    session = SessionStub()

    response = update_client_settings(
        ClientSettingsUpdateRequest(
            default_repository="Medalcode/securecode-ground-truth",
            default_branch="main",
            locale="es-CL",
            timezone="America/Santiago",
            theme="dark",
            notify_evaluation_completed=True,
            notify_evaluation_failure=True,
            notify_weekly_digest=False,
        ),
        session,
        user,
    )

    assert response["default_repository"] == "Medalcode/securecode-ground-truth"
    assert response["theme"] == "dark"
    assert any(isinstance(item, UserSettings) for item in session.added)
    audit = next(item for item in session.added if isinstance(item, UserAuditEvent))
    assert audit.action == "client_settings_updated"
    assert "password" not in audit.details
    assert session.commits == 1


def test_settings_reject_invalid_repository_and_empty_update():
    user = UserStub()
    with pytest.raises(HTTPException) as invalid_repo:
        update_client_settings(
            ClientSettingsUpdateRequest(default_repository="https://github.com/owner/repo"),
            SessionStub(),
            user,
        )
    assert invalid_repo.value.status_code == 422

    with pytest.raises(HTTPException) as empty_update:
        update_client_settings(ClientSettingsUpdateRequest(), SessionStub(), user)
    assert empty_update.value.status_code == 422
