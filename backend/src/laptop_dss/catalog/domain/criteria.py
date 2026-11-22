"""Criteria registry: the single definition of the seven SIR criteria.

The JSON file is the source of truth; this loader validates it and exposes an
immutable registry whose content hash is stored with every ranking so a result
can be tied to the exact criteria definition that produced it.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Direction = Literal["min", "max"]
CRITERIA_COUNT = 7
_REPO_ROOT = Path(__file__).resolve().parents[5]


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
            raise RegistryError(f"weights must cover exactly {self.keys}; missing={missing}, extra={extra}")


def _default_path() -> Path:
    override = os.environ.get("CRITERIA_PATH")
    return Path(override) if override else _REPO_ROOT / "shared" / "criteria.json"


def _parse(raw: dict[str, Any]) -> CriteriaRegistry:
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


_registry: CriteriaRegistry | None = None


def load_registry(path: Path | None = None) -> CriteriaRegistry:
    """Load and validate the registry (cached per process)."""
    global _registry
    if path is None and _registry is not None:
        return _registry
    target = path or _default_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"criteria registry not found at {target}") from exc
    registry = _parse(raw)
    if path is None:
        _registry = registry
    return registry


def reset_registry_cache() -> None:
    """Test helper: drop the process cache."""
    global _registry
    _registry = None
