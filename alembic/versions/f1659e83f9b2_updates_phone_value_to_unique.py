"""updates phone value to unique"""

from collections.abc import Sequence

from alembic import op

revision: str = "f1659e83f9b2"
down_revision: str | Sequence[str] | None = "265453ea34a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(None, "customers", ["phone"])


def downgrade() -> None:
    op.drop_constraint(None, "customers", type_="unique")
