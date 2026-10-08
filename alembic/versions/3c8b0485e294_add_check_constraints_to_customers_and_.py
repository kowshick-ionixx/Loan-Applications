from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3c8b0485e294"
down_revision: str | Sequence[str] | None = "5af6002ac670"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_customers_name_length", "customers", "char_length(name) BETWEEN 3 AND 50"
    )
    op.create_check_constraint(
        "ck_customers_name_letters", "customers", "name ~ '^[A-Za-z ]+$'"
    )
    op.create_check_constraint(
        "ck_customers_phone_10_digits", "customers", "phone ~ '^[0-9]{10}$'"
    )
    op.create_check_constraint(
        "ck_customers_income_positive", "customers", "monthly_income > 0"
    )

    op.create_check_constraint(
        "ck_loans_amount_range", "loans", "amount BETWEEN 10000 AND 5000000"
    )
    op.create_check_constraint(
        "ck_loans_tenure_allowed", "loans", "tenure_months IN (12, 24, 36, 48, 60)"
    )
    op.create_check_constraint(
        "ck_loans_status_allowed", "loans", "status IN ('APPROVED', 'REJECTED')"
    )
    op.create_check_constraint(
        "ck_loans_rate_positive", "loans", "interest_rate IS NULL OR interest_rate > 0"
    )
    op.create_check_constraint(
        "ck_loans_emi_non_negative", "loans", "emi IS NULL OR emi >= 0"
    )
    op.create_check_constraint(
        "ck_loans_status_consistency",
        "loans",
        "(status = 'APPROVED' AND rejection_reason IS NULL AND emi IS NOT NULL AND interest_rate IS NOT NULL)"
        " OR (status = 'REJECTED' AND rejection_reason IS NOT NULL)",
    )
    op.alter_column("loans", "applied_on", server_default=sa.text("CURRENT_DATE"))


def downgrade() -> None:
    op.alter_column("loans", "applied_on", server_default=None)
    for name in (
        "ck_loans_status_consistency",
        "ck_loans_emi_non_negative",
        "ck_loans_rate_positive",
        "ck_loans_status_allowed",
        "ck_loans_tenure_allowed",
        "ck_loans_amount_range",
    ):
        op.drop_constraint(name, "loans", type_="check")
    for name in (
        "ck_customers_income_positive",
        "ck_customers_phone_10_digits",
        "ck_customers_name_letters",
        "ck_customers_name_length",
    ):
        op.drop_constraint(name, "customers", type_="check")
