"""Saved delta-matroids. Named DeltaMatroidRecord: DeltaMatroid is the domain class.

Only the input matrix and the feasible family are stored; fingerprint and frequencies are
cheap to recalculate from the family, so they are computed when read.
"""

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from deltaweb.db import Base


class DeltaMatroidRecord(Base):
    __tablename__ = "delta_matroids"
    __table_args__ = (
        CheckConstraint("name <> ''", name="name_not_empty"),
        CheckConstraint("field IN (2, 3)", name="field_is_2_or_3"),
        # Same rule as folders: unique names in the same place, case-sensitive, and
        # NULLS NOT DISTINCT so delta-matroids in the root are unique too
        UniqueConstraint(
            "owner_id",
            "folder_id",
            "name",
            name="uq_delta_matroids_owner_id_folder_id_name",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # None = root. Deleting a folder deletes the delta-matroids inside it
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[int] = mapped_column(SmallInteger)
    matrix: Mapped[list[list[int]]] = mapped_column(ARRAY(Integer, dimensions=2))
    ground_set: Mapped[list[str]] = mapped_column(ARRAY(Text))
    # Bitmasks: bit k set <=> ground_set[k] is in the feasible set (fits BIGINT for n <= 63)
    feasible: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
