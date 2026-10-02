from typing import Literal

import flint
import numpy as np
from numpy import uint64 as Feasible
from numpy.typing import NDArray as Family
from numpy.typing import NDArray as Matrix


class DeltaMatroid:
    """Describe what this class represents."""

    # --- Class attributes (shared by all instances) ---
    # name: type = value
    name: str
    field: Literal[2, 3]  # 2 = binary, 3 = ternary
    matrix: Matrix[np.int64] | None
    ground_set: list[str]
    feasible_family: Family[Feasible]

    # --- Constructor: name is required; build from a matrix or from a feasible family ---
    def __init__(
        self,
        name: str,
        field: Literal[2, 3] = 2,
        matrix: Matrix[np.int64] | None = None,
        feasible_family: Family[Feasible] | None = None,
        size: int | None = None,
    ) -> None:
        self.name = name
        self.field = field
        self.matrix = matrix

        if matrix is not None:
            self.feasible_family = self.calculate_dm_from_matrix(matrix, field)
        elif feasible_family is not None:
            self.feasible_family = feasible_family
        else:
            raise ValueError("Provide a matrix or a feasible family")

        # Ground set = {1, ..., n}: bit k of a feasible set <-> element k + 1.
        # n is explicit so that labels never drift from bit positions.
        # From a matrix n = len(matrix); from a family n = ``size`` or, if omitted,
        # the highest element that appears in some feasible set.
        union = int(np.bitwise_or.reduce(self.feasible_family))
        if matrix is not None:
            n = len(matrix)
        elif size is not None:
            n = size
        else:
            n = union.bit_length()
        if union.bit_length() > n:
            raise ValueError(f"Feasible sets use element {union.bit_length()}, but size is {n}")
        self.ground_set = [str(i + 1) for i in range(n)]

    @staticmethod
    def calculate_dm_from_matrix(
        matrix: Matrix[np.int64], field: Literal[2, 3]
    ) -> Family[Feasible]:
        """Feasible family (as bitmasks) of the delta-matroid of ``matrix`` over GF(field)."""
        n = len(matrix)
        feasible: list[int] = []
        for binary_word in range(2**n):
            # bit k of binary_word on -> row/column k belongs to the subset
            index = [k for k in range(n) if (binary_word >> k) & 1]
            sub_matrix = DeltaMatroid.submatrix(matrix, index)
            size = len(index)
            det = flint.fmpz_mat(size, size, sub_matrix.flatten().tolist()).det()
            if int(det) % field != 0:
                feasible.append(binary_word)
        return np.array(feasible, dtype=Feasible)

    @staticmethod
    def submatrix(matrix: Matrix[np.int64], indices: list[int]) -> Matrix[np.int64]:
        """Principal submatrix of ``matrix``: rows and columns given by ``indices``."""
        return matrix[np.ix_(indices, indices)]

    def relabel(self, labels: list[str]) -> None:
        """Replace the ground set labels, keeping their order."""
        if len(labels) != len(self.ground_set):
            raise ValueError(f"Expected {len(self.ground_set)} labels, got {len(labels)}")
        self.ground_set = labels
