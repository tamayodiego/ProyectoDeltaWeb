"""create folders

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("name <> ''", name=op.f("ck_folders_name_not_empty")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_folders_owner_id_users")),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["folders.id"],
            name=op.f("fk_folders_parent_id_folders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_folders")),
        sa.UniqueConstraint(
            "owner_id",
            "parent_id",
            "name",
            name="uq_folders_owner_id_parent_id_name",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(op.f("ix_folders_owner_id"), "folders", ["owner_id"], unique=False)
    op.create_index(op.f("ix_folders_parent_id"), "folders", ["parent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_folders_parent_id"), table_name="folders")
    op.drop_index(op.f("ix_folders_owner_id"), table_name="folders")
    op.drop_table("folders")
