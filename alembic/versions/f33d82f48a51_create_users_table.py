from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f33d82f48a51"
down_revision: str | Sequence[str] | None = "3c8b0485e294"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('OFFICER', 'CUSTOMER')", name="ck_users_role_allowed"
        ),
        sa.CheckConstraint(
            "(role = 'OFFICER' AND customer_id IS NULL)"
            " OR (role = 'CUSTOMER' AND customer_id IS NOT NULL)",
            name="ck_users_customer_link",
        ),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
