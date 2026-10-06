"""Folders. Each user organizes their delta-matroids in a tree of folders."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from deltaweb.db import Base


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (
        CheckConstraint("name <> ''", name="name_not_empty"),
        # No two folders with the same name in the same place. Case-sensitive: "Research"
        # and "research" can coexist. NULLS NOT DISTINCT so root folders (parent_id NULL)
        # are also unique per owner (PostgreSQL 15+).
        UniqueConstraint(
            "owner_id",
            "parent_id",
            "name",
            name="uq_folders_owner_id_parent_id_name",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # None = root folder. Deleting a folder deletes its subfolders
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
