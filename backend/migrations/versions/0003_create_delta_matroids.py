"""create delta matroids

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delta_matroids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("folder_id", sa.Integer(), nullable=True),
        sa.Column("field", sa.SmallInteger(), nullable=False),
        sa.Column("matrix", sa.ARRAY(sa.Integer(), dimensions=2), nullable=False),
        sa.Column("ground_set", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("feasible", sa.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("name <> ''", name=op.f("ck_delta_matroids_name_not_empty")),
        sa.CheckConstraint("field IN (2, 3)", name=op.f("ck_delta_matroids_field_is_2_or_3")),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["folders.id"],
            name=op.f("fk_delta_matroids_folder_id_folders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_delta_matroids_owner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delta_matroids")),
        sa.UniqueConstraint(
            "owner_id",
            "folder_id",
            "name",
            name="uq_delta_matroids_owner_id_folder_id_name",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        op.f("ix_delta_matroids_folder_id"), "delta_matroids", ["folder_id"], unique=False
    )
    op.create_index(
        op.f("ix_delta_matroids_owner_id"), "delta_matroids", ["owner_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_delta_matroids_owner_id"), table_name="delta_matroids")
    op.drop_index(op.f("ix_delta_matroids_folder_id"), table_name="delta_matroids")
    op.drop_table("delta_matroids")
