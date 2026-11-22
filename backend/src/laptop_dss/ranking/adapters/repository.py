"""Ranking persistence: stored snapshots make replay exact (FR-016)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping, Sequence

from psycopg2.extras import Json

from laptop_dss.shared.adapters import db

_ITEM_COLUMNS = (
    "ranking_id, rank, model_id, model_snapshot, phi_plus, phi_minus, net_score, "
    "contributions, reason"
)


def save_ranking(
    *,
    user_id: uuid.UUID | None,
    preferences: Mapping[str, Any],
    catalog_snapshot: Sequence[Mapping[str, Any]],
    criteria_version: str,
    algorithm_version: str,
    items: Sequence[Mapping[str, Any]],
) -> uuid.UUID:
    ranking_id = uuid.uuid4()
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO rankings (id, user_id, preferences, catalog_snapshot, algorithm_version, "
            "criteria_version, candidate_count) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                ranking_id,
                user_id,
                Json(dict(preferences)),
                Json(list(catalog_snapshot)),
                algorithm_version,
                criteria_version,
                len(catalog_snapshot),
            ),
        )
        for item in items:
            cur.execute(
                "INSERT INTO ranking_items (ranking_id, rank, model_id, model_snapshot, phi_plus, "
                "phi_minus, net_score, contributions, reason) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    ranking_id,
                    item["rank"],
                    item["model_id"],
                    Json(dict(item["model_snapshot"])),
                    item["phi_plus"],
                    item["phi_minus"],
                    item["net_score"],
                    Json(dict(item["contributions"])),
                    item["reason"],
                ),
            )
    return ranking_id


def get_ranking(ranking_id: uuid.UUID) -> dict[str, Any] | None:
    return db.fetch_one(
        "SELECT id, user_id, preferences, catalog_snapshot, algorithm_version, criteria_version, "
        "candidate_count, created_at FROM rankings WHERE id = %s",
        (ranking_id,),
    )


def get_items(ranking_id: uuid.UUID) -> list[dict[str, Any]]:
    return db.fetch_all(
        f"SELECT {_ITEM_COLUMNS} FROM ranking_items WHERE ranking_id = %s ORDER BY rank ASC",
        (ranking_id,),
    )


def list_rankings(user_id: uuid.UUID, limit: int = 20) -> list[dict[str, Any]]:
    return db.fetch_all(
        "SELECT id, created_at, candidate_count, algorithm_version, criteria_version "
        "FROM rankings WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    )
