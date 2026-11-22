"""Authentication and profile use cases (FR-011 .. FR-013)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from laptop_dss.catalog.domain.criteria import load_registry
from laptop_dss.config import load_settings
from laptop_dss.profiles.adapters import repository as repo
from laptop_dss.profiles.domain.weights import WeightSet
from laptop_dss.shared.domain.errors import Conflict, InvalidWeights, NotFound, Unauthorized, ValidationError

_hasher = PasswordHasher()
settings = load_settings()


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    user: dict[str, Any]


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValidationError("Пароль должен содержать не менее 12 символов")
    return _hasher.hash(password)


def register(email: str, password: str) -> dict[str, Any]:
    email = email.strip().lower()
    if "@" not in email or len(email) > 254:
        raise ValidationError("Некорректный адрес электронной почты")
    if repo.find_user_by_email(email) is not None:
        raise Conflict("Пользователь с таким адресом уже существует")
    return repo.create_user(email, hash_password(password))


def login(email: str, password: str) -> IssuedSession:
    user = repo.find_user_by_email(email)
    if user is None:
        raise Unauthorized("Неверный адрес или пароль")
    try:
        _hasher.verify(user["password_hash"], password)
    except (VerifyMismatchError, VerificationError) as exc:
        raise Unauthorized("Неверный адрес или пароль") from exc
    token = secrets.token_urlsafe(32)
    repo.create_session(
        user["id"],
        _token_hash(token),
        idle_days=settings.session_idle_days,
        absolute_days=settings.session_absolute_days,
    )
    return IssuedSession(
        token=token,
        user={"id": str(user["id"]), "email": user["email"], "role": user["role"]},
    )


def logout(token: str) -> None:
    repo.delete_session(_token_hash(token))


def current_user(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    user = repo.find_session_user(_token_hash(token))
    if user is None:
        return None
    repo.touch_session(_token_hash(token), idle_days=settings.session_idle_days)
    return {"id": str(user["id"]), "email": user["email"], "role": user["role"]}


def require_user(token: str | None) -> dict[str, Any]:
    user = current_user(token)
    if user is None:
        raise Unauthorized("Требуется вход")
    return user


def get_profile(user_id: str) -> dict[str, Any]:
    profile = repo.get_profile(uuid.UUID(user_id))
    if profile is None:
        raise NotFound("Профиль ещё не заполнен")
    return profile


def save_profile(
    user_id: str,
    *,
    goals: list[str],
    budget_minor: int,
    preferred_brand: str | None,
    preferred_os: str | None,
    form_factor: str | None,
    weights: WeightSet,
    partial: bool,
) -> dict[str, Any]:
    registry = load_registry()
    if not goals:
        raise ValidationError("Укажите хотя бы одну цель использования")
    unknown = set(goals) - set(registry.goals)
    if unknown:
        raise ValidationError(f"Неизвестные цели: {', '.join(sorted(unknown))}")
    if budget_minor <= 0 or budget_minor > 100_000_000:
        raise ValidationError("Бюджет должен быть в пределах от 1 до 1 000 000 рублей")
    if preferred_os is not None and preferred_os not in registry.operating_systems:
        raise ValidationError("Недопустимая операционная система")
    if form_factor is not None and form_factor not in registry.form_factors:
        raise ValidationError("Недопустимый форм-фактор")
    weights.assert_normalized()
    return repo.upsert_profile(
        uuid.UUID(user_id),
        goals=goals,
        budget_minor=budget_minor,
        preferred_brand=preferred_brand,
        preferred_os=preferred_os,
        form_factor=form_factor,
        weights=weights,
        partial=partial,
    )


def saved_weights(user_id: str) -> WeightSet | None:
    profile = repo.get_profile(uuid.UUID(user_id))
    if profile is None:
        return None
    try:
        return WeightSet.from_user_input(profile["weights"], load_registry().keys)
    except InvalidWeights:
        return None
