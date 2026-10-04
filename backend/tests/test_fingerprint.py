"""Tests for the fingerprint (huella) and frequency table (Phase 1, task 3).

Expected API, as methods of ``DeltaMatroid``:

    def fingerprint(self) -> tuple[int, ...]:
        '''Number of feasible sets of each size: entry k counts feasible sets with k elements.
        Length n + 1 (sizes 0..n).'''

    def frequencies(self) -> list[int]:
        '''Entry i counts the feasible sets that contain element i + 1. Length n.'''

n is the size of the ground set (len(dm.ground_set)), not just the elements that appear.
The matrix cases are taken from the Java golden master (backend/tests/golden/).
GF(2) takes symmetric matrices and GF(3) skew-symmetric ones (the zero matrix fits both).
"""

import numpy as np
import pytest

from deltaweb.domain.deltamatroid import DeltaMatroid

pytestmark = pytest.mark.skip(reason="fingerprint() and frequencies() not implemented yet")


def family(masks: list[int]) -> np.ndarray:
    return np.array(masks, dtype=np.uint64)


def matrix(rows: list[list[int]]) -> np.ndarray:
    return np.array(rows, dtype=np.int64)


# --- From a feasible family ---


def test_fingerprint_of_small_family() -> None:
    # {}, {1,2}, {1,3}, {2,3}
    dm = DeltaMatroid("D", feasible_family=family([0b000, 0b011, 0b101, 0b110]))

    assert dm.fingerprint() == (1, 0, 3, 0)


def test_frequencies_of_small_family() -> None:
    dm = DeltaMatroid("D", feasible_family=family([0b000, 0b011, 0b101, 0b110]))

    assert dm.frequencies() == [2, 2, 2]


def test_element_in_no_feasible_set_has_frequency_zero() -> None:
    # Element 2 appears in no feasible set but is part of the ground set
    dm = DeltaMatroid("D", feasible_family=family([0b000, 0b101]))

    assert dm.frequencies() == [1, 0, 1]
    assert dm.fingerprint() == (1, 0, 1, 0)


def test_explicit_size_extends_both_tables() -> None:
    dm = DeltaMatroid("D", feasible_family=family([0b0, 0b1]), size=3)

    assert dm.fingerprint() == (1, 1, 0, 0)
    assert dm.frequencies() == [1, 0, 0]


def test_types_are_plain_python_ints() -> None:
    # numpy integers do not serialize to JSON; the API will need plain ints
    dm = DeltaMatroid("D", feasible_family=family([0b00, 0b11]))

    assert all(type(x) is int for x in dm.fingerprint())
    assert all(type(x) is int for x in dm.frequencies())


# --- From matrices (golden master cases) ---


@pytest.mark.parametrize(
    ("field", "rows", "fingerprint", "frequencies"),
    [
        # n=1 ANTI GF3: only the empty set
        (3, [[0]], (1, 0), [0]),
        # n=2 ANTI GF3 semilla=1
        (3, [[0, 1], [-1, 0]], (1, 0, 1), [1, 1]),
        # n=2 SIM GF2 semilla=2
        (2, [[1, 1], [1, 1]], (1, 2, 0), [1, 1]),
        # n=3 SIM GF2 semilla=1 (two zero rows)
        (2, [[1, 0, 0], [0, 0, 0], [0, 0, 0]], (1, 1, 0, 0), [1, 0, 0]),
        # n=3 ANTI GF3 semilla=1
        (3, [[0, -1, -1], [1, 0, 0], [1, 0, 0]], (1, 0, 2, 0), [2, 1, 1]),
        # n=4 SIM GF2 semilla=3
        (
            2,
            [[1, 0, 0, 0], [0, 1, 1, 0], [0, 1, 0, 1], [0, 0, 1, 1]],
            (1, 3, 5, 3, 0),
            [6, 6, 4, 6],
        ),
    ],
)
def test_golden_cases(
    field: int, rows: list[list[int]], fingerprint: tuple[int, ...], frequencies: list[int]
) -> None:
    dm = DeltaMatroid("D", field=field, matrix=matrix(rows))  # type: ignore[arg-type]

    assert dm.fingerprint() == fingerprint
    assert dm.frequencies() == frequencies


# --- Invariants that must hold for any delta-matroid ---


def test_fingerprint_adds_up_to_number_of_feasible_sets() -> None:
    dm = DeltaMatroid("D", field=2, matrix=matrix([[1, 1, 0], [1, 0, 1], [0, 1, 1]]))

    assert sum(dm.fingerprint()) == len(dm.feasible_family)


def test_frequencies_add_up_to_total_size() -> None:
    # Counting element memberships two ways: by element, and by size of each feasible set
    dm = DeltaMatroid("D", field=2, matrix=matrix([[1, 1, 0], [1, 0, 1], [0, 1, 1]]))

    by_size = sum(k * count for k, count in enumerate(dm.fingerprint()))
    assert sum(dm.frequencies()) == by_size
