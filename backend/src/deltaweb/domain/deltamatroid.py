from typing import Literal

import flint
import numpy as np
from numpy import uint64 as Feasible
from numpy.typing import NDArray as Family
from numpy.typing import NDArray as Matrix


class InvalidMatrixError(ValueError):
    """The matrix is not a valid symmetric or skew-symmetric matrix."""


def validate_matrix(matrix: Matrix[np.int64]) -> Literal["symmetric", "skew-symmetric"]:
    """Return the kind of matrix, or raise InvalidMatrixError.

    symmetric:      square, entries in {0, 1}, M[i][j] == M[j][i]
    skew-symmetric: square, entries in {-1, 0, 1}, M[i][j] == -M[j][i]
    The zero matrix is both and is reported as "symmetric".
    """
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] == 0:
        raise InvalidMatrixError(f"Expected a non-empty square matrix, got shape {matrix.shape}")
    if np.isin(matrix, (0, 1)).all() and (matrix == matrix.T).all():
        return "symmetric"
    if np.isin(matrix, (-1, 0, 1)).all() and (matrix == -matrix.T).all():
        return "skew-symmetric"
    raise InvalidMatrixError("Matrix is neither symmetric (0/1) nor skew-symmetric (-1/0/1)")


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
            # GF(2) requires a symmetric matrix, GF(3) a skew-symmetric one
            kind = validate_matrix(matrix)
            is_zero = not matrix.any()
            expected = "symmetric" if field == 2 else "skew-symmetric"
            if kind != expected and not is_zero:
                raise InvalidMatrixError(f"GF({field}) requires a {expected} matrix, got {kind}")
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

    def fingerprint(self) -> tuple[int, ...]:
        """Number of feasible sets of each size: entry k counts those with k elements (0..n)."""
        n = len(self.ground_set)
        sizes = np.bitwise_count(self.feasible_family).astype(np.intp)
        return tuple(int(count) for count in np.bincount(sizes, minlength=n + 1))

    def frequencies(self) -> list[int]:
        """Entry i counts the feasible sets that contain element i + 1."""
        n = len(self.ground_set)
        bits = (self.feasible_family[:, None] >> np.arange(n, dtype=Feasible)) & Feasible(1)
        return [int(count) for count in bits.sum(axis=0)]
