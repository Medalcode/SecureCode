"""Authoritative role vocabulary for the SecureCode B2B boundary.

The platform deliberately keeps this list small.  A platform operator is not a
customer administrator: client authority is represented by a membership in one
organization.
"""

from typing import Final

PLATFORM_ADMIN: Final = "platform_admin"
ORGANIZATION_OWNER: Final = "organization_owner"
ANALYST: Final = "analyst"

USER_ROLES: Final = frozenset({PLATFORM_ADMIN, ORGANIZATION_OWNER, ANALYST})
CUSTOMER_ROLES: Final = frozenset({ORGANIZATION_OWNER, ANALYST})

ROLE_LABELS: Final = {
    PLATFORM_ADMIN: "Administrador de plataforma",
    ORGANIZATION_OWNER: "Propietario de organización",
    ANALYST: "Auditor de seguridad",
}


def is_platform_admin(role: str | None) -> bool:
    return role == PLATFORM_ADMIN


def is_organization_owner(role: str | None) -> bool:
    return role == ORGANIZATION_OWNER
