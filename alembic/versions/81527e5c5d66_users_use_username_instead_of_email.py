"""users use username instead of email"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "81527e5c5d66"
down_revision: str | Sequence[str] | None = "52d206543609"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=False))
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.drop_column("users", "email")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    )
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.drop_column("users", "username")
