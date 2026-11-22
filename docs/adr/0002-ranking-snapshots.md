# ADR 0002: Store ranking snapshots, not references

**Status**: accepted (2026-11-22)

## Context

FR-016 and SC-008 require that a ranking the user was shown can be reproduced
exactly, even after the catalog changes. A ranking computed from live tables
would silently change when a price is edited or a model is retired, so the
historical result could no longer be defended in the report or in a review.

## Decision

Each ranking stores `preferences` (normalized weights, goals, budget, soft
preferences), `catalog_snapshot` (every eligible model with its raw criterion
values, in id order), `algorithm_version`, and `criteria_version` (content hash
of `shared/criteria.json`). `ranking_items` store the computed rank, flows, net
score, per-criterion contributions, and the generated reason. Replay reads the
stored rows; it never recomputes against the current catalog.

## Consequences

- Historical rankings are immutable by construction, which is exactly what
  SC-008 demands.
- Storage grows with the eligible set (about 0.2 KB per model per ranking). For
  a coursework-scale catalog this is negligible.
- Retired models remain visible in old rankings but disappear from `/models`
  and from new rankings, which is the intended behaviour for FR-015.
- Changing normalization, thresholds, or criteria requires a new
  `algorithm_version`; old rankings keep their original version string.
