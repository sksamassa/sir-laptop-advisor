"""Profiles persistence: users, sessions, and saved profiles."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from laptop_dss.profiles.domain.weights import WeightSet
from laptop_dss.shared.adapters import db

WEIGHT_COLUMNS = {
    "price": "w_price",
    "performance": "w_performance",
    "memory": "w_memory",
    "weight": "w_weight",
    "battery": "w_battery",
    "screen": "w_screen",
    "warranty": "w_warranty",
}


def find_user_by_email(email: str) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT id, email, password_hash, role, created_at FROM users WHERE lower(email) = lower(%s)",
        (email,),
    )


def get_user(user_id: uuid.UUID) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT id, email, role, created_at FROM users WHERE id = %s", (user_id,)
    )


def create_user(email: str, password_hash: str, role: str = "shopper") -> dict[str, Any]:
    row = db.fetch_one(
        "INSERT INTO users (id, email, password_hash, role) VALUES (%s, %s, %s, %s) "
        "RETURNING id, email, role",
        (uuid.uuid4(), email, password_hash, role),
    )
    assert row is not None
    return row


def create_session(
    user_id: uuid.UUID,
    token_hash: bytes,
    *,
    idle_days: int,
    absolute_days: int,
) -> None:
    now = datetime.now(UTC)
    db.execute(
        "INSERT INTO sessions (id, user_id, token_hash, last_seen_at, expires_at, absolute_expires_at) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (
            uuid.uuid4(),
            user_id,
            token_hash,
            now,
            now + timedelta(days=idle_days),
            now + timedelta(days=absolute_days),
        ),
    )


def find_session_user(token_hash: bytes) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT u.id, u.email, u.role, s.expires_at, s.absolute_expires_at "
        "FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = %s AND s.expires_at > now() AND s.absolute_expires_at > now()",
        (token_hash,),
    )


def touch_session(token_hash: bytes, *, idle_days: int) -> None:
    db.execute(
        "UPDATE sessions SET last_seen_at = now(), "
        "expires_at = LEAST(now() + make_interval(days => %s), absolute_expires_at) "
        "WHERE token_hash = %s",
        (idle_days, token_hash),
    )


def delete_session(token_hash: bytes) -> None:
    db.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))


def purge_expired_sessions() -> None:
    db.execute("DELETE FROM sessions WHERE expires_at <= now() OR absolute_expires_at <= now()")


def get_profile(user_id: uuid.UUID) -> dict[str, Any] | None:
    row = db.fetch_one(
        "SELECT id, user_id, goals, budget_minor, preferred_brand, preferred_os, form_factor, "
        "w_price, w_performance, w_memory, w_weight, w_battery, w_screen, w_warranty, revision, "
        "updated_at FROM profiles WHERE user_id = %s",
        (user_id,),
    )
    if row is None:
        return None
    weights = {key: float(row[column]) for key, column in WEIGHT_COLUMNS.items()}
    return {
        "goals": row["goals"],
        "budget_minor": row["budget_minor"],
        "preferred_brand": row["preferred_brand"],
        "preferred_os": row["preferred_os"],
        "form_factor": row["form_factor"],
        "weights": weights,
        "revision": row["revision"],
        "updated_at": row["updated_at"].isoformat(),
    }


def upsert_profile(
    user_id: uuid.UUID,
    *,
    goals: list[str],
    budget_minor: int,
    preferred_brand: str | None,
    preferred_os: str | None,
    form_factor: str | None,
    weights: WeightSet,
    partial: bool,
) -> dict[str, Any]:
    values = weights.as_dict()
    columns = [WEIGHT_COLUMNS[key] for key in values]
    if partial:
        assignments = ", ".join(f"{column} = %s" for column in columns)
        db.execute(
            f"UPDATE profiles SET {assignments}, goals = %s, budget_minor = %s, "
            "preferred_brand = %s, preferred_os = %s, form_factor = %s, "
            "revision = revision + 1, updated_at = now() WHERE user_id = %s",
            [
                *[values[key] for key in values],
                goals,
                budget_minor,
                preferred_brand,
                preferred_os,
                form_factor,
                user_id,
            ],
        )
    else:
        db.execute(
            "INSERT INTO profiles (id, user_id, goals, budget_minor, preferred_brand, "
            "preferred_os, form_factor, " + ", ".join(columns) + ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, " + ", ".join(["%s"] * len(columns)) + ") "
            "ON CONFLICT (user_id) DO UPDATE SET goals = EXCLUDED.goals, "
            "budget_minor = EXCLUDED.budget_minor, preferred_brand = EXCLUDED.preferred_brand, "
            "preferred_os = EXCLUDED.preferred_os, form_factor = EXCLUDED.form_factor, "
            + ", ".join(f"{column} = EXCLUDED.{column}" for column in columns)
            + ", revision = profiles.revision + 1, updated_at = now()",
            [
                uuid.uuid4(),
                user_id,
                goals,
                budget_minor,
                preferred_brand,
                preferred_os,
                form_factor,
                *[values[key] for key in values],
            ],
        )
    saved = get_profile(user_id)
    assert saved is not None
    return saved
