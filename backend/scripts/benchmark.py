"""Time how long building a DeltaMatroid from a matrix takes, for n = 8..15.

Run from backend/:  uv run python scripts/benchmark.py

Each size runs a few random valid matrices (symmetric over GF(2), skew-symmetric over GF(3))
and reports the median time. The roadmap target is n = 15 in under 1.5 s on one core.
"""

import statistics
import time

import numpy as np

from deltaweb.domain.deltamatroid import DeltaMatroid

SIZES = range(8, 16)
REPEATS = 3
TARGET_SECONDS = 1.5


def random_matrix(n: int, field: int, rng: np.random.Generator) -> np.ndarray:
    if field == 2:  # symmetric 0/1
        upper = np.triu(rng.integers(0, 2, size=(n, n)))
        return (upper + np.triu(upper, 1).T).astype(np.int64)
    upper = np.triu(rng.integers(-1, 2, size=(n, n)), 1)  # skew-symmetric -1/0/1
    return (upper - upper.T).astype(np.int64)


def median_seconds(n: int, field: int, rng: np.random.Generator) -> float:
    times = []
    for _ in range(REPEATS):
        m = random_matrix(n, field, rng)
        start = time.perf_counter()
        DeltaMatroid("bench", field=field, matrix=m)  # type: ignore[arg-type]
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def main() -> None:
    rng = np.random.default_rng(2026)
    print(f"{'n':>3} {'subsets':>8} {'GF(2) sym':>10} {'GF(3) skew':>11}")
    for n in SIZES:
        gf2 = median_seconds(n, 2, rng)
        gf3 = median_seconds(n, 3, rng)
        print(f"{n:>3} {2**n:>8} {gf2:>9.3f}s {gf3:>10.3f}s")
    verdict = "OK" if max(gf2, gf3) < TARGET_SECONDS else "TOO SLOW: optimize"
    print(f"\nn = 15 target < {TARGET_SECONDS} s: {verdict}")


if __name__ == "__main__":
    main()
