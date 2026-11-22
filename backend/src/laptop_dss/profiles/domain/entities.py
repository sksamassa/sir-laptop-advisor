"""Profile domain entities with their invariants.

Persistence still speaks in rows, but every row that reaches the application layer
passes through these entities first, so an invalid account, session, or profile
cannot be constructed by accident.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from laptop_dss.profiles.domain.weights import WeightSet
from laptop_dss.shared.domain.errors import ValidationError

ROLES = ("shopper", "maintainer")


@dataclass(frozen=True, slots=True)
class User:
    id: uuid.UUID
    email: str
    role: str = "shopper"

    def __post_init__(self) -> None:
        email = self.email.strip().lower()
        if "@" not in email or len(email) > 254:
            raise ValidationError("Некорректный адрес электронной почты")
        if self.role not in ROLES:
            raise ValidationError("Недопустимая роль пользователя")
        object.__setattr__(self, "email", email)


@dataclass(frozen=True, slots=True)
class Session:
    user_id: uuid.UUID
    token_hash: bytes
    absolute_expires_at: datetime

    def __post_init__(self) -> None:
        if len(self.token_hash) != 32:
            raise ValidationError("Хеш токена сессии должен быть 32 байта (SHA-256)")
        if self.absolute_expires_at.tzinfo is None:
            raise ValidationError("Срок жизни сессии должен быть задан в UTC")


@dataclass(frozen=True, slots=True)
class Profile:
    user_id: uuid.UUID
    goals: tuple[str, ...]
    budget_minor: int
    weights: WeightSet

    def __post_init__(self) -> None:
        if not self.goals:
            raise ValidationError("Укажите хотя бы одну цель использования")
        if not 0 < self.budget_minor <= 100_000_000:
            raise ValidationError("Бюджет должен быть в пределах от 1 до 1 000 000 рублей")
        self.weights.assert_normalized()
