"""SC-004: ranking 5 000 models must stay well under the 3 s user-facing budget.

Run directly (no pytest needed):

    python tests/perf/test_rank_5000.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "tests")]

from laptop_dss.catalog.adapters.criteria_source import load_registry  # noqa: E402
from laptop_dss.ranking.adapters import vectorized_sir  # noqa: E402
from helpers import random_models, uniform_weights  # noqa: E402

MODEL_COUNT = 5_000
BUDGET_SECONDS = 0.3  # plan target: ranking p95 <= 300 ms


def test_rank_5000_models_within_budget() -> None:
    registry = load_registry()
    weights = uniform_weights(registry)
    models = random_models(MODEL_COUNT, 2026)

    timings: list[float] = []
    for _ in range(5):
        started = time.perf_counter()
        result = vectorized_sir.rank(models, weights, registry)
        timings.append(time.perf_counter() - started)

    assert len(result.ordered) == MODEL_COUNT
    p95 = statistics.quantiles(timings, n=20)[-1]
    assert p95 < BUDGET_SECONDS, f"p95={p95:.3f}s exceeds {BUDGET_SECONDS}s"


def main() -> int:
    registry = load_registry()
    weights = uniform_weights(registry)
    started = time.perf_counter()
    models = random_models(MODEL_COUNT, 2026)
    build = time.perf_counter() - started

    timings: list[float] = []
    for _ in range(5):
        started = time.perf_counter()
        result = vectorized_sir.rank(models, weights, registry)
        timings.append(time.perf_counter() - started)

    print(f"models: {MODEL_COUNT} (built in {build * 1000:.0f} ms)")
    print(f"ranking runs: {[round(t * 1000) for t in timings]} ms")
    print(f"median: {statistics.median(timings) * 1000:.1f} ms")
    print(f"p95:    {statistics.quantiles(timings, n=20)[-1] * 1000:.1f} ms")
    print(f"top: {result.ordered[0].model_id[:8]} score={result.ordered[0].net_score:.4f}")
    ok = statistics.quantiles(timings, n=20)[-1] < BUDGET_SECONDS
    print("PASS" if ok else "FAIL: above the 300 ms budget")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
