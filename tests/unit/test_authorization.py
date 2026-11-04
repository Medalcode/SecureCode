import pytest
from fastapi import HTTPException

from securecode.api.dependencies import require_admin


class UserStub:
    def __init__(self, role):
        self.role = role


def test_require_admin_accepts_administrator():
    admin = UserStub("admin")
    assert require_admin(admin) is admin


def test_require_admin_rejects_auditor():
    with pytest.raises(HTTPException) as exc_info:
        require_admin(UserStub("auditor"))
    assert exc_info.value.status_code == 403
