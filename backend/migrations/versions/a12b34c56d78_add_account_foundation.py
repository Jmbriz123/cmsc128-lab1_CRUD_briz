"""Add users, persistent sessions, and password reset tokens.

Revision ID: a12b34c56d78
Revises: 9a2b3c4d5e6f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a12b34c56d78"
down_revision: Union[str, Sequence[str], None] = "9a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    for table in ("auth_sessions", "password_reset_tokens"):
        columns = [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        ]
        if table == "password_reset_tokens":
            columns.append(sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True))
        op.create_table(
            table,
            *columns,
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("token_hash", name=f"uq_{table}_token_hash"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    for table in ("password_reset_tokens", "auth_sessions"):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_table(table)
    op.drop_table("users")
