"""Adapter that loads the criteria registry from disk.

All file and environment access lives here; the domain only receives the parsed
mapping through ``parse_registry`` (constitution, Principle II).

Two locations are supported:

- the packaged copy next to the domain module (always present in a container image),
- the repository's ``shared/criteria.json`` (developer checkouts).

``CRITERIA_PATH`` overrides both. The first existing candidate wins, so the API
works regardless of whether the working directory is the repository root.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from laptop_dss.catalog.domain.criteria import CriteriaRegistry, RegistryError, parse_registry

_PACKAGE_PATH = Path(__file__).resolve().parents[1] / "domain" / "criteria.json"
_REPO_PATH = Path(__file__).resolve().parents[5] / "shared" / "criteria.json"
_registry: CriteriaRegistry | None = None


def _candidates() -> tuple[Path, ...]:
    override = os.environ.get("CRITERIA_PATH")
    if override:
        return (Path(override),)
    return (_PACKAGE_PATH, _REPO_PATH)


def _default_path() -> Path:
    for candidate in _candidates():
        if candidate.exists():
            return candidate
    tried = ", ".join(str(candidate) for candidate in _candidates())
    raise RegistryError(f"criteria registry not found; looked in: {tried}")


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
