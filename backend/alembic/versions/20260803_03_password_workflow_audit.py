"""Adiciona troca obrigatoria de senha e auditoria administrativa.

Revision ID: 20260803_03
Revises: 20260729_02
Create Date: 2026-08-03
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260803_03"
down_revision: str | None = "20260729_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.add_column(
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_username", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_username", sa.String(length=80), nullable=True),
        sa.Column("details", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_username", "audit_logs", ["actor_username"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_target_username", "audit_logs", ["target_username"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.drop_column("must_change_password")
