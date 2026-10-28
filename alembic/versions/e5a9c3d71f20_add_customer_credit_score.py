"""Customers get an optional credit score (300-900); existing customers stay NULL."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5a9c3d71f20"
down_revision: str | Sequence[str] | None = "d81f3b6c2a45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("credit_score", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_customers_credit_score_range",
        "customers",
        "credit_score IS NULL OR credit_score BETWEEN 300 AND 900",
    )


def downgrade() -> None:
    op.drop_constraint("ck_customers_credit_score_range", "customers", type_="check")
    op.drop_column("customers", "credit_score")
