"""Garante nome de exibição obrigatório nas enfermarias.

Revision ID: 20260729_02
Revises: 20260729_01
Create Date: 2026-07-29
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_02"
down_revision: str | None = "20260729_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE wards SET display_name = name "
            "WHERE display_name IS NULL OR display_name = ''"
        )
    )
    with op.batch_alter_table("wards") as batch_op:
        batch_op.alter_column(
            "display_name",
            existing_type=sa.String(length=50),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("wards") as batch_op:
        batch_op.alter_column(
            "display_name",
            existing_type=sa.String(length=50),
            nullable=True,
        )
