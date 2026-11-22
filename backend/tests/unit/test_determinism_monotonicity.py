"""Determinism and monotonicity properties required by the constitution."""

from __future__ import annotations

import pytest

from laptop_dss.ranking.adapters import vectorized_sir
from laptop_dss.ranking.domain import sir_reference
from tests.conftest import make_model, random_models, uniform_weights


@pytest.mark.parametrize("engine", [sir_reference.rank, vectorized_sir.rank])
def test_repeated_ranking_is_identical(engine, registry) -> None:  # noqa: ANN001
    models = random_models(7, 42)
    weights = uniform_weights(registry)
    first = engine(models, weights, registry)
    second = engine(models, weights, registry)
    assert [(s.model_id, s.net_score) for s in first.ordered] == [
        (s.model_id, s.net_score) for s in second.ordered
    ]


@pytest.mark.parametrize("seed", [7, 8, 9])
def test_improving_one_criterion_never_lowers_rank(registry, seed: int) -> None:  # noqa: ANN001
    models = random_models(6, seed)
    weights = uniform_weights(registry)
    baseline = vectorized_sir.rank(models, weights, registry)
    baseline_rank = {s.model_id: index for index, s in enumerate(baseline.ordered)}

    worst = baseline.ordered[-1].model_id
    target = next(m for m in models if str(m.id) == worst)
    improved_values = target.values.__class__(
        price=target.values.price,
        performance=target.values.performance,
        memory=target.values.memory,
        weight=target.values.weight,
        battery=min(target.values.battery + 600, 2000),
        screen=target.values.screen,
        warranty=target.values.warranty,
    )
    improved = [m if m.id != target.id else m.__class__(
        id=m.id, brand=m.brand, model_name=m.model_name, os=m.os,
        form_factor=m.form_factor, values=improved_values, status=m.status,
    ) for m in models]

    after = vectorized_sir.rank(improved, weights, registry)
    after_rank = {s.model_id: index for index, s in enumerate(after.ordered)}
    assert after_rank[worst] <= baseline_rank[worst]
