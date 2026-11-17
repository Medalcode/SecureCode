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


# Values written by SecureCode before ORG-001 introduced the explicit
# platform/customer vocabulary.  Keeping this narrow compatibility map at the
# domain boundary prevents legacy rows from crashing response validation while
# a database migration is being applied.  Unknown values are deliberately not
# coerced so data-integrity problems remain visible instead of granting access.
LEGACY_ROLE_ALIASES: Final = {
    "admin": PLATFORM_ADMIN,
    "auditor": ANALYST,
    "owner": ORGANIZATION_OWNER,
    "member": ANALYST,
}


def canonical_role(role: str | None) -> str | None:
    """Return the current role name for an explicit legacy alias."""
    if role is None:
        return None
    return LEGACY_ROLE_ALIASES.get(role, role)


def is_platform_admin(role: str | None) -> bool:
    return canonical_role(role) == PLATFORM_ADMIN


def is_organization_owner(role: str | None) -> bool:
    return canonical_role(role) == ORGANIZATION_OWNER
