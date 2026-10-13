"""Allow self-registered customers: CUSTOMER users without a profile yet."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7c2e91d4b10"
down_revision: str | Sequence[str] | None = "f33d82f48a51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Registered usernames are emails, which can be longer than 50 characters.
    op.alter_column(
        "users",
        "username",
        type_=sa.String(length=255),
        existing_type=sa.String(length=50),
        existing_nullable=False,
    )
    op.drop_constraint("ck_users_customer_link", "users", type_="check")
    op.create_check_constraint(
        "ck_users_customer_link", "users", "role = 'CUSTOMER' OR customer_id IS NULL"
    )


def downgrade() -> None:
    # Fails while CUSTOMER users without a profile, or long usernames, exist.
    op.drop_constraint("ck_users_customer_link", "users", type_="check")
    op.create_check_constraint(
        "ck_users_customer_link",
        "users",
        "(role = 'OFFICER' AND customer_id IS NULL)"
        " OR (role = 'CUSTOMER' AND customer_id IS NOT NULL)",
    )
    op.alter_column(
        "users",
        "username",
        type_=sa.String(length=50),
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
