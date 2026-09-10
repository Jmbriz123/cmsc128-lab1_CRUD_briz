"""add todo filtering and sorting fields

Revision ID: 9a2b3c4d5e6f
Revises: 8f1c2d3e4b5a
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "8f1c2d3e4b5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("todos", sa.Column("due_date", sa.DateTime(), nullable=True))
    op.add_column(
        "todos",
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            server_default="medium",
        ),
    )
    op.add_column("todos", sa.Column("tag", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_todos_due_date"), "todos", ["due_date"], unique=False)
    op.create_index(op.f("ix_todos_priority"), "todos", ["priority"], unique=False)
    op.create_index(op.f("ix_todos_tag"), "todos", ["tag"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_todos_tag"), table_name="todos")
    op.drop_index(op.f("ix_todos_priority"), table_name="todos")
    op.drop_index(op.f("ix_todos_due_date"), table_name="todos")
    op.drop_column("todos", "tag")
    op.drop_column("todos", "priority")
    op.drop_column("todos", "due_date")