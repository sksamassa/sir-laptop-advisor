"""The vectorized engine must equal the reference definition, not approximate it."""

from __future__ import annotations

import dataclasses

import pytest

from laptop_dss.catalog.domain.criteria import CriteriaRegistry
from laptop_dss.catalog.adapters.criteria_source import load_registry
from laptop_dss.ranking.adapters import vectorized_sir
from laptop_dss.ranking.domain import sir_reference
from tests.conftest import random_models, uniform_weights


def _thresholded_registry(q: float, p: float) -> CriteriaRegistry:
    base = load_registry()
    criteria = tuple(
        dataclasses.replace(c, indifference_threshold=q, preference_threshold=p)
        for c in base.criteria
    )
    return dataclasses.replace(base, criteria=criteria)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("count", [3, 5, 8])
def test_engines_agree_on_random_matrices(registry, seed: int, count: int) -> None:  # noqa: ANN001
    models = random_models(count, seed)
    weights = uniform_weights(registry)
    reference = sir_reference.rank(models, weights, registry)
    vectorized = vectorized_sir.rank(models, weights, registry)

    assert [s.model_id for s in reference.ordered] == [s.model_id for s in vectorized.ordered]
    for left, right in zip(reference.ordered, vectorized.ordered, strict=True):
        assert left.net_score == pytest.approx(right.net_score, abs=1e-9)
        assert left.phi_plus == pytest.approx(right.phi_plus, abs=1e-9)
        assert left.phi_minus == pytest.approx(right.phi_minus, abs=1e-9)
        for key in registry.keys:
            assert left.contributions[key].contribution == pytest.approx(
                right.contributions[key].contribution, abs=1e-9
            )


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_engines_agree_with_thresholds(registry, seed: int) -> None:  # noqa: ANN001
    models = random_models(6, seed)
    weights = {key: (index + 1) / 28 for index, key in enumerate(registry.keys)}
    tuned = _thresholded_registry(q=0.1, p=0.4)

    reference = sir_reference.rank(models, weights, tuned)
    vectorized = vectorized_sir.rank(models, weights, tuned)

    assert [s.model_id for s in reference.ordered] == [s.model_id for s in vectorized.ordered]
    for left, right in zip(reference.ordered, vectorized.ordered, strict=True):
        assert left.net_score == pytest.approx(right.net_score, abs=1e-9)


def test_engines_agree_on_degenerate_inputs(registry) -> None:  # noqa: ANN001
    weights = uniform_weights(registry)
    models = [random_models(2, 21)[0]]
    assert [s.model_id for s in sir_reference.rank(models, weights, registry).ordered] == [
        s.model_id for s in vectorized_sir.rank(models, weights, registry).ordered
    ]
    assert vectorized_sir.rank([], weights, registry).ordered == ()
