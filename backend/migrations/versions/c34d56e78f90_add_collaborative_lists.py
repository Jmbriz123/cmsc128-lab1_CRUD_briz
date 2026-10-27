"""Add collaborative lists, their memberships, and an optional list on tasks.

Revision ID: c34d56e78f90
Revises: b23c45d67e89
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c34d56e78f90"
down_revision: Union[str, Sequence[str], None] = "b23c45d67e89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_task_lists_owner_id", "task_lists", ["owner_id"])
    op.create_table(
        "list_members",
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("list_id", "user_id"),
        sa.ForeignKeyConstraint(["list_id"], ["task_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_list_members_user_id", "list_members", ["user_id"])
    op.add_column("todos", sa.Column("list_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_todos_list_id_task_lists", "todos", "task_lists", ["list_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index(op.f("ix_todos_list_id"), "todos", ["list_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_todos_list_id"), table_name="todos")
    op.drop_constraint("fk_todos_list_id_task_lists", "todos", type_="foreignkey")
    op.drop_column("todos", "list_id")
    op.drop_index("ix_list_members_user_id", table_name="list_members")
    op.drop_table("list_members")
    op.drop_index("ix_task_lists_owner_id", table_name="task_lists")
    op.drop_table("task_lists")
