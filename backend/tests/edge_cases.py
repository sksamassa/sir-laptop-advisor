"""Branch coverage for domain validation, errors, and explanation variants.

These cases exist to exercise the paths that the happy-path checks never touch:
rejected inputs, threshold validation, registry corruption, and explanation
branches. Each assertion is a real behaviour the service relies on.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from laptop_dss.catalog.domain.criteria import (
    CriteriaRegistry,
    Criterion,
    RegistryError,
    load_registry,
)
from laptop_dss.catalog.domain.device import CriterionValues, DeviceModel
from laptop_dss.profiles.domain.weights import WeightSet
from laptop_dss.ranking.domain import explanation
from laptop_dss.ranking.domain.normalization import normalize
from laptop_dss.ranking.domain.preference import preference, thresholds
from laptop_dss.ranking.domain.sir_reference import (
    CriterionContribution,
    SirScore,
    rank,
)
from laptop_dss.shared.domain import errors
from laptop_dss.shared.domain.ids import FixedClock, SystemClock, new_id
from laptop_dss.shared.domain.money import format_rub, rubles


def _model(**overrides: object) -> DeviceModel:
    base = {
        "id": uuid.uuid4(),
        "brand": "Brand",
        "model_name": "Model",
        "os": "windows",
        "form_factor": "laptop",
        "values": CriterionValues(
            price=50_000_00,
            performance=5000,
            memory=16,
            weight=1400,
            battery=600,
            screen=7.5,
            warranty=12,
        ),
    }
    base.update(overrides)
    return DeviceModel(**base)  # type: ignore[arg-type]


def _score(model_id: str, contributions: dict[str, float]) -> SirScore:
    return SirScore(
        model_id=model_id,
        phi_plus=sum(value for value in contributions.values() if value > 0),
        phi_minus=sum(value for value in contributions.values() if value < 0),
        net_score=sum(contributions.values()),
        contributions={
            key: CriterionContribution(normalized=0.5, contribution=value)
            for key, value in contributions.items()
        },
    )


def run_edge_cases() -> None:
    registry = load_registry()

    # ---- money and identifiers -------------------------------------------
    assert str(rubles(6499000)) == "64990"
    assert format_rub(6499000) == "64 990 \u20BD"
    assert format_rub(6499050).endswith(",50 \u20BD")
    assert isinstance(new_id(), uuid.UUID)
    assert SystemClock().now().tzinfo is UTC
    fixed = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    assert fixed.now().year == 2026

    # ---- error hierarchy -------------------------------------------------
    for error_cls, status in (
        (errors.ValidationError, 400),
        (errors.InvalidWeights, 400),
        (errors.NotFound, 404),
        (errors.Forbidden, 403),
        (errors.Unauthorized, 401),
        (errors.Conflict, 409),
    ):
        error = error_cls("сообщение", field="value")
        payload = error.to_payload()
        assert error.status_code == status
        assert payload["error"]["message"] == "сообщение"
        assert payload["error"]["details"] == {"field": "value"}

    # ---- device validation ----------------------------------------------
    for bad in (
        {"brand": ""},
        {"model_name": ""},
        {"status": "draft"},
    ):
        try:
            _model(**bad)
        except errors.ValidationError:
            pass
        else:
            raise AssertionError(f"expected rejection for {bad}")

    try:
        _model(values=CriterionValues(price=0, performance=1, memory=8, weight=1000,
                                      battery=300, screen=5.0, warranty=12))
    except errors.ValidationError:
        pass
    else:
        raise AssertionError("non-positive price must be rejected")

    device = _model()
    assert device.is_complete()
    device.validate_vocabularies(registry)
    for bad_os, bad_form in (("amiga", "laptop"), ("windows", "toaster")):
        broken = _model(os=bad_os, form_factor=bad_form)
        try:
            broken.validate_vocabularies(registry)
        except errors.ValidationError:
            pass
        else:
            raise AssertionError("unknown vocabulary value must be rejected")

    # ---- criteria registry ----------------------------------------------
    assert registry.by_key("price").direction == "min"
    try:
        registry.by_key("nope")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown criterion must raise")
    assert set(registry.storage_fields().values()) >= {"price_minor", "cpu_score"}
    try:
        registry.validate_weights_keys({"price": 1.0})
    except RegistryError:
        pass
    else:
        raise AssertionError("incomplete weights must be rejected")
    registry.validate_weights_keys({key: 1 / 7 for key in registry.keys})

    raw = json.loads((Path(registry_probe_path())).read_text(encoding="utf-8"))

    def broken_registry(mutate) -> None:  # noqa: ANN001
        payload = json.loads(json.dumps(raw))
        mutate(payload)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
            path = Path(fh.name)
        try:
            load_registry(path)
        except (RegistryError, KeyError, TypeError):
            return
        finally:
            path.unlink(missing_ok=True)
        raise AssertionError("corrupted registry must be rejected")

    broken_registry(lambda data: data["criteria"].pop())
    broken_registry(lambda data: data["criteria"][0].update(direction="sideways"))
    broken_registry(lambda data: data["criteria"][0].update(indifference_threshold=0.9,
                                                             preference_threshold=0.1))
    broken_registry(lambda data: data["criteria"][0].update(order=9))

    # ---- weights ---------------------------------------------------------
    keys = registry.keys
    for bad in (
        {"price": 1.0},
        {**{key: 0.1 for key in keys}, "extra": 0.1},
    ):
        try:
            WeightSet.from_user_input(bad, keys)
        except errors.InvalidWeights:
            pass
        else:
            raise AssertionError("bad weight shape must be rejected")
    try:
        WeightSet.from_user_input({**{key: 0.0 for key in keys}}, keys)
    except errors.InvalidWeights:
        pass
    else:
        raise AssertionError("all-zero weights must be rejected")
    try:
        WeightSet.from_user_input({**{key: 1 / 7 for key in keys}, "price": -0.1}, keys)
    except errors.InvalidWeights:
        pass
    else:
        raise AssertionError("negative weight must be rejected")
    try:
        WeightSet.from_user_input({"price": "abc", **{k: 0.1 for k in keys if k != "price"}}, keys)
    except errors.InvalidWeights:
        pass
    else:
        raise AssertionError("non-numeric weight must be rejected")
    normalized = WeightSet.from_user_input({key: 1 / 7 for key in keys}, keys)
    normalized.assert_normalized()

    # ---- preference and normalization -----------------------------------
    assert thresholds(registry)["price"] == (0.0, 1.0)
    try:
        preference(0.5, q=0.7, p=0.7)
    except ValueError:
        pass
    else:
        raise AssertionError("q >= p must raise")
    empty = normalize([], registry)
    assert empty.model_ids == ()
    singleton = normalize([_model()], registry)
    assert all(value == 0.0 for value in singleton.values["price"])

    # ---- SIR reference degenerate cases ---------------------------------
    weights = {key: 1 / 7 for key in keys}
    assert rank([], weights, registry).ordered == ()
    single = rank([_model()], weights, registry)
    assert len(single.ordered) == 1

    # ---- explanation branches -------------------------------------------
    plain = _score(str(uuid.uuid4()), {"price": -0.2, "performance": 0.4})
    text = explanation.build_reason(plain, registry, "Model X", rank=1, total=5)
    assert "Model X" in text and "производительность" in text
    runner_up = explanation.build_reason(plain, registry, "Model X", rank=2, total=5)
    assert "2-е место" in runner_up

    neutral = _score(str(uuid.uuid4()), {key: 0.0 for key in keys})
    neutral_text = explanation.build_reason(neutral, registry, "Model Y", rank=1, total=1)
    assert "равны" in neutral_text

    top = _score("a", {"price": -0.1, "performance": 0.5})
    other = _score("b", {"price": 0.2, "performance": 0.1})
    gap = explanation.gap_to_top(top, other, registry)
    assert gap["gap"] == round(other.net_score - top.net_score, 6)
    assert isinstance(gap["decisive_criteria"], list)

    payload = explanation.contribution_payload(plain.contributions)
    assert set(payload) == set(plain.contributions)


def registry_probe_path() -> str:
    import os

    return os.environ.get("CRITERIA_PATH") or str(
        Path(__file__).resolve().parents[2] / "shared" / "criteria.json"
    )
