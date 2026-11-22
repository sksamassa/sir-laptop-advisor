"""Reference SIR kernel: normalization, preference regions, degenerate inputs."""

from __future__ import annotations

import pytest
from tests.conftest import make_model

from laptop_dss.catalog.domain.criteria import RegistryError
from laptop_dss.ranking.domain.normalization import normalize
from laptop_dss.ranking.domain.preference import preference
from laptop_dss.ranking.domain.sir_reference import rank


def test_normalization_respects_direction(registry) -> None:
    models = [
        make_model("A a", price=100_00, battery=300),
        make_model("B b", price=200_00, battery=900),
    ]
    matrix = normalize(models, registry)
    # price is minimized: the cheaper model normalizes to 1.0
    assert matrix.values["price"][0] == pytest.approx(1.0)
    assert matrix.values["price"][1] == pytest.approx(0.0)
    # battery is maximized
    assert matrix.values["battery"][0] == pytest.approx(0.0)
    assert matrix.values["battery"][1] == pytest.approx(1.0)


def test_zero_range_criterion_is_neutral(registry) -> None:
    models = [make_model("A a"), make_model("B b"), make_model("C c")]
    matrix = normalize(models, registry)
    for key in registry.keys:
        assert matrix.values[key] == (0.0, 0.0, 0.0)


def test_preference_regions() -> None:
    assert preference(0.0, q=0.0, p=1.0) == 0.0
    assert preference(0.5, q=0.0, p=1.0) == pytest.approx(0.5)
    assert preference(1.0, q=0.0, p=1.0) == 1.0
    assert preference(0.1, q=0.2, p=0.6) == 0.0
    assert preference(0.4, q=0.2, p=0.6) == pytest.approx(0.5)
    assert preference(0.9, q=0.2, p=0.6) == 1.0
    with pytest.raises(ValueError):
        preference(0.5, q=0.6, p=0.2)


def test_single_model_rank_is_defined(registry) -> None:
    result = rank(
        [make_model("A a")],
        {"price": 1.0, **{k: 0.0 for k in registry.keys if k != "price"}},
        registry,
    )
    assert len(result.ordered) == 1
    assert result.ordered[0].net_score == pytest.approx(0.0)
    assert result.ordered[0].phi_plus == pytest.approx(0.0)


def test_identical_alternatives_tie_break_by_id(registry) -> None:
    models = [make_model(f"S{i} same") for i in range(3)]
    weights = {key: 1.0 / len(registry.keys) for key in registry.keys}
    result = rank(models, weights, registry)
    assert [s.model_id for s in result.ordered] == sorted(str(m.id) for m in models)
    assert all(s.net_score == pytest.approx(0.0) for s in result.ordered)


def test_contributions_sum_to_net_score(registry) -> None:
    models = [
        make_model("A a", price=100_00),
        make_model("B b", price=150_00),
        make_model("C c", price=200_00),
    ]
    weights = {key: 1.0 / len(registry.keys) for key in registry.keys}
    result = rank(models, weights, registry)
    for score in result.ordered:
        total = sum(c.contribution for c in score.contributions.values())
        assert total == pytest.approx(score.net_score, abs=1e-9)


def test_weights_must_cover_every_criterion(registry) -> None:
    with pytest.raises(RegistryError):
        rank([make_model("A a")], {"price": 1.0}, registry)
