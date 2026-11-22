"""Shared test fixtures: the criteria registry and seeded model factories."""

from __future__ import annotations

import pytest

from laptop_dss.catalog.adapters.criteria_source import load_registry, reset_registry_cache
from tests.helpers import make_model, random_models, uniform_weights  # noqa: F401


@pytest.fixture(scope="session")
def registry():
    reset_registry_cache()
    return load_registry()
