"""Add per-user task creation idempotency.

Revision ID: a1b2c3d4e5f6
Revises: 8fe4053ad719
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "8fe4053ad719"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("tasks")}
    if "idempotency_key" not in existing_columns:
        op.add_column("tasks", sa.Column("idempotency_key", sa.String(128), nullable=True))
    if "idempotency_hash" not in existing_columns:
        op.add_column("tasks", sa.Column("idempotency_hash", sa.String(64), nullable=True))

    existing_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("tasks")}
    if "uq_tasks_user_idempotency" not in existing_indexes:
        op.create_index(
            "uq_tasks_user_idempotency",
            "tasks",
            ["user_id", "idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("uq_tasks_user_idempotency", table_name="tasks")
    op.drop_column("tasks", "idempotency_hash")
    op.drop_column("tasks", "idempotency_key")
