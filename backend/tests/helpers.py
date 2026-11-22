"""Model factories shared by pytest fixtures and the stdlib check runner."""

from __future__ import annotations

import random
import uuid

from laptop_dss.catalog.domain.device import CriterionValues, DeviceModel


def make_model(
    name: str,
    *,
    price: int = 60_000_00,
    performance: int = 5000,
    memory: int = 16,
    weight: int = 1400,
    battery: int = 600,
    screen: float = 7.0,
    warranty: int = 12,
    os: str = "windows",
    form_factor: str = "laptop",
) -> DeviceModel:
    return DeviceModel(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, name),
        brand=name.split()[0],
        model_name=name,
        os=os,
        form_factor=form_factor,
        values=CriterionValues(
            price=price,
            performance=performance,
            memory=memory,
            weight=weight,
            battery=battery,
            screen=screen,
            warranty=warranty,
        ),
    )


def random_models(count: int, seed: int) -> list[DeviceModel]:
    rng = random.Random(seed)
    return [
        make_model(
            f"Brand{i} Model{i}",
            price=rng.randint(40_000, 200_000) * 100,
            performance=rng.randint(1000, 12_000),
            memory=rng.choice([8, 16, 32, 64]),
            weight=rng.randint(900, 2600),
            battery=rng.randint(240, 1200),
            screen=round(rng.uniform(5.0, 9.8), 1),
            warranty=rng.choice([6, 12, 24, 36]),
        )
        for i in range(count)
    ]


def uniform_weights(registry) -> dict[str, float]:  # noqa: ANN001
    return {key: 1.0 / len(registry.keys) for key in registry.keys}
