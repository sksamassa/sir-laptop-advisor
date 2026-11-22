"""Russian explanation text for a ranked model (FR-006)."""

from __future__ import annotations

from typing import Mapping

from laptop_dss.catalog.domain.criteria import CriteriaRegistry
from laptop_dss.ranking.domain.sir_reference import SirScore


def _label(registry: CriteriaRegistry, key: str) -> str:
    return registry.by_key(key).label_ru.lower()


def build_reason(
    score: SirScore,
    registry: CriteriaRegistry,
    model_name: str,
    *,
    rank: int,
    total: int,
) -> str:
    contributions = {
        key: value.contribution for key, value in score.contributions.items()
    }
    if not contributions:
        return f"{model_name}: недостаточно данных для объяснения."
    ranked = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
    best_key, best_value = ranked[0]
    worst_key, worst_value = ranked[-1]

    if abs(best_value) < 1e-12:
        return (
            f"{model_name}: все модели в выборке равны по выбранным критериям, "
            "порядок определён стабильным правилом."
        )

    if rank == 1:
        lead = f"{model_name} — лучший баланс по выбранным весам"
    else:
        lead = f"{model_name} занимает {rank}-е место из {total}"

    parts = [f"{lead}: сильнее всего помогла «{_label(registry, best_key)}»"]
    if worst_value < -1e-12:
        parts.append(f"слабее всего — «{_label(registry, worst_key)}»")
    return "; ".join(parts) + "."


def gap_to_top(
    top: SirScore,
    other: SirScore,
    registry: CriteriaRegistry,
) -> dict[str, object]:
    """Return the score gap and the criteria responsible for it."""
    deltas: list[tuple[str, float]] = []
    for key in registry.keys:
        top_entry = top.contributions.get(key)
        other_entry = other.contributions.get(key)
        if top_entry is None or other_entry is None:
            # A stored ranking can predate a criterion; skip it instead of failing.
            continue
        delta = other_entry.contribution - top_entry.contribution
        deltas.append((key, delta))
    deltas.sort(key=lambda item: item[1])
    gap = other.net_score - top.net_score
    return {
        "gap": round(gap, 6),
        "decisive_criteria": [
            {"criterion": key, "delta": round(delta, 6)} for key, delta in deltas[:2] if delta < 0
        ],
        "strongest_criteria": [
            {"criterion": key, "delta": round(delta, 6)} for key, delta in deltas[-2:] if delta > 0
        ],
    }


def contribution_payload(contributions: Mapping[str, object]) -> dict[str, dict[str, float]]:
    payload: dict[str, dict[str, float]] = {}
    for key, value in contributions.items():
        payload[key] = {
            "normalized": round(float(getattr(value, "normalized")), 6),
            "contribution": round(float(getattr(value, "contribution")), 6),
        }
    return payload
