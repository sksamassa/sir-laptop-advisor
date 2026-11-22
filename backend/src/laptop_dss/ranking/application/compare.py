"""Comparison of 2-4 models drawn from one stored ranking (FR-010)."""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from laptop_dss.catalog.domain.criteria import load_registry
from laptop_dss.ranking.adapters import repository as ranking_repo
from laptop_dss.shared.domain.errors import Forbidden, NotFound, ValidationError


def compare(
    ranking_id: uuid.UUID,
    model_ids: Sequence[uuid.UUID],
    *,
    user_id: str | None,
) -> dict[str, Any]:
    ranking = ranking_repo.get_ranking(ranking_id)
    if ranking is None:
        raise NotFound("Ранжирование не найдено")
    # Guest rankings (no owner) are addressed by their unguessable id, which acts
    # as a capability; account-owned rankings stay restricted to their owner.
    if ranking["user_id"] is not None and str(ranking["user_id"]) != user_id:
        raise Forbidden("Ранжирование принадлежит другому пользователю")

    identifiers = [str(model_id) for model_id in model_ids]
    if len(set(identifiers)) != len(identifiers):
        raise ValidationError("Модели в сравнении не должны повторяться")
    if not 2 <= len(identifiers) <= 4:
        raise ValidationError("Для сравнения выберите от 2 до 4 моделей")

    items = {str(item["model_id"]): item for item in ranking_repo.get_items(ranking_id)}
    missing = [model_id for model_id in identifiers if model_id not in items]
    if missing:
        raise ValidationError("Модели должны входить в выбранное ранжирование")

    registry = load_registry()
    selected = [items[model_id] for model_id in identifiers]
    snapshots = [item["model_snapshot"] for item in selected]

    rows = []
    for criterion in registry.criteria:
        values = [snapshot["values"][criterion.key] for snapshot in snapshots]
        best = min(values) if criterion.direction == "min" else max(values)
        rows.append(
            {
                "criterion": criterion.key,
                "label_ru": criterion.label_ru,
                "direction": criterion.direction,
                "unit": criterion.unit,
                "values": values,
                "best_index": values.index(best),
            }
        )

    best_overall = max(range(len(selected)), key=lambda i: float(selected[i]["net_score"]))
    return {
        "models": [
            {
                "id": snapshot["id"],
                "brand": snapshot["brand"],
                "model_name": snapshot["model_name"],
                "price_minor": snapshot["price_minor"],
                "rank": item["rank"],
                "net_score": round(float(item["net_score"]), 6),
            }
            for item, snapshot in zip(selected, snapshots, strict=True)
        ],
        "criteria": list(registry.keys),
        "rows": rows,
        "best_overall_index": best_overall,
    }
