"""Min-max normalization with direction handling.

Values are mapped to ``[0, 1]`` so that larger is always better. When a
criterion has no spread across the candidate set, every value becomes 0.0 and
the criterion contributes no differences -- it cannot destabilize the ranking.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from laptop_dss.catalog.domain.criteria import CriteriaRegistry
from laptop_dss.catalog.domain.device import DeviceModel


@dataclass(frozen=True, slots=True)
class NormalizedMatrix:
    """Normalized values per criterion, aligned to ``model_ids``."""

    keys: tuple[str, ...]
    model_ids: tuple[str, ...]
    values: dict[str, tuple[float, ...]]

    def row(self, index: int) -> dict[str, float]:
        return {key: self.values[key][index] for key in self.keys}


def normalize(models: Sequence[DeviceModel], registry: CriteriaRegistry) -> NormalizedMatrix:
    if not models:
        return NormalizedMatrix(
            keys=registry.keys, model_ids=(), values={k: () for k in registry.keys}
        )

    model_ids = tuple(str(m.id) for m in models)
    normalized: dict[str, tuple[float, ...]] = {}
    for criterion in registry.criteria:
        raw = [m.values.as_dict()[criterion.key] for m in models]
        lo, hi = min(raw), max(raw)
        if hi == lo:
            normalized[criterion.key] = tuple(0.0 for _ in raw)
            continue
        span = hi - lo
        if criterion.direction == "max":
            normalized[criterion.key] = tuple((value - lo) / span for value in raw)
        else:
            normalized[criterion.key] = tuple((hi - value) / span for value in raw)
    return NormalizedMatrix(keys=registry.keys, model_ids=model_ids, values=normalized)
