"""Link every task to the account that owns it.

Revision ID: b23c45d67e89
Revises: a12b34c56d78

Tasks created before this revision were shared by all signed-in users and
cannot be attributed to an owner, so they are removed rather than exposed
to an arbitrary account.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b23c45d67e89"
down_revision: Union[str, Sequence[str], None] = "a12b34c56d78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM todos")
    op.add_column("todos", sa.Column("user_id", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "fk_todos_user_id_users", "todos", "users", ["user_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index(op.f("ix_todos_user_id"), "todos", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_todos_user_id"), table_name="todos")
    op.drop_constraint("fk_todos_user_id_users", "todos", type_="foreignkey")
    op.drop_column("todos", "user_id")
