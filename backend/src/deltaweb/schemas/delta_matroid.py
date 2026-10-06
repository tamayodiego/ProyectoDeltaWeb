"""Delta-matroid data that travels as JSON."""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

from deltaweb.config import get_settings

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
# Same rules as folder names: stripped, 1..255 characters
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class GenerateRequest(BaseModel):
    """A symmetric 0/1 matrix over GF(2), or a skew-symmetric -1/0/1 matrix over GF(3)."""

    matrix: list[list[int]] = Field(min_length=1)
    field: Literal[2, 3]
    labels: list[Label] | None = None  # default "1", "2", ..., "n"

    @model_validator(mode="after")
    def check_shape_and_labels(self) -> Self:
        n = len(self.matrix)
        if any(len(row) != n for row in self.matrix):
            raise ValueError("matrix must be square")
        limit = get_settings().max_matrix_size
        if n > limit:
            raise ValueError(f"matrix size {n} exceeds the limit of {limit}")
        if self.labels is not None:
            if len(self.labels) != n:
                raise ValueError(f"expected {n} labels, got {len(self.labels)}")
            if len(set(self.labels)) != n:
                raise ValueError("labels must be unique")
        return self


class GeneratedDeltaMatroid(BaseModel):
    """The feasible family as bitmasks: bit k set <=> ``ground_set[k]`` is in the set.

    Example with ground_set ["a", "b", "c"]: 5 = 0b101 = {"a", "c"}.
    """

    field: Literal[2, 3]
    ground_set: list[str]
    feasible: list[int]
    fingerprint: list[int]  # feasible sets of each size, 0..n
    frequencies: list[int]  # feasible sets that contain each element


# --- Saved delta-matroids ---


class DeltaMatroidCreate(GenerateRequest):
    """Generate from the matrix, then save under ``name`` in ``folder_id`` (None = root)."""

    name: Name
    folder_id: int | None = None


class DeltaMatroidUpdate(BaseModel):
    """Only the fields that are sent change. ``"folder_id": null`` moves to the root."""

    name: Name | None = None
    folder_id: int | None = None

    @model_validator(mode="after")
    def name_cannot_be_null(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class DeltaMatroidSummary(BaseModel):
    """Light version for lists: no matrix and no family (it can have 2^n sets)."""

    id: int
    name: str
    folder_id: int | None
    field: Literal[2, 3]
    size: int  # n, the size of the ground set
    feasible_count: int
    created_at: datetime


class DeltaMatroidOut(GeneratedDeltaMatroid):
    """Everything about a saved delta-matroid."""

    id: int
    name: str
    folder_id: int | None
    matrix: list[list[int]]
    created_at: datetime
