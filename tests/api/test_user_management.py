from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from securecode.api.app import (
    UserCreateRequest,
    UserUpdateRequest,
    create_user,
    list_users,
    update_user,
)
from securecode.api.security import verify_password
from securecode.adapters.postgres.models import UserAuditEvent


class UserStub:
    def __init__(self, username="platform@example.com", role="platform_admin", active=True):
        self.id = uuid4()
        self.username = username
        self.role = role
        self.active = active
        self.password_hash = ""
        self.created_at = datetime.now(timezone.utc)


class QueryStub:
    def __init__(self, first_result=None, all_results=None, count_value=2):
        self.first_result = first_result
        self.all_results = all_results or []
        self.count_value = count_value

    def filter(self, *_):
        return self

    def first(self):
        return self.first_result

    def order_by(self, *_):
        return self

    def all(self):
        return self.all_results

    def count(self):
        return self.count_value


class SessionStub:
    def __init__(self, first_result=None, all_results=None, count_value=2):
        self.query_stub = QueryStub(first_result, all_results, count_value)
        self.added = []
        self.commits = 0

    def query(self, *_):
        return self.query_stub

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def refresh(self, _):
        return None


def test_platform_admin_can_create_a_normalized_platform_user_with_hashed_password():
    session = SessionStub()
    created = create_user(
        UserCreateRequest(username="  Operator.Nuevo@Example.com ", password="PasswordTemporal#2026", role="platform_admin"),
        session,
        UserStub(role="platform_admin"),
    )

    stored_user = session.added[0]
    assert created["username"] == "operator.nuevo@example.com"
    assert created["role"] == "platform_admin"
    assert stored_user.password_hash != "PasswordTemporal#2026"
    assert verify_password("PasswordTemporal#2026", stored_user.password_hash)
    assert isinstance(session.added[1], UserAuditEvent)
    assert session.added[1].action == "account_created"
    assert "password" not in session.added[1].details
    assert session.commits == 1


def test_duplicate_username_is_rejected():
    session = SessionStub(first_result=UserStub())

    with pytest.raises(HTTPException) as exc_info:
        create_user(
            UserCreateRequest(username="operator@example.com", password="PasswordTemporal#2026"),
            session,
            UserStub(role="platform_admin"),
        )

    assert exc_info.value.status_code == 409


def test_weak_password_is_rejected_before_persistence():
    session = SessionStub()

    with pytest.raises(HTTPException) as exc_info:
        create_user(
            UserCreateRequest(username="operator@example.com", password="onlylowercase12"),
            session,
            UserStub(role="platform_admin"),
        )

    assert exc_info.value.status_code == 422
    assert session.added == []


def test_admin_can_read_and_update_user_state():
    managed_user = UserStub()
    session = SessionStub(first_result=managed_user, all_results=[managed_user])
    admin = UserStub(username="admin@example.com", role="platform_admin")

    listed = list_users(session, admin)
    updated = update_user(str(managed_user.id), UserUpdateRequest(active=False, role="platform_admin"), session, admin)

    assert listed[0]["username"] == "platform@example.com"
    assert updated["active"] is False
    assert updated["role"] == "platform_admin"
    assert session.commits == 1


def test_administrator_cannot_remove_own_access():
    admin = UserStub(username="admin@example.com", role="platform_admin")
    session = SessionStub(first_result=admin)

    with pytest.raises(HTTPException) as exc_info:
        update_user(str(admin.id), UserUpdateRequest(active=False), session, admin)

    assert exc_info.value.status_code == 400


def test_last_active_administrator_cannot_be_deactivated_by_another_admin():
    only_admin = UserStub(username="only-admin@example.com", role="platform_admin")
    session = SessionStub(first_result=only_admin, count_value=1)
    actor = UserStub(username="actor@example.com", role="platform_admin")

    with pytest.raises(HTTPException) as exc_info:
        update_user(str(only_admin.id), UserUpdateRequest(active=False), session, actor)

    assert exc_info.value.status_code == 400
