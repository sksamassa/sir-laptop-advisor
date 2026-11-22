"""Criteria registry: the immutable definition of the seven SIR criteria.

This module is pure domain: it validates a parsed mapping and exposes value
objects. Reading the JSON file, caching, and environment lookup live in
``catalog/adapters/criteria_source.py`` so the domain performs no I/O
(constitution, Principle II).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

Direction = Literal["min", "max"]
CRITERIA_COUNT = 7


class RegistryError(ValueError):
    """Raised when the criteria registry violates its contract."""


@dataclass(frozen=True, slots=True)
class Criterion:
    key: str
    order: int
    label_ru: str
    direction: Direction
    unit: str
    storage_field: str
    indifference_threshold: float
    preference_threshold: float
    display_decimals: int

    def validate(self) -> None:
        if self.direction not in ("min", "max"):
            raise RegistryError(f"criterion {self.key}: direction must be min or max")
        if not 0.0 <= self.indifference_threshold < self.preference_threshold <= 1.0:
            raise RegistryError(
                f"criterion {self.key}: require 0 <= q < p <= 1, "
                f"got q={self.indifference_threshold}, p={self.preference_threshold}"
            )
        if self.order < 1 or self.order > CRITERIA_COUNT:
            raise RegistryError(f"criterion {self.key}: order must be 1..{CRITERIA_COUNT}")


@dataclass(frozen=True, slots=True)
class CriteriaRegistry:
    version: str
    criteria: tuple[Criterion, ...]
    goals: tuple[str, ...]
    operating_systems: tuple[str, ...]
    form_factors: tuple[str, ...]
    content_hash: str

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(c.key for c in self.criteria)

    def by_key(self, key: str) -> Criterion:
        for criterion in self.criteria:
            if criterion.key == key:
                return criterion
        raise KeyError(key)

    def storage_fields(self) -> dict[str, str]:
        return {c.key: c.storage_field for c in self.criteria}

    def validate_weights_keys(self, weights: dict[str, float]) -> None:
        missing = set(self.keys) - set(weights)
        extra = set(weights) - set(self.keys)
        if missing or extra:
            raise RegistryError(
                f"weights must cover exactly {self.keys}; missing={missing}, extra={extra}"
            )


def parse_registry(raw: dict[str, Any]) -> CriteriaRegistry:
    """Validate a parsed registry mapping and build the immutable registry."""
    items = [Criterion(**item) for item in raw["criteria"]]
    if len(items) != CRITERIA_COUNT:
        raise RegistryError(f"expected exactly {CRITERIA_COUNT} criteria, got {len(items)}")
    keys = [c.key for c in items]
    if len(set(keys)) != len(keys):
        raise RegistryError("criteria keys must be unique")
    if sorted(c.order for c in items) != list(range(1, CRITERIA_COUNT + 1)):
        raise RegistryError("criteria order values must cover 1..7 exactly once")
    for criterion in items:
        criterion.validate()
    ordered = tuple(sorted(items, key=lambda c: c.order))
    vocab = raw["vocabularies"]
    payload = json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return CriteriaRegistry(
        version=str(raw["version"]),
        criteria=ordered,
        goals=tuple(vocab["goals"]),
        operating_systems=tuple(vocab["os"]),
        form_factors=tuple(vocab["form_factor"]),
        content_hash="sha256:" + hashlib.sha256(payload).hexdigest(),
    )
