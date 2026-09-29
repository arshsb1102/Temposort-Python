"""Add ownership foreign keys with cascade deletion.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_foreign_key(table_name: str, columns: list[str], referred_table: str) -> bool:
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    return any(
        foreign_key["constrained_columns"] == columns
        and foreign_key["referred_table"] == referred_table
        for foreign_key in foreign_keys
    )


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_foreign_key("tasks", ["user_id"], "users"):
        orphan_tasks = bind.execute(
            sa.text("SELECT count(*) FROM tasks t LEFT JOIN users u ON u.id = t.user_id WHERE u.id IS NULL")
        ).scalar_one()
        if orphan_tasks:
            raise RuntimeError(f"Cannot add task ownership constraint: {orphan_tasks} orphan tasks exist")
        op.create_foreign_key(
            "fk_tasks_user_id_users",
            "tasks",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if not _has_foreign_key("reminders", ["user_email"], "users"):
        orphan_reminders = bind.execute(
            sa.text("SELECT count(*) FROM reminders r LEFT JOIN users u ON u.email = r.user_email WHERE u.id IS NULL")
        ).scalar_one()
        if orphan_reminders:
            raise RuntimeError(f"Cannot add reminder ownership constraint: {orphan_reminders} orphan reminders exist")
        op.create_foreign_key(
            "fk_reminders_user_email_users",
            "reminders",
            "users",
            ["user_email"],
            ["email"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    if _has_foreign_key("reminders", ["user_email"], "users"):
        op.drop_constraint("fk_reminders_user_email_users", "reminders", type_="foreignkey")
    if _has_foreign_key("tasks", ["user_id"], "users"):
        op.drop_constraint("fk_tasks_user_id_users", "tasks", type_="foreignkey")
