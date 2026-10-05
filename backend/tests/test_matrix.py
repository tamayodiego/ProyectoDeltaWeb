"""Tests for matrix validation (Phase 1, task 2).

Expected API, in ``src/deltaweb/domain/deltamatroid.py`` (module-level, outside the class):

    class InvalidMatrixError(ValueError): ...

    def validate_matrix(matrix: NDArray[np.int64]) -> Literal["symmetric", "skew-symmetric"]:
        '''Return the kind of matrix, or raise InvalidMatrixError.'''

Valid matrices:
- symmetric:      square, entries in {0, 1}, M[i][j] == M[j][i]
- skew-symmetric: square, entries in {-1, 0, 1}, M[i][j] == -M[j][i] (so the diagonal is 0)

A matrix that is both (only the zero matrix) is reported as "symmetric".
"""

import numpy as np
import pytest

from deltaweb.domain.deltamatroid import InvalidMatrixError, validate_matrix


def matrix(rows: list[list[int]]) -> np.ndarray:
    return np.array(rows, dtype=np.int64)


# --- Valid matrices ---


@pytest.mark.parametrize(
    "rows",
    [
        [[1]],
        [[0]],
        [[1, 0], [0, 1]],
        [[1, 1], [1, 1]],
        [[1, 1, 1], [1, 0, 1], [1, 1, 1]],  # golden n=3 SIM semilla=2
    ],
)
def test_symmetric_matrices(rows: list[list[int]]) -> None:
    assert validate_matrix(matrix(rows)) == "symmetric"


@pytest.mark.parametrize(
    "rows",
    [
        [[0, 1], [-1, 0]],
        [[0, -1], [1, 0]],
        [[0, 1, -1], [-1, 0, -1], [1, 1, 0]],  # golden n=3 ANTI semilla=2
    ],
)
def test_skew_symmetric_matrices(rows: list[list[int]]) -> None:
    assert validate_matrix(matrix(rows)) == "skew-symmetric"


def test_zero_matrix_counts_as_symmetric() -> None:
    assert validate_matrix(matrix([[0, 0], [0, 0]])) == "symmetric"


def test_skew_symmetric_with_negatives_only_below_diagonal() -> None:
    # The Java app's Validar got this one wrong: it looked for negatives only above the diagonal
    assert validate_matrix(matrix([[0, 1, 1], [-1, 0, 1], [-1, -1, 0]])) == "skew-symmetric"


# --- Invalid matrices ---


@pytest.mark.parametrize(
    ("rows", "reason"),
    [
        ([[1, 0, 1], [0, 1, 0]], "not square"),
        ([[1, 1], [0, 1]], "symmetric 0/1 entries but M[0][1] != M[1][0]"),
        ([[0, 1], [1, -1]], "neither: -1 on the diagonal"),
        ([[2, 0], [0, 1]], "entry 2 is out of range"),
        ([[0, 2], [-2, 0]], "skew-symmetric shape but entries out of {-1, 0, 1}"),
        ([[1, -1], [1, 0]], "has -1, so it can only be skew, but the diagonal is not 0"),
        ([[0, 1], [1, 0], [0, 0]], "more rows than columns"),
    ],
)
def test_invalid_matrices_raise(rows: list[list[int]], reason: str) -> None:
    with pytest.raises(InvalidMatrixError):
        validate_matrix(matrix(rows))


def test_empty_matrix_raises() -> None:
    with pytest.raises(InvalidMatrixError):
        validate_matrix(np.zeros((0, 0), dtype=np.int64))


def test_one_dimensional_array_raises() -> None:
    with pytest.raises(InvalidMatrixError):
        validate_matrix(np.array([0, 1, 0], dtype=np.int64))


def test_invalid_matrix_error_is_a_value_error() -> None:
    # So code that already catches ValueError keeps working
    assert issubclass(InvalidMatrixError, ValueError)
