"""enforce one organization membership per user

Revision ID: b7e4a2c9d615
Revises: f2b6c8d0a913
"""

from collections.abc import Sequence

from sqlalchemy import inspect, text

from alembic import op

revision: str = "b7e4a2c9d615"
down_revision: str | Sequence[str] | None = "f2b6c8d0a913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = inspector.get_unique_constraints("organization_memberships")
    if any(tuple(item["column_names"]) == ("user_id",) for item in existing):
        return

    duplicate_users = bind.execute(
        text(
            """
            SELECT count(*)
            FROM (
                SELECT user_id
                FROM organization_memberships
                GROUP BY user_id
                HAVING count(*) > 1
            ) duplicates
            """
        )
    ).scalar_one()
    if duplicate_users:
        raise RuntimeError(
            "Refusing to enforce single membership: "
            f"{duplicate_users} users have duplicate organization memberships"
        )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("organization_memberships") as batch_op:
            batch_op.create_unique_constraint(
                "uq_organization_memberships_user",
                ["user_id"],
            )
    else:
        op.create_unique_constraint(
            "uq_organization_memberships_user",
            "organization_memberships",
            ["user_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("organization_memberships") as batch_op:
            batch_op.drop_constraint(
                "uq_organization_memberships_user",
                type_="unique",
            )
    else:
        op.drop_constraint(
            "uq_organization_memberships_user",
            "organization_memberships",
            type_="unique",
        )
