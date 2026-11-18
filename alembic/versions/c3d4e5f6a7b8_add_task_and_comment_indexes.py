"""add task and comment composite indexes

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-11-18 08:35:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema by adding composite indexes."""
    op.create_index(
        op.f("ix_tasks_project_id_status"),
        "tasks",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_comments_task_id_created_at"),
        "comments",
        ["task_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_comments_task_id_created_at"), table_name="comments")
    op.drop_index(op.f("ix_tasks_project_id_status"), table_name="tasks")
