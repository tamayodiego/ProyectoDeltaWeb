"""Delta-matroid data that travels as JSON."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

from deltaweb.config import get_settings

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


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
