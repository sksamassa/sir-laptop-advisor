"""Adapter that loads the criteria registry from disk.

All file and environment access lives here; the domain only receives the parsed
mapping through ``parse_registry`` (constitution, Principle II).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from laptop_dss.catalog.domain.criteria import CriteriaRegistry, RegistryError, parse_registry

_REPO_ROOT = Path(__file__).resolve().parents[5]
_registry: CriteriaRegistry | None = None


def _default_path() -> Path:
    override = os.environ.get("CRITERIA_PATH")
    return Path(override) if override else _REPO_ROOT / "shared" / "criteria.json"


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
    registry = parse_registry(raw)
    if path is None:
        _registry = registry
    return registry


def reset_registry_cache() -> None:
    """Test helper: drop the process cache."""
    global _registry
    _registry = None
