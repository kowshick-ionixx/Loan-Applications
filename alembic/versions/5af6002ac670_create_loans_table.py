from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5af6002ac670"
down_revision: str | Sequence[str] | None = "117da6a418a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tenure_months", sa.Integer(), nullable=False),
        sa.Column("interest_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("emi", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("applied_on", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_loans_customer_id"), "loans", ["customer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_loans_customer_id"), table_name="loans")
    op.drop_table("loans")
