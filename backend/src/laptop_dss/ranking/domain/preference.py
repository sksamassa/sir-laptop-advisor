"""Per-criterion preference function for SIR.

``p(d)`` is 0 up to the indifference threshold ``q``, rises linearly between
``q`` and ``p``, and is 1 at or above ``p``. With the defaults ``q=0, p=1`` this
is the linear preference used by the prototype notebook.
"""

from __future__ import annotations

from laptop_dss.catalog.domain.criteria import CriteriaRegistry


def preference(d: float, *, q: float, p: float) -> float:
    if not 0.0 <= q < p <= 1.0:
        raise ValueError(f"require 0 <= q < p <= 1, got q={q}, p={p}")
    if d <= q:
        return 0.0
    if d >= p:
        return 1.0
    return (d - q) / (p - q)


def thresholds(registry: CriteriaRegistry) -> dict[str, tuple[float, float]]:
    return {c.key: (c.indifference_threshold, c.preference_threshold) for c in registry.criteria}
