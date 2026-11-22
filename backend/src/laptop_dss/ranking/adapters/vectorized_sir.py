"""Vectorized SIR engine: exact result in O(m * n log n) without a pair matrix.

The superiority flow decomposes per criterion because ``pi+`` is additive:

    Phi+(a) = sum_j w_j * S_j(v_j(a)),   S_j(x) = sum_b p_j(x - s_b)

With the sorted criterion column and its prefix sums, each ``S_j(x)`` splits into
the three regions of ``p_j`` and is evaluated with two binary searches. The
inferiority flow is the same function applied to the negated, re-sorted column.

NumPy is confined to this adapter (constitution, Technology & Data
Constraints); the reference implementation stays pure Python.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from laptop_dss.catalog.domain.criteria import CriteriaRegistry
from laptop_dss.catalog.domain.device import DeviceModel
from laptop_dss.ranking.domain.normalization import normalize
from laptop_dss.ranking.domain.sir_reference import (
    CriterionContribution,
    SirResult,
    SirScore,
)
from laptop_dss.ranking.domain.preference import thresholds


def _sum_preference(
    values: np.ndarray,
    sorted_values: np.ndarray,
    prefix: np.ndarray,
    *,
    q: float,
    p: float,
) -> np.ndarray:
    """Return S(x) = sum_b p(x - s_b) for every x in ``values``."""
    if sorted_values.size == 0:
        return np.zeros_like(values)
    k_one = np.searchsorted(sorted_values, values - p, side="right")
    k_linear = np.searchsorted(sorted_values, values - q, side="left")
    middle_sum = prefix[k_linear] - prefix[k_one]
    linear = ((values - q) * (k_linear - k_one) - middle_sum) / (p - q)
    return k_one.astype(np.float64) + linear


def _column(values: np.ndarray, *, q: float, p: float) -> tuple[np.ndarray, np.ndarray]:
    sorted_values = np.sort(values)
    prefix = np.concatenate(([0.0], np.cumsum(sorted_values)))
    plus = _sum_preference(values, sorted_values, prefix, q=q, p=p)
    neg_sorted = np.sort(-values)
    neg_prefix = np.concatenate(([0.0], np.cumsum(neg_sorted)))
    minus = _sum_preference(-values, neg_sorted, neg_prefix, q=q, p=p)
    return plus, minus


def rank(
    models: Sequence[DeviceModel],
    weights: Mapping[str, float],
    registry: CriteriaRegistry,
) -> SirResult:
    if not models:
        return SirResult(ordered=(), normalized={}, phi_plus={}, phi_minus={})
    registry.validate_weights_keys(dict(weights))

    matrix = normalize(models, registry)
    limits = thresholds(registry)
    n = len(models)
    phi_plus = np.zeros(n, dtype=np.float64)
    phi_minus = np.zeros(n, dtype=np.float64)
    contribution_matrix = np.zeros((n, len(registry.criteria)), dtype=np.float64)

    for column_index, criterion in enumerate(registry.criteria):
        values = np.asarray(matrix.values[criterion.key], dtype=np.float64)
        q, p = limits[criterion.key]
        plus, minus = _column(values, q=q, p=p)
        weight = float(weights[criterion.key])
        phi_plus += weight * plus
        phi_minus += weight * minus
        contribution_matrix[:, column_index] = weight * (plus - minus)

    ordered_scores: list[SirScore] = []
    for index, model_id in enumerate(matrix.model_ids):
        contributions = {
            criterion.key: CriterionContribution(
                normalized=matrix.values[criterion.key][index],
                contribution=float(contribution_matrix[index, position]),
            )
            for position, criterion in enumerate(registry.criteria)
        }
        ordered_scores.append(
            SirScore(
                model_id=model_id,
                phi_plus=float(phi_plus[index]),
                phi_minus=float(phi_minus[index]),
                net_score=float(phi_plus[index] - phi_minus[index]),
                contributions=contributions,
            )
        )

    ordered = tuple(sorted(ordered_scores, key=lambda s: (-round(s.net_score, 9), s.model_id)))
    return SirResult(
        ordered=ordered,
        normalized={
            model_id: {key: matrix.values[key][index] for key in registry.keys}
            for index, model_id in enumerate(matrix.model_ids)
        },
        phi_plus={model_id: float(phi_plus[i]) for i, model_id in enumerate(matrix.model_ids)},
        phi_minus={model_id: float(phi_minus[i]) for i, model_id in enumerate(matrix.model_ids)},
    )
