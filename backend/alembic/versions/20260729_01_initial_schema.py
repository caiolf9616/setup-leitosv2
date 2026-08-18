"""Schema inicial do Setup de Leitos v2.

Revision ID: 20260729_01
Revises:
Create Date: 2026-07-29
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


event_type = sa.Enum(
    "ALTA",
    "DESOCUPADO",
    "APTO",
    "OCUPADO",
    name="event_type",
)
user_role = sa.Enum("UNIDADE", "COORDENADOR", name="user_role")
account_user_role = sa.Enum(
    "UNIDADE",
    "COORDENADOR",
    name="account_user_role",
)


def upgrade() -> None:
    op.create_table(
        "unit_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_group", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unit_group"),
    )
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("unit_group", sa.String(length=50), nullable=False),
        sa.Column("role", account_user_role, nullable=False),
        sa.Column("employment_type", sa.String(length=30), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(
        op.f("ix_user_accounts_unit_group"),
        "user_accounts",
        ["unit_group"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_accounts_username"),
        "user_accounts",
        ["username"],
        unique=True,
    )
    op.create_table(
        "wards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("unit_group", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_wards_unit_group"),
        "wards",
        ["unit_group"],
        unique=False,
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["unit_credentials.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "beds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ward_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ward_id", "number", name="uq_bed_ward_number"),
    )
    op.create_table(
        "bed_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bed_id", sa.Integer(), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_unit", sa.String(length=50), nullable=False),
        sa.Column("recorded_by_user", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bed_id"], ["beds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bed_events")
    op.drop_table("beds")
    op.drop_table("user_sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_wards_unit_group"), table_name="wards")
    op.drop_table("wards")
    op.drop_index(op.f("ix_user_accounts_username"), table_name="user_accounts")
    op.drop_index(op.f("ix_user_accounts_unit_group"), table_name="user_accounts")
    op.drop_table("user_accounts")
    op.drop_table("unit_credentials")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        account_user_role.drop(bind, checkfirst=True)
        user_role.drop(bind, checkfirst=True)
        event_type.drop(bind, checkfirst=True)
