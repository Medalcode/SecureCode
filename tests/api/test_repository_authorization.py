from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from securecode.api.app import _normalise_repository, _require_repository_authorization


class QueryStub:
    def __init__(self, result):
        self.result = result

    def filter(self, *_):
        return self

    def join(self, *_):
        return self

    def order_by(self, *_):
        return self

    def first(self):
        return self.result


class SessionStub:
    def __init__(self, authorization):
        self.authorization = authorization

    def query(self, *_):
        return QueryStub(self.authorization)


def test_auditor_is_denied_without_an_active_repository_authorization():
    auditor = SimpleNamespace(id=uuid4(), role="auditor")

    with pytest.raises(HTTPException) as exc_info:
        _require_repository_authorization(SessionStub(None), auditor, "Medalcode", "securecode-ground-truth")

    assert exc_info.value.status_code == 403


def test_auditor_can_evaluate_an_explicitly_authorized_repository():
    auditor = SimpleNamespace(id=uuid4(), role="auditor")
    authorization = SimpleNamespace(active=True)

    _require_repository_authorization(SessionStub(authorization), auditor, "Medalcode", "securecode-ground-truth")


def test_administrator_bypasses_per_account_scope_for_platform_operations():
    administrator = SimpleNamespace(id=uuid4(), role="admin")

    _require_repository_authorization(SessionStub(None), administrator, "Medalcode", "securecode-ground-truth")


def test_repository_scope_is_case_insensitive_like_github_identity():
    assert _normalise_repository("  Medalcode/SecureCode-Ground-Truth  ") == "medalcode/securecode-ground-truth"


@pytest.mark.parametrize("value", ["owner", "owner/repo/path", "owner /repo", "owner/../repo"])
def test_repository_scope_requires_canonical_owner_repo_format(value):
    with pytest.raises(HTTPException) as exc_info:
        _normalise_repository(value)

    assert exc_info.value.status_code == 422
