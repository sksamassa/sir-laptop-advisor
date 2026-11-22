"""Catalog domain: a device model and its seven criterion values."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from laptop_dss.catalog.domain.criteria import CriteriaRegistry
from laptop_dss.shared.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class CriterionValues:
    price: int
    performance: int
    memory: int
    weight: int
    battery: int
    screen: float
    warranty: int

    def as_dict(self) -> dict[str, float]:
        return {
            "price": float(self.price),
            "performance": float(self.performance),
            "memory": float(self.memory),
            "weight": float(self.weight),
            "battery": float(self.battery),
            "screen": float(self.screen),
            "warranty": float(self.warranty),
        }


@dataclass(frozen=True, slots=True)
class DeviceModel:
    id: uuid.UUID
    brand: str
    model_name: str
    os: str
    form_factor: str
    values: CriterionValues
    status: str = "active"

    def __post_init__(self) -> None:
        if not 1 <= len(self.brand) <= 60:
            raise ValidationError("Бренд должен содержать от 1 до 60 символов")
        if not 1 <= len(self.model_name) <= 120:
            raise ValidationError("Название модели должно содержать от 1 до 120 символов")
        if self.values.price <= 0:
            raise ValidationError("Цена должна быть положительной")
        if self.status not in ("active", "retired"):
            raise ValidationError("Недопустимый статус модели")

    @property
    def price_minor(self) -> int:
        return self.values.price

    def validate_vocabularies(self, registry: CriteriaRegistry) -> None:
        if self.os not in registry.operating_systems:
            raise ValidationError(f"Недопустимая операционная система: {self.os}")
        if self.form_factor not in registry.form_factors:
            raise ValidationError(f"Недопустимый форм-фактор: {self.form_factor}")

    def is_complete(self) -> bool:
        return all(value is not None for value in self.values.as_dict().values())
