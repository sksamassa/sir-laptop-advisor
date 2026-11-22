# Phase 1 Data Model: SIR-Based Laptop Selection Service

**Feature**: `001-sir-laptop-selection` | **Date**: 2026-11-22

Derived from the spec's Key Entities and Functional Requirements. Physical model targets
PostgreSQL 16; all timestamps are `timestamptz` in UTC, all money is integer kopecks.

## Entity map

```text
users 1──1 profiles
users 1──* sessions
users 1──* rankings (nullable: guest rankings have no user)
device_models 1──* ranking_items   (via snapshotted model id, not an FK)
rankings 1──* ranking_items
processed_events (standalone idempotency ledger)
```

`ranking_items` deliberately keeps a snapshot of the model data instead of an FK to
`device_models`: a retired or renamed model must not alter a historical ranking (FR-016,
SC-008).

## Tables

### `users`

| Column | Type | Rules |
|--------|------|-------|
| `id` | `uuid` PK | generated application-side |
| `email` | `citext` unique, not null | lowercased, validated; never logged |
| `password_hash` | `text` not null | Argon2id encoded hash |
| `role` | `text` not null | `shopper` (default) or `maintainer`; guards the admin catalog endpoints in `contracts/api.md` |
| `created_at` | `timestamptz` not null | |
| `updated_at` | `timestamptz` not null | |

### `sessions`

| Column | Type | Rules |
|--------|------|-------|
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK → `users.id` ON DELETE CASCADE | |
| `token_hash` | `bytea` unique not null | SHA-256 of the opaque token; the raw token is never stored |
| `created_at` | `timestamptz` not null | |
| `last_seen_at` | `timestamptz` not null | slides the 7-day idle timeout |
| `expires_at` | `timestamptz` not null | `last_seen_at + 7 days`, capped by absolute expiry |
| `absolute_expires_at` | `timestamptz` not null | `created_at + 30 days` |

Index: `(user_id)`, `(expires_at)` for cleanup.

### `profiles`

| Column | Type | Rules |
|--------|------|-------|
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK → `users.id` ON DELETE CASCADE, unique | one profile per account |
| `goals` | `text[]` not null | non-empty subset of `study`, `development`, `design`, `gaming` |
| `budget_minor` | `bigint` not null | > 0, ≤ 100 000 000 kopecks (1 000 000 RUB) |
| `preferred_brand` | `text` null | free text, 1–60 chars when present |
| `preferred_os` | `text` null | one of `windows`, `macos`, `linux` |
| `form_factor` | `text` null | one of `ultrabook`, `laptop`, `gaming`, `convertible` |
| `w_price` … `w_warranty` | `numeric(9,6)` not null each | ≥ 0, sum ∈ [0.999999, 1.000001] (DB `CHECK`), renormalized by the domain |
| `revision` | `integer` not null default 1 | incremented on every accepted change |
| `created_at` / `updated_at` | `timestamptz` not null | |

Seven explicit weight columns (rather than JSONB) keep the invariant enforceable by a
database `CHECK` and make the sum auditable. Adding a criterion therefore needs a migration,
which is accepted and documented in the plan.

### `device_models`

| Column | Type | Rules |
|--------|------|-------|
| `id` | `uuid` PK | stable identity used for tie-breaking |
| `brand` | `text` not null | 1–60 chars |
| `model_name` | `text` not null | 1–120 chars |
| `slug` | `text` unique not null | derived, lowercase, hyphenated |
| `os` | `text` not null | `windows` \| `macos` \| `linux` |
| `form_factor` | `text` not null | `ultrabook` \| `laptop` \| `gaming` \| `convertible` |
| `price_minor` | `bigint` not null | > 0 kopecks |
| `cpu_score` | `integer` not null | benchmark points, > 0 |
| `ram_gb` | `integer` not null | 4–256 |
| `weight_g` | `integer` not null | 500–5000 |
| `battery_minutes` | `integer` not null | 60–2000 |
| `screen_score` | `numeric(4,2)` not null | 0–10 |
| `warranty_months` | `integer` not null | 0–60 |
| `status` | `text` not null | `active` \| `retired` |
| `published_at` | `timestamptz` null | set when status becomes `active` |
| `retired_at` | `timestamptz` null | set when status becomes `retired` |
| `created_at` / `updated_at` | `timestamptz` not null | |

Rule (FR-015): a model may leave `draft`-like incompleteness only when all seven criteria and
the price are present; the table enforces `NOT NULL` on every criterion column. Unique
`(brand, model_name)`.

Indexes: `(status, price_minor)`, `(brand)`, `(os)`, `(form_factor)`.

**State transitions**: `active` → `retired` (sets `retired_at`, excludes from new rankings)
and `retired` → `active` (clears `retired_at`, sets `published_at` if absent). No hard
delete, so historical snapshots keep meaning.

### `rankings`

| Column | Type | Rules |
|--------|------|-------|
| `id` | `uuid` PK | |
| `user_id` | `uuid` null FK → `users.id` ON DELETE SET NULL | null for guest rankings |
| `preferences` | `jsonb` not null | goals, budget, brand/os/form filter, normalized weights |
| `catalog_snapshot` | `jsonb` not null | ordered array of eligible models with raw criterion values |
| `algorithm_version` | `text` not null | e.g. `sir-1.0.0` |
| `criteria_version` | `text` not null | hash of `shared/criteria.json` used |
| `candidate_count` | `integer` not null | length of the eligible set |
| `created_at` | `timestamptz` not null | |

Index: `(user_id, created_at desc)`.

### `ranking_items`

| Column | Type | Rules |
|--------|------|-------|
| `ranking_id` | `uuid` FK → `rankings.id` ON DELETE CASCADE | |
| `rank` | `integer` not null | 1-based, dense across the result |
| `model_id` | `uuid` not null | snapshotted identity |
| `model_snapshot` | `jsonb` not null | brand, name, price, seven raw values |
| `phi_plus` / `phi_minus` / `net_score` | `numeric(12,9)` not null | 6-decimal display |
| `contributions` | `jsonb` not null | `{criterion_key: {normalized, contribution}}` |
| `reason` | `text` not null | generated Russian one-liner |

Primary key `(ranking_id, rank)`; unique `(ranking_id, model_id)`.

### `processed_events`

| Column | Type | Rules |
|--------|------|-------|
| `event_id` | `uuid` not null | |
| `handler` | `text` not null | subscriber name |
| `processed_at` | `timestamptz` not null | |

Primary key `(event_id, handler)` — the idempotency guard required by Principle II.

## Validation rules traced to requirements

| Rule | Source |
|------|--------|
| Weights non-negative, at least one > 0, input total within 0.5%, stored sum within 1e-6 | FR-003, Principle IV |
| Budget is a hard filter applied before normalization and scoring | FR-005 |
| Every model in a ranking has values for all seven criteria | FR-015 |
| Normalized values and per-criterion contributions stored for every ranked model | FR-007 |
| Rank order is total and stable; equal scores break by `model_id` ascending | FR-008 |
| Preferences and catalog are snapshotted per ranking | FR-016, SC-008 |
| A ranking stores the algorithm and criteria versions that produced it | Principle IV, SC-008 |

## Derived value objects (not tables)

- **CriteriaRegistry**: loaded from `shared/criteria.json`, immutable, versioned by content
  hash; provides direction, unit, thresholds, and display metadata for the seven criteria.
- **WeightSet**: seven normalized decimals summing to 1 within 1e-6; construction validates
  and renormalizes.
- **SirScore**: `phi_plus`, `phi_minus`, `net_score`, and the per-criterion decomposition;
  produced by the ranking kernel and compared as rank, never by float equality.
- **ComparisonSet**: 2–4 model ids drawn from one ranking; validated against that ranking's
  items, not against the live catalog.

## Indexing and volume notes

Expected volume: ≤ 5,000 `device_models`, ≤ 1,000 `users`, and a few thousand `rankings`
over the coursework lifetime. `catalog_snapshot` is bounded by the eligible set after the
budget filter, typically well under 1,000 rows per ranking, at roughly 0.2 KB per model.
