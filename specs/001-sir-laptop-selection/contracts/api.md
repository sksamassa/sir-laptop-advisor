# HTTP API Contract: SIR-Based Laptop Selection Service

**Version**: 1.0.0 | **Feature**: `001-sir-laptop-selection` | **Date**: 2026-11-22

Base path `/api/v1`. JSON in, JSON out (`Content-Type: application/json; charset=utf-8`),
snake_case field names, money as integer kopecks, timestamps as UTC ISO-8601 with `Z`.
FastAPI generates `/api/v1/openapi.json`; a contract test asserts every documented path,
status code, and required field here is present in the generated schema.

## Authentication

- Login sets an opaque session cookie named `sess`: `HttpOnly; SameSite=Lax; Path=/;
  Secure` (Secure omitted only over plain HTTP on `localhost`).
- Identity is always derived from the cookie. No endpoint accepts a user id.
- `maintainer` routes require `users.role = 'maintainer'`.
- Guest callers may call `POST /rankings`; the stored ranking is then addressable
  **only** by its unguessable id (a capability), so guests can replay and compare
  their own result without an account. Account-owned rankings stay owner-only.

## Errors

All errors use:

```json
{ "error": { "code": "invalid_weights", "message": "Сумма весов должна быть 100%", "details": { "sum": 0.87 } } }
```

| Status | When |
|--------|------|
| 400 | Semantically invalid input that passed schema validation (weights, budget) |
| 401 | No valid session, or wrong credentials |
| 403 | Authenticated but not the owner, or not a maintainer |
| 404 | Unknown resource, or a profile that was never created |
| 409 | Email already registered |
| 422 | Request body failed schema validation (unknown fields rejected) |
| 429 | Rate limit exceeded |
| 503 | Database unavailable |

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | none | Liveness and DB reachability |
| GET | `/criteria` | none | The seven criteria, labels, directions, units, thresholds |
| GET | `/models` | none | Paginated catalog browse |
| GET | `/models/{id}` | none | One model with all seven criteria |
| POST | `/auth/register` | none | Create an account |
| POST | `/auth/login` | none | Start a session |
| POST | `/auth/logout` | session | Delete the session |
| GET | `/auth/me` | session | Current account summary |
| GET | `/profile` | session | Saved profile |
| PUT | `/profile` | session | Create or replace the profile |
| PATCH | `/profile` | session | Change individual fields or weights |
| POST | `/rankings` | optional session | Compute a ranking |
| GET | `/rankings` | session | Ranking history, newest first |
| GET | `/rankings/{id}` | owner or guest id | Replay a stored ranking |
| POST | `/rankings/{id}/comparison` | owner or guest id | Compare 2–4 models from that ranking |
| POST | `/admin/models` | maintainer | Add a model |
| PATCH | `/admin/models/{id}` | maintainer | Update a model |
| POST | `/admin/models/{id}/retire` | maintainer | Retire a model |
| POST | `/admin/models/{id}/publish` | maintainer | Restore a retired model |
| POST | `/admin/catalog/refresh` | maintainer | Pull the catalog from the configured live source, falling back to CSV |

---

### `POST /rankings`

Request (guest form; fields marked `?` are optional):

```json
{
  "budget_minor": 8000000,
  "goals": ["study", "development"],
  "preferred_brand": "Lenovo",
  "preferred_os": "windows",
  "form_factor": "ultrabook",
  "weights": { "price": 0.20, "performance": 0.20, "memory": 0.15,
               "weight": 0.10, "battery": 0.20, "screen": 0.10, "warranty": 0.05 },
  "use_saved_weights": false
}
```

- `weights` may be omitted: a guest receives an equal-weight default; an authenticated caller
  with `use_saved_weights: true` receives the saved profile weights.
- `preferred_brand`, `preferred_os`, `form_factor` are *soft* preferences recorded with the
  request; hard filtering uses `budget_minor`. (Browsing filters are hard on `/models`.)

Response `201`:

```json
{
  "ranking_id": "6f1c…",
  "algorithm_version": "sir-1.0.0",
  "criteria_version": "sha256:9a3c…",
  "candidate_count": 42,
  "items": [
    {
      "rank": 1,
      "model": { "id": "0b7d…", "brand": "Lenovo", "model_name": "IdeaPad 5",
                 "price_minor": 6499000, "os": "windows", "form_factor": "ultrabook" },
      "net_score": 0.182401,
      "phi_plus": 2.140331,
      "phi_minus": 1.957930,
      "contributions": {
        "price":      { "normalized": 0.62, "contribution":  0.0431 },
        "performance":{ "normalized": 0.55, "contribution":  0.0210 },
        "memory":     { "normalized": 0.90, "contribution":  0.0680 },
        "weight":     { "normalized": 0.40, "contribution": -0.0120 },
        "battery":    { "normalized": 0.75, "contribution":  0.0410 },
        "screen":     { "normalized": 0.60, "contribution":  0.0100 },
        "warranty":   { "normalized": 0.50, "contribution":  0.0000 }
      },
      "reason": "Лучший баланс памяти и автономности в пределах бюджета"
    }
  ]
}
```

Contract rules:

1. `items` are ordered by `rank` ascending; `rank` starts at 1 and has no gaps.
2. Ordering is by `net_score` descending; equal scores break by `model.id` ascending.
   Scores are stored with 6 decimals; clients MUST NOT compare floats for ordering.
3. `contributions` always contains exactly the seven criterion keys and
   `sum(contribution) == net_score` within `1e-6`.
4. `candidate_count == 0` returns `201` with `items: []` and an `empty_reason` string
   (for example `budget_too_low`), never a `4xx`. It also carries
   `cheapest_price_minor`: the lowest active catalog price (or `null` when the catalog
   is empty), so the interface can tell the shopper what budget would find something.
5. Weights outside the allowed tolerance return `400 invalid_weights` before any ranking.

### `GET /rankings/{id}`

Returns the stored ranking in the same shape as the `POST` response plus
`created_at`, `preferences`, and `catalog_snapshot_version`. A stored ranking is replayed
from its snapshot; it does not reflect later catalog edits.

Optional display filters: `brand`, `os`, `form_factor`, `max_price_minor`. They narrow the
returned `items` **without re-ranking**: stored SIR order and the original `rank` values are
preserved, and `filtered_from` reports the pre-filter candidate count. This is deliberate —
re-running SIR on a subset would change normalization and could reorder results.

### `POST /rankings/{id}/comparison`

```json
{ "model_ids": ["0b7d…", "aa12…", "c9f0…"] }
```

`2 <= len(model_ids) <= 4`, all ids MUST belong to that ranking, otherwise `400`. Response:

```json
{
  "models": [ { "id": "…", "brand": "…", "model_name": "…", "price_minor": 6499000 } ],
  "criteria": ["price", "performance", "memory", "weight", "battery", "screen", "warranty"],
  "rows": [ { "criterion": "price", "direction": "min",
              "values": [6499000, 8299000, 7199000], "best_index": 0 } ],
  "best_overall_index": 0
}
```

`best_index` respects direction: lowest price wins, highest battery wins.

### `GET /models`

Query: `brand`, `os`, `form_factor`, `max_price_minor`, `q` (name search), `page` (default 1),
`page_size` (default 20, max 100), `sort` (`price_asc|price_desc|name`). Response:
`{ "items": [...], "page": 1, "page_size": 20, "total": 137, "meta": { "source": "live:https://…",
"fetched_at": "2026-11-22T15:10:00Z", "tracked": 36, "total": 36 } }`. Only `active` models
appear. `meta` reports where the visible prices came from and when, so the UI never implies
live data it does not have.

### `POST /admin/catalog/refresh`

Runs the configured source chain in order: `CATALOG_LIVE_URL` (JSON feed), then
`CATALOG_HTML_CONFIG` (CSS selectors for a page you are permitted to read), then
`CATALOG_CSV_PATH`. Returns `{ "source": "live:…", "inserted": 0, "updated": 36, "errors": [],
"fallback_errors": ["live:…: HTTP 403"], "fetched_at": "…" }`. If every source fails it returns
`503 catalog_unavailable` and the catalog is left untouched — a failed refresh never empties
the service.

### `GET /profile` and `PUT /profile`

Profile response:

```json
{
  "goals": ["study", "development"],
  "budget_minor": 8000000,
  "preferred_brand": "Lenovo",
  "preferred_os": "windows",
  "form_factor": "ultrabook",
  "weights": { "price": 0.20, "performance": 0.20, "memory": 0.15,
               "weight": 0.10, "battery": 0.20, "screen": 0.10, "warranty": 0.05 },
  "revision": 3,
  "updated_at": "2026-11-22T13:40:00Z"
}
```

`PUT` replaces the whole profile and requires all fields except the three soft preferences.
`PATCH` accepts any subset, including a single weight. Both revalidate the weight total and
return the new `revision`.

### `POST /auth/register` and `POST /auth/login`

```json
{ "email": "student@example.com", "password": "…at least 12 characters…" }
```

Register returns `201 { "user_id": "…", "role": "shopper" }`. Login returns `200` with the
profile summary and the `sess` cookie. Passwords shorter than 12 characters return `400`.
Login is rate limited to 5 attempts per minute per (IP, email) pair and always returns the
same message for unknown email and wrong password.

### Admin catalog endpoints

`POST /admin/models` requires every criterion value and the price; the body uses the same
field names as the `device_models` table. A model missing any criterion returns `422`.
`PATCH` updates values and sets `updated_at`. `retire`/`publish` toggle `status` and the
corresponding timestamps. Retired models disappear from `/models` and from new rankings but
remain readable through historical rankings.

## Cross-cutting contract rules

- Unknown JSON fields are rejected (`422`) on every write endpoint.
- The frontend never receives secrets, tokens, or the API base URL from server-rendered
  props.
- CORS: explicit origin allowlist from configuration; wildcard origins are forbidden when
  credentials are enabled.
- Logs record `request_id`, route, status, and duration; never email, password, cookie, or
  weight values.
- Rate limits: `POST /rankings` 30 per minute per session, `POST /auth/login` 5 per minute,
  `POST /auth/register` 3 per 10 minutes per IP.
- The response to `GET /health` includes `{"status": "ok", "db": "ok"}` or `503`.
