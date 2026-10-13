"""Deleting a customer unlinks its login instead of deleting it."""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e8f2a19d07"
down_revision: str | Sequence[str] | None = "a7c2e91d4b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("users_customer_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_customer_id_fkey",
        "users",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("users_customer_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_customer_id_fkey",
        "users",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="CASCADE",
    )
