"""Reference SIR implementation: the readable, pairwise O(n^2 * m) definition.

This module is the executable specification. The vectorized engine in
``ranking/adapters/vectorized_sir.py`` must reproduce it exactly; the test suite
compares the two on random matrices. Never optimize this file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from laptop_dss.catalog.domain.criteria import CriteriaRegistry
from laptop_dss.catalog.domain.device import DeviceModel
from laptop_dss.ranking.domain.normalization import normalize
from laptop_dss.ranking.domain.preference import preference, thresholds


@dataclass(frozen=True, slots=True)
class CriterionContribution:
    normalized: float
    contribution: float


@dataclass(frozen=True, slots=True)
class SirScore:
    model_id: str
    phi_plus: float
    phi_minus: float
    net_score: float
    contributions: Mapping[str, CriterionContribution]


@dataclass(frozen=True, slots=True)
class SirResult:
    ordered: tuple[SirScore, ...]
    normalized: Mapping[str, Mapping[str, float]]
    phi_plus: Mapping[str, float]
    phi_minus: Mapping[str, float]


def _flows(
    models: Sequence[DeviceModel],
    weights: Mapping[str, float],
    registry: CriteriaRegistry,
) -> tuple[dict[str, float], dict[str, float], Mapping[str, Mapping[str, float]]]:
    matrix = normalize(models, registry)
    limits = thresholds(registry)
    ids = matrix.model_ids
    phi_plus = {model_id: 0.0 for model_id in ids}
    phi_minus = {model_id: 0.0 for model_id in ids}

    for i, a in enumerate(ids):
        for j in range(len(ids)):
            if i == j:
                continue
            for criterion in registry.criteria:
                span = matrix.values[criterion.key]
                q, p = limits[criterion.key]
                weight = weights[criterion.key]
                phi_plus[a] += weight * preference(span[i] - span[j], q=q, p=p)
                phi_minus[a] += weight * preference(span[j] - span[i], q=q, p=p)

    rows = {model_id: matrix.row(index) for index, model_id in enumerate(ids)}
    return phi_plus, phi_minus, rows


def rank(
    models: Sequence[DeviceModel],
    weights: Mapping[str, float],
    registry: CriteriaRegistry,
) -> SirResult:
    """Compute SIR scores and the total order (tie-break by model id)."""
    if not models:
        return SirResult(ordered=(), normalized={}, phi_plus={}, phi_minus={})
    registry.validate_weights_keys(dict(weights))
    phi_plus, phi_minus, rows = _flows(models, weights, registry)
    matrix = normalize(models, registry)
    limits = thresholds(registry)

    scores: list[SirScore] = []
    for index, model_id in enumerate(matrix.model_ids):
        contributions: dict[str, CriterionContribution] = {}
        for criterion in registry.criteria:
            span = matrix.values[criterion.key]
            q, p = limits[criterion.key]
            weight = weights[criterion.key]
            gain = sum(
                preference(span[index] - span[other], q=q, p=p)
                for other in range(len(span))
                if other != index
            )
            loss = sum(
                preference(span[other] - span[index], q=q, p=p)
                for other in range(len(span))
                if other != index
            )
            contributions[criterion.key] = CriterionContribution(
                normalized=span[index],
                contribution=weight * (gain - loss),
            )
        net = phi_plus[model_id] - phi_minus[model_id]
        scores.append(
            SirScore(
                model_id=model_id,
                phi_plus=phi_plus[model_id],
                phi_minus=phi_minus[model_id],
                net_score=net,
                contributions=contributions,
            )
        )

    ordered = tuple(sorted(scores, key=lambda s: (-round(s.net_score, 9), s.model_id)))
    return SirResult(
        ordered=ordered,
        normalized={model_id: rows[model_id] for model_id in matrix.model_ids},
        phi_plus=phi_plus,
        phi_minus=phi_minus,
    )
