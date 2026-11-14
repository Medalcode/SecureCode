import pytest
from fastapi import HTTPException

from securecode.api.dependencies import require_platform_admin


class UserStub:
    def __init__(self, role):
        self.role = role


def test_require_platform_admin_accepts_platform_administrator():
    admin = UserStub("platform_admin")
    assert require_platform_admin(admin) is admin


def test_require_platform_admin_rejects_analyst():
    with pytest.raises(HTTPException) as exc_info:
        require_platform_admin(UserStub("analyst"))
    assert exc_info.value.status_code == 403
