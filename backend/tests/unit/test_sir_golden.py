"""Golden ranking: a dataset whose expected scores are computed by hand."""

from __future__ import annotations

import pytest
from tests.conftest import make_model

from laptop_dss.ranking.adapters import vectorized_sir
from laptop_dss.ranking.domain import sir_reference


def _price_only_weights(registry) -> dict[str, float]:
    return {key: (1.0 if key == "price" else 0.0) for key in registry.keys}


def test_golden_price_ranking(registry) -> None:
    # Only price varies; min-max on three values 10 000 / 20 000 / 30 000 RUB
    # yields normalized 1.0 / 0.5 / 0.0, and with one active criterion
    # net(a) = 3*v(a) - sum(v) => 1.5 / 0.0 / -1.5.
    models = [
        make_model("A a", price=100_00),
        make_model("B b", price=200_00),
        make_model("C c", price=300_00),
    ]
    weights = _price_only_weights(registry)

    for engine in (sir_reference.rank, vectorized_sir.rank):
        result = engine(models, weights, registry)
        assert [s.net_score for s in result.ordered] == pytest.approx([1.5, 0.0, -1.5])
        assert result.ordered[0].model_id == str(models[0].id)
        assert result.ordered[0].contributions["price"].normalized == pytest.approx(1.0)


def test_golden_second_criterion_flips_memory_order(registry) -> None:
    # Memory dominates; more RAM must rank first even at a higher price.
    models = [
        make_model("A a", price=100_00, memory=8),
        make_model("B b", price=200_00, memory=32),
    ]
    weights = {key: (1.0 if key == "memory" else 0.0) for key in registry.keys}
    result = vectorized_sir.rank(models, weights, registry)
    assert result.ordered[0].model_id == str(models[1].id)
    assert result.ordered[0].net_score == pytest.approx(1.0)
