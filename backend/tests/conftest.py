"""Shared test fixtures: the criteria registry and seeded model factories."""

from __future__ import annotations

import pytest

from laptop_dss.catalog.domain.criteria import load_registry, reset_registry_cache
from tests.helpers import make_model, random_models, uniform_weights  # noqa: F401


@pytest.fixture(scope="session")
def registry():  # noqa: ANN201 - pytest fixture
    reset_registry_cache()
    return load_registry()
