"""reconcile rc001 email auth objects missing from historical head drift

Revision ID: ab12cd34ef56
Revises: d4e9f1a2b3c4
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "ab12cd34ef56"
down_revision: str | Sequence[str] | None = "d4e9f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USERS_TABLE = "users"
TOKENS_TABLE = "account_action_tokens"
TOKEN_HASH_UQ = "uq_account_action_token_hash"
TOKEN_USER_PURPOSE_IX = "ix_account_action_tokens_user_purpose"
TOKEN_USER_FK = "account_action_tokens_user_id_fkey"
EXPECTED_TOKEN_COLUMNS = {
    "id": {"nullable": False},
    "user_id": {"nullable": False},
    "purpose": {"nullable": False},
    "token_hash": {"nullable": False},
    "expires_at": {"nullable": False},
    "used_at": {"nullable": True},
    "created_at": {"nullable": False},
}


def _is_datetime_type(type_: object) -> bool:
    return isinstance(type_, sa.DateTime)


def _is_uuid_type(type_: object, dialect_name: str | None = None) -> bool:
    if isinstance(type_, sa.Uuid):
        return True
    name = type_.__class__.__name__.lower()
    if name == "uuid":
        return True
    # SQLite commonly stores SQLAlchemy UUID as CHAR(32) or BLOB/BINARY(16).
    if dialect_name == "sqlite":
        if isinstance(type_, sa.String) and getattr(type_, "length", None) in (32, 36):
            return True
        if isinstance(type_, (sa.LargeBinary, sa.BINARY)) and getattr(type_, "length", None) in (16, None):
            return True
        if name in {"char", "varchar", "binary", "largebinary", "blob"}:
            return True
    return False


def _is_string_type(type_: object, length: int | None = None) -> bool:
    if not isinstance(type_, sa.String):
        return False
    if length is None:
        return True
    return getattr(type_, "length", None) == length


def _fail(msg: str) -> None:
    raise RuntimeError(f"RC001 Alembic reconciliation failed: {msg}")


def _require_users_email_verified_at(inspector: sa.Inspector) -> bool:
    if not inspector.has_table(USERS_TABLE):
        _fail(f"required table '{USERS_TABLE}' is missing")
    cols = {c["name"]: c for c in inspector.get_columns(USERS_TABLE)}
    col = cols.get("email_verified_at")
    if col is None:
        return False
    if not _is_datetime_type(col["type"]):
        _fail("users.email_verified_at exists but is not a datetime/timestamptz type")
    if col.get("nullable") not in (True, False):
        _fail("users.email_verified_at nullability could not be verified")
    if col.get("nullable") is False:
        _fail("users.email_verified_at exists but is NOT NULL; incompatible with expected schema")
    return True


def _validate_existing_tokens_table(inspector: sa.Inspector, dialect_name: str | None = None) -> None:
    cols = {c["name"]: c for c in inspector.get_columns(TOKENS_TABLE)}
    missing = [name for name in EXPECTED_TOKEN_COLUMNS if name not in cols]
    if missing:
        _fail(f"{TOKENS_TABLE} exists but is missing columns: {', '.join(sorted(missing))}")

    validators = {
        "id": lambda c: _is_uuid_type(c["type"], dialect_name),
        "user_id": lambda c: _is_uuid_type(c["type"], dialect_name),
        "purpose": lambda c: _is_string_type(c["type"], 32),
        "token_hash": lambda c: _is_string_type(c["type"], 64),
        "expires_at": lambda c: _is_datetime_type(c["type"]),
        "used_at": lambda c: _is_datetime_type(c["type"]),
        "created_at": lambda c: _is_datetime_type(c["type"]),
    }
    for name, expected in EXPECTED_TOKEN_COLUMNS.items():
        col = cols[name]
        if col.get("nullable") != expected["nullable"]:
            _fail(
                f"{TOKENS_TABLE}.{name} nullability mismatch: expected nullable={expected['nullable']} got {col.get('nullable')}"
            )
        if not validators[name](col):
            _fail(f"{TOKENS_TABLE}.{name} has incompatible type {col['type']!r}")

    pk = inspector.get_pk_constraint(TOKENS_TABLE) or {}
    pk_cols = set(pk.get("constrained_columns") or [])
    if pk_cols != {"id"}:
        _fail(f"{TOKENS_TABLE} primary key mismatch: expected ['id'] got {sorted(pk_cols)!r}")

    uniques = inspector.get_unique_constraints(TOKENS_TABLE) or []
    has_token_hash_uq = any(
        set(u.get("column_names") or []) == {"token_hash"} or u.get("name") == TOKEN_HASH_UQ
        for u in uniques
    )
    if not has_token_hash_uq:
        indexes = inspector.get_indexes(TOKENS_TABLE) or []
        has_token_hash_uq = any(
            bool(i.get("unique")) and set(i.get("column_names") or []) == {"token_hash"}
            for i in indexes
        )
    if not has_token_hash_uq:
        _fail(f"{TOKENS_TABLE} missing unique constraint/index on token_hash")

    indexes = inspector.get_indexes(TOKENS_TABLE) or []
    has_user_purpose = any(set(i.get("column_names") or []) == {"user_id", "purpose"} for i in indexes)
    if not has_user_purpose:
        _fail(f"{TOKENS_TABLE} missing index on (user_id, purpose)")

    fks = inspector.get_foreign_keys(TOKENS_TABLE) or []
    has_user_fk = any(
        set(fk.get("constrained_columns") or []) == {"user_id"}
        and fk.get("referred_table") == USERS_TABLE
        and set(fk.get("referred_columns") or []) == {"id"}
        for fk in fks
    )
    if not has_user_fk:
        _fail(f"{TOKENS_TABLE} missing foreign key user_id -> users.id")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    email_verified_exists = _require_users_email_verified_at(inspector)
    tokens_exists = inspector.has_table(TOKENS_TABLE)

    if tokens_exists:
        _validate_existing_tokens_table(inspector, bind.dialect.name)

    if not email_verified_exists:
        op.add_column(
            USERS_TABLE,
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        )
        # Historical policy from e7b1c4d2a809: accounts created before email
        # verification existed keep access unchanged. Only applied when the
        # missing column indicates pre-email-verification schema drift.
        op.execute(
            sa.text("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL")
        )

    if not tokens_exists:
        op.create_table(
            TOKENS_TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("purpose", sa.String(length=32), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], [f"{USERS_TABLE}.id"], name=TOKEN_USER_FK),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name=TOKEN_HASH_UQ),
        )
        op.create_index(TOKEN_USER_PURPOSE_IX, TOKENS_TABLE, ["user_id", "purpose"], unique=False)


def downgrade() -> None:
    # Conservative downgrade: removing auth objects can destroy security data.
    pass
