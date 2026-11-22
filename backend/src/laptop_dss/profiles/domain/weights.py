"""Profiles domain: weight validation and normalization (Principle IV)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from laptop_dss.shared.domain.errors import InvalidWeights

INPUT_TOLERANCE = 0.005  # spec FR-003: 0.5% on the user-entered total
INTERNAL_TOLERANCE = 1e-6  # constitution Principle IV


@dataclass(frozen=True, slots=True)
class WeightSet:
    values: Mapping[str, float]

    @classmethod
    def from_user_input(cls, raw: Mapping[str, float], keys: tuple[str, ...]) -> WeightSet:
        if set(raw) != set(keys):
            raise InvalidWeights("Веса должны быть заданы для всех семи критериев")
        numeric: dict[str, float] = {}
        for key in keys:
            try:
                value = float(raw[key])
            except (TypeError, ValueError) as exc:
                raise InvalidWeights(f"Вес критерия {key} должен быть числом") from exc
            if value < 0:
                raise InvalidWeights("Веса не могут быть отрицательными")
            numeric[key] = value
        total = sum(numeric.values())
        if total <= 0:
            raise InvalidWeights("Хотя бы один вес должен быть больше нуля")
        if abs(total - 1.0) > INPUT_TOLERANCE:
            raise InvalidWeights(
                "Сумма весов должна быть 100% (допуск 0,5%)",
                sum=round(total, 6),
            )
        return cls({key: numeric[key] / total for key in keys})

    @property
    def total(self) -> float:
        return sum(self.values.values())

    def assert_normalized(self) -> None:
        if abs(self.total - 1.0) > INTERNAL_TOLERANCE:
            raise InvalidWeights("Внутренняя ошибка нормализации весов")

    def as_dict(self) -> dict[str, float]:
        return {key: round(value, 6) for key, value in self.values.items()}


def default_weights(keys: tuple[str, ...]) -> WeightSet:
    return WeightSet({key: 1.0 / len(keys) for key in keys})
