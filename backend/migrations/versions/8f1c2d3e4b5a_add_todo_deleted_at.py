"""add soft delete support to todos

Revision ID: 8f1c2d3e4b5a
Revises: 676f5530653f
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f1c2d3e4b5a"
down_revision: Union[str, Sequence[str], None] = "676f5530653f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("todos", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_todos_deleted_at"), "todos", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_todos_deleted_at"), table_name="todos")
    op.drop_column("todos", "deleted_at")