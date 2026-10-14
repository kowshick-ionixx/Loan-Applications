"""Customers get an optional address (customers may edit it themselves)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d81f3b6c2a45"
down_revision: str | Sequence[str] | None = "c4e8f2a19d07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("address", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "address")
