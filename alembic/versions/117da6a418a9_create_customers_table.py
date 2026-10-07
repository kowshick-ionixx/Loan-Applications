from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "117da6a418a9"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=10), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("monthly_income", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_email"), "customers", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_customers_email"), table_name="customers")
    op.drop_table("customers")
