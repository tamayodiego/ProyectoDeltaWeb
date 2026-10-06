"""Generate delta-matroids outside the API process.

Building a delta-matroid walks the 2^n principal submatrices: pure CPU work. Running it in
the request thread would hold Python's GIL and slow every other request, so it goes to a
small pool of worker processes. The worker returns plain data (lists and ints), which is
cheap and safe to send back between processes.
"""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Literal

import numpy as np

from deltaweb.domain.deltamatroid import DeltaMatroid


@dataclass(frozen=True)
class GenerationResult:
    ground_set: list[str]
    feasible: list[int]  # bitmasks: bit k set <=> ground_set[k] is in the feasible set
    fingerprint: list[int]
    frequencies: list[int]


def generate(
    matrix: list[list[int]], field: Literal[2, 3], labels: list[str] | None
) -> GenerationResult:
    """Runs inside a worker process. Raises InvalidMatrixError for invalid input."""
    dm = DeltaMatroid("generated", field=field, matrix=np.array(matrix, dtype=np.int64))
    if labels is not None:
        dm = dm.relabel(dict(zip(dm.ground_set, labels, strict=True)))
    return GenerationResult(
        ground_set=list(dm.ground_set),
        feasible=[int(mask) for mask in dm.feasible_family],
        fingerprint=list(dm.fingerprint),
        frequencies=list(dm.frequencies),
    )


def create_executor(workers: int) -> ProcessPoolExecutor:
    # "spawn" starts clean processes on every OS (fork is unsafe once threads exist)
    return ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
