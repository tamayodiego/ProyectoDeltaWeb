"""Golden master: the Python port must reproduce the Java desktop app (Phase 1, task 5).

Reads every case in ``tests/golden/*.txt`` (see its README), builds the delta-matroid from
the same matrix, and compares the number of feasible sets, the fingerprint (huella) and
the frequency table.

Cases skipped on purpose:
- ``SIM`` over GF(3) and ``ANTI`` over GF(2): the web version only accepts symmetric
  matrices over GF(2) and skew-symmetric ones over GF(3) (the Java app accepted any
  combination). Zero matrices fit both kinds, so they are always checked.
- The two ``sha`` fields depend on the internal order of Java's lists; not compared yet.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from deltaweb.domain.deltamatroid import DeltaMatroid

GOLDEN_DIR = Path(__file__).parent / "golden"

LINE = re.compile(
    r"n=(?P<n>\d+) tipo=(?P<kind>SIM|ANTI) campo=GF(?P<field>[23]) semilla=(?P<seed>\d+)"
    r" \| matriz=(?P<matrix>[-0-9,;]+)"
    r" \| toString=.*?"
    r" \| familia=(?P<count>\d+) sha=\w+"
    r" \| huella=\((?P<fingerprint>[0-9,]+)\)"
    r" \| frecuencias=\[(?P<frequencies>[0-9, ]+)\]"
    r" \| determinantes sha=\w+$"
)


@dataclass(frozen=True)
class GoldenCase:
    key: str
    kind: str
    field: int
    matrix: tuple[tuple[int, ...], ...]
    count: int
    fingerprint: tuple[int, ...]
    frequencies: tuple[int, ...]

    @property
    def is_zero(self) -> bool:
        return not any(any(row) for row in self.matrix)

    @property
    def supported(self) -> bool:
        expected = "SIM" if self.field == 2 else "ANTI"
        return self.kind == expected or self.is_zero


def parse(line: str) -> GoldenCase:
    match = LINE.match(line)
    if match is None:
        raise ValueError(f"Unrecognized golden line: {line!r}")
    g = match.groupdict()
    return GoldenCase(
        key=line.split(" | ")[0],
        kind=g["kind"],
        field=int(g["field"]),
        matrix=tuple(tuple(int(x) for x in row.split(",")) for row in g["matrix"].split(";")),
        count=int(g["count"]),
        fingerprint=tuple(int(x) for x in g["fingerprint"].split(",")),
        frequencies=tuple(int(x) for x in g["frequencies"].split(",")),
    )


def load_cases() -> list[GoldenCase]:
    cases = []
    for path in sorted(GOLDEN_DIR.glob("*.txt")):
        cases += [parse(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return cases


ALL_CASES = load_cases()


def test_golden_files_are_complete() -> None:
    # 132 cases in group A (n = 1..11) + 32 in group B (n = 12..15)
    assert len(ALL_CASES) == 164


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(c, marks=[] if c.supported else pytest.mark.skip(reason="field/kind"))
        for c in ALL_CASES
    ],
    ids=[c.key for c in ALL_CASES],
)
def test_matches_java(case: GoldenCase) -> None:
    dm = DeltaMatroid(
        "golden",
        field=case.field,  # type: ignore[arg-type]
        matrix=np.array(case.matrix, dtype=np.int64),
    )

    assert len(dm.feasible_family) == case.count
    assert dm.fingerprint == case.fingerprint
    assert tuple(dm.frequencies) == case.frequencies
