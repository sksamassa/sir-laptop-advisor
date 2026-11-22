"""Use case: compute and persist a SIR ranking (FR-004, FR-005, FR-016)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping, Sequence

from laptop_dss.catalog.adapters import repository as catalog_repo
from laptop_dss.catalog.domain.criteria import CriteriaRegistry
from laptop_dss.catalog.adapters.criteria_source import load_registry
from laptop_dss.catalog.domain.device import DeviceModel
from laptop_dss.profiles.domain.weights import WeightSet, default_weights
from laptop_dss.ranking.adapters import repository as ranking_repo
from laptop_dss.ranking.adapters.vectorized_sir import rank as sir_rank
from laptop_dss.ranking.domain.explanation import build_reason, contribution_payload
from laptop_dss.ranking.domain.sir_reference import SirScore
from laptop_dss.shared.adapters import events
from laptop_dss.shared.application.events import DomainEvent

ALGORITHM_VERSION = "sir-1.0.0"


def _model_snapshot(model: DeviceModel) -> dict[str, Any]:
    return {
        "id": str(model.id),
        "brand": model.brand,
        "model_name": model.model_name,
        "price_minor": model.price_minor,
        "os": model.os,
        "form_factor": model.form_factor,
        "values": model.values.as_dict(),
    }


def _item_payload(
    score: SirScore,
    registry: CriteriaRegistry,
    models_by_id: Mapping[str, DeviceModel],
    *,
    rank: int,
    total: int,
) -> dict[str, Any]:
    model = models_by_id[score.model_id]
    contributions = contribution_payload(score.contributions)
    # The published net score is the sum of the published contributions, so the
    # contract invariant sum(contribution) == net_score holds exactly after
    # rounding, not merely within a tolerance.
    net = round(sum(item["contribution"] for item in contributions.values()), 6)
    return {
        "rank": rank,
        "model_id": uuid.UUID(score.model_id),
        "phi_plus": round(score.phi_plus, 9),
        "phi_minus": round(score.phi_minus, 9),
        "net_score": net,
        "contributions": contributions,
        "reason": build_reason(score, registry, model.model_name, rank=rank, total=total),
        "model_snapshot": _model_snapshot(model),
    }


def create_ranking(
    *,
    budget_minor: int,
    goals: Sequence[str],
    weights: WeightSet | None,
    brand: str | None,
    os_name: str | None,
    form_factor: str | None,
    user_id: uuid.UUID | None,
) -> dict[str, Any]:
    registry = load_registry()
    chosen = weights or default_weights(registry.keys)
    chosen.assert_normalized()
    eligible = catalog_repo.eligible_by_budget(budget_minor)

    preferences = {
        "budget_minor": budget_minor,
        "goals": list(goals),
        "weights": chosen.as_dict(),
        "preferred_brand": brand,
        "preferred_os": os_name,
        "form_factor": form_factor,
    }

    if not eligible:
        ranking_id = ranking_repo.save_ranking(
            user_id=user_id,
            preferences=preferences,
            catalog_snapshot=[],
            criteria_version=registry.content_hash,
            algorithm_version=ALGORITHM_VERSION,
            items=[],
        )
        return {
            "ranking_id": str(ranking_id),
            "algorithm_version": ALGORITHM_VERSION,
            "criteria_version": registry.content_hash,
            "candidate_count": 0,
            "items": [],
            "empty_reason": "budget_too_low",
            "cheapest_price_minor": catalog_repo.cheapest_active_price(),
        }

    result = sir_rank(eligible, chosen.values, registry)
    models_by_id = {str(model.id): model for model in eligible}
    total = len(result.ordered)
    items = [
        _item_payload(score, registry, models_by_id, rank=index + 1, total=total)
        for index, score in enumerate(result.ordered)
    ]
    ranking_id = ranking_repo.save_ranking(
        user_id=user_id,
        preferences=preferences,
        catalog_snapshot=[_model_snapshot(model) for model in eligible],
        criteria_version=registry.content_hash,
        algorithm_version=ALGORITHM_VERSION,
        items=items,
    )
    events.publish(
        DomainEvent(
            name="RankingComputed",
            payload={
                "ranking_id": str(ranking_id),
                "candidate_count": total,
                "user_id": str(user_id) if user_id else None,
            },
        )
    )
    return {
        "ranking_id": str(ranking_id),
        "algorithm_version": ALGORITHM_VERSION,
        "criteria_version": registry.content_hash,
        "candidate_count": total,
        "items": _attach_gaps([_public_item(item) for item in items]),
    }


def _attach_gaps(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add a gap-to-leader breakdown to every item ranked 2 and below.

    Derived from the stored per-criterion contributions, so replay gets the same
    explanation without another table.
    """
    if not items:
        return items
    top = items[0]
    for item in items:
        if item["rank"] == 1:
            item["gap_to_top"] = None
            continue
        deltas: list[tuple[str, float]] = []
        for key, contribution in item["contributions"].items():
            top_contribution = top["contributions"].get(key)
            if top_contribution is None:
                continue
            deltas.append(
                (key, round(contribution["contribution"] - top_contribution["contribution"], 6))
            )
        deltas.sort(key=lambda pair: pair[1])
        item["gap_to_top"] = {
            "gap": round(item["net_score"] - top["net_score"], 6),
            "decisive_criteria": [
                {"criterion": key, "delta": delta} for key, delta in deltas[:2] if delta < 0
            ],
            "strongest_criteria": [
                {"criterion": key, "delta": delta} for key, delta in deltas[-2:] if delta > 0
            ],
        }
    return items


def _public_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rank": item["rank"],
        "model": item["model_snapshot"],
        "net_score": round(float(item["net_score"]), 6),
        "phi_plus": round(float(item["phi_plus"]), 6),
        "phi_minus": round(float(item["phi_minus"]), 6),
        "contributions": item["contributions"],
        "reason": item["reason"],
    }


def replay_ranking(ranking_id: uuid.UUID) -> dict[str, Any] | None:
    row = ranking_repo.get_ranking(ranking_id)
    if row is None:
        return None
    items = ranking_repo.get_items(ranking_id)
    return {
        "ranking_id": str(row["id"]),
        "algorithm_version": row["algorithm_version"],
        "criteria_version": row["criteria_version"],
        "candidate_count": row["candidate_count"],
        "created_at": row["created_at"].isoformat(),
        "preferences": row["preferences"],
        "items": _attach_gaps([_public_item(item) for item in items]),
    }
