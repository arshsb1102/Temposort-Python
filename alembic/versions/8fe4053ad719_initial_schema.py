"""Create the initial TempoSort schema.

Revision ID: 8fe4053ad719
Revises:
Create Date: 2026-09-26 03:29:46.967001
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "8fe4053ad719"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_index_if_missing(
    table_name: str,
    index_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_index_if_missing("users", "ix_users_email", ["email"], unique=True)

    if not inspector.has_table("verification_tokens"):
        op.create_table(
            "verification_tokens",
            sa.Column("token", sa.String(255), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False),
        )
    _create_index_if_missing(
        "verification_tokens",
        "ix_verification_tokens_email",
        ["email"],
    )

    if not inspector.has_table("tasks"):
        op.create_table(
            "tasks",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.String(2000), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("priority", sa.String(32), server_default="medium", nullable=False),
            sa.Column("idempotency_key", sa.String(128), nullable=True),
            sa.Column("idempotency_hash", sa.String(64), nullable=True),
            sa.Column("is_completed", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    existing_task_columns = {column["name"] for column in sa.inspect(bind).get_columns("tasks")}
    if "idempotency_key" not in existing_task_columns:
        op.add_column("tasks", sa.Column("idempotency_key", sa.String(128), nullable=True))
    if "idempotency_hash" not in existing_task_columns:
        op.add_column("tasks", sa.Column("idempotency_hash", sa.String(64), nullable=True))
    _create_index_if_missing("tasks", "ix_tasks_user_id", ["user_id"])
    _create_index_if_missing(
        "tasks",
        "uq_tasks_user_idempotency",
        ["user_id", "idempotency_key"],
        unique=True,
    )

    if not inspector.has_table("reminders"):
        op.create_table(
            "reminders",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_email", sa.String(255), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("message", sa.String(2000), nullable=False),
            sa.Column("channel", sa.String(32), server_default="email", nullable=False),
            sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_sent", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.ForeignKeyConstraint(["user_email"], ["users.email"], ondelete="CASCADE"),
        )
    _create_index_if_missing("reminders", "ix_reminders_user_email", ["user_email"])


def downgrade() -> None:
    raise NotImplementedError("The initial schema may have adopted existing data and cannot be safely downgraded.")
