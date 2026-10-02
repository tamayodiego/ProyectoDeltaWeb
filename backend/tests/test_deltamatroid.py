import numpy as np
import pytest

from deltaweb.domain.deltamatroid import DeltaMatroid


def matrix(rows: list[list[int]]) -> np.ndarray:
    return np.array(rows, dtype=np.int64)


def family(masks: list[int]) -> np.ndarray:
    return np.array(masks, dtype=np.uint64)


# --- Construction from a matrix ---


def test_from_skew_symmetric_2x2() -> None:
    # {} -> det 1, {1} and {2} -> det 0, {1,2} -> det 1
    dm = DeltaMatroid("D", field=2, matrix=matrix([[0, 1], [-1, 0]]))

    np.testing.assert_array_equal(dm.feasible_family, family([0b00, 0b11]))
    assert dm.ground_set == ["1", "2"]


def test_from_skew_symmetric_3x3() -> None:
    # Every pair has det 1; singletons and the whole set (odd skew-symmetric) have det 0
    m = matrix([[0, 1, 1], [-1, 0, 1], [-1, -1, 0]])
    dm = DeltaMatroid("D", field=2, matrix=m)

    np.testing.assert_array_equal(dm.feasible_family, family([0b000, 0b011, 0b101, 0b110]))
    assert dm.ground_set == ["1", "2", "3"]


def test_zero_row_stays_in_ground_set() -> None:
    # Row/column 3 is all zeros: element 3 is in no feasible set,
    # but the ground set has one element per row of the matrix
    m = matrix([[0, 1, 0], [-1, 0, 0], [0, 0, 0]])
    dm = DeltaMatroid("D", field=2, matrix=m)

    np.testing.assert_array_equal(dm.feasible_family, family([0b000, 0b011]))
    assert dm.ground_set == ["1", "2", "3"]


def test_binary_field_drops_even_determinants() -> None:
    # det of the whole matrix is -2: 0 mod 2
    dm = DeltaMatroid("D", field=2, matrix=matrix([[1, 1], [1, -1]]))

    np.testing.assert_array_equal(dm.feasible_family, family([0b00, 0b01, 0b10]))


def test_ternary_field_keeps_determinant_minus_two() -> None:
    # det of the whole matrix is -2: -2 mod 3 = 1
    dm = DeltaMatroid("D", field=3, matrix=matrix([[1, 1], [1, -1]]))

    np.testing.assert_array_equal(dm.feasible_family, family([0b00, 0b01, 0b10, 0b11]))


def test_matrix_and_attributes_are_stored() -> None:
    m = matrix([[0, 1], [-1, 0]])
    dm = DeltaMatroid("D1", field=3, matrix=m)

    assert dm.name == "D1"
    assert dm.field == 3
    assert dm.matrix is m
    assert dm.feasible_family.dtype == np.uint64


# --- Construction from a feasible family ---


def test_from_feasible_family() -> None:
    f = family([0b000, 0b011, 0b101])
    dm = DeltaMatroid("D", feasible_family=f)

    np.testing.assert_array_equal(dm.feasible_family, f)
    assert dm.matrix is None
    assert dm.field == 2
    assert dm.ground_set == ["1", "2", "3"]


def test_ground_set_keeps_gaps_aligned_with_bits() -> None:
    # Bit 1 (element "2") appears in no feasible set, but it keeps its place:
    # label k always names bit k - 1
    dm = DeltaMatroid("D", feasible_family=family([0b000, 0b101]))

    assert dm.ground_set == ["1", "2", "3"]


def test_explicit_size_adds_trailing_elements() -> None:
    dm = DeltaMatroid("D", feasible_family=family([0b000, 0b011]), size=4)

    assert dm.ground_set == ["1", "2", "3", "4"]


def test_size_smaller_than_family_raises() -> None:
    with pytest.raises(ValueError, match="use element 3, but size is 2"):
        DeltaMatroid("D", feasible_family=family([0b000, 0b101]), size=2)


def test_matrix_takes_precedence_over_family() -> None:
    dm = DeltaMatroid("D", matrix=matrix([[0, 1], [-1, 0]]), feasible_family=family([0b1]))

    np.testing.assert_array_equal(dm.feasible_family, family([0b00, 0b11]))


def test_without_matrix_or_family_raises() -> None:
    with pytest.raises(ValueError, match="matrix or a feasible family"):
        DeltaMatroid("D")


# --- Helpers ---


def test_submatrix() -> None:
    m = matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

    np.testing.assert_array_equal(DeltaMatroid.submatrix(m, [0, 2]), matrix([[1, 3], [7, 9]]))
    assert DeltaMatroid.submatrix(m, []).shape == (0, 0)


def test_relabel() -> None:
    dm = DeltaMatroid("D", feasible_family=family([0b000, 0b011, 0b101]))
    dm.relabel(["a", "b", "c"])

    assert dm.ground_set == ["a", "b", "c"]


def test_relabel_with_wrong_length_raises() -> None:
    dm = DeltaMatroid("D", feasible_family=family([0b000, 0b011, 0b101]))

    with pytest.raises(ValueError, match="Expected 3 labels, got 2"):
        dm.relabel(["a", "b"])
