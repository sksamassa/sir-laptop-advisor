# Quickstart Validation Guide: SIR-Based Laptop Selection Service

**Feature**: `001-sir-laptop-selection` | **Date**: 2026-11-22

This guide proves the feature works end to end. It lists prerequisites, the one-command
startup, and validation scenarios that map to the spec's success criteria. It intentionally
contains no implementation code; see [data-model.md](./data-model.md) and
[contracts/api.md](./contracts/api.md) for the details each check relies on.

## Prerequisites

- Docker Engine or Docker Desktop with Compose v2 (`docker compose version` works)
- Git, and this repository checked out on branch `001-sir-laptop-selection`
- Optional for running tests outside containers: Python 3.12 and Node.js 20 LTS
- A browser; a phone-sized viewport (390 × 844) for the mobile check

## Start the stack

```bash
cp .env.example .env            # set POSTGRES_PASSWORD and SESSION_SECRET
docker compose up --build -d    # postgres, api, web
docker compose exec api alembic upgrade head
docker compose exec api python -m laptop_dss.seed --catalog fixtures/models.seed.json
```

Expected state:

- `curl http://localhost:8000/api/v1/health` → `{"status":"ok","db":"ok"}`
- `curl http://localhost:8000/api/v1/criteria` → seven criteria with Russian labels
- `http://localhost:3000` renders the ranking form in Russian
- The seed is idempotent: running it twice keeps the same model count

## Validation scenarios

| # | Scenario | Steps | Expected outcome | Covers |
|---|----------|-------|------------------|--------|
| V1 | Guest ranking | Open `/`, enter budget 80 000 ₽, goals «учёба» and «разработка», submit with default weights | A ranked list appears within 2 s; every item shows rank, score, and a one-line Russian reason; all prices ≤ 80 000 ₽ | SC-001, SC-004, FR-005, FR-006 |
| V2 | Explainability | Open the detail panel of the second item | Seven criteria with normalized values and contributions; contributions sum to the item's net score; the two strongest and the weakest criterion are visible | SC-003, FR-007 |
| V3 | Determinism | Submit the identical ranking request twice; compare item ids and ranks | Identical order and ranks in both responses, including ties | SC-007, FR-008 |
| V4 | Empty result | Submit a budget of 10 000 ₽ | A friendly empty state with guidance (`empty_reason: budget_too_low`); no error page, no stack trace | SC-006 |
| V5 | Weight validation | Set the battery weight to 40% while the total becomes 105% | Submission is blocked before ranking with `400 invalid_weights` and a Russian message naming the problem | FR-003, Principle IV |
| V6 | Comparison | From a ranking with ≥ 4 items, select three | Side-by-side table across all seven criteria; the best value in each row is highlighted; `best_index` matches direction (lowest price, highest battery) | FR-010 |
| V7 | Profile persistence | Register, save a profile with battery 40%, sign out, sign in, request a ranking without entering weights | Saved weights are applied automatically and the ranking visibly favours battery life | FR-011, FR-012, FR-013 |
| V8 | Replay after catalog change | Note a ranking id; as a maintainer change that model's price via `PATCH /admin/models/{id}`; reopen the stored ranking | The stored ranking is unchanged; a newly requested ranking may differ | FR-016, SC-008 |
| V9 | Retired model | Retire the top-ranked model; reload `/models` and request a new ranking | The model disappears from browsing and from new rankings; the historical ranking still lists it | FR-015, edge cases |
| V10 | Algorithm equivalence | Run `make test` | The vectorized SIR kernel matches the brute-force pairwise definition on random matrices at `1e-9`, and the golden dataset reproduces its expected ranking | Principle IV, research R1 |
| V11 | Impossible filters | On `/catalog`, filter by a brand and an OS combination that does not exist | Empty state with a suggestion to relax a filter; catalogue order preserved when filters are cleared | SC-006, FR-009 |
| V12 | Mobile layout | Repeat V1 at a 390 × 844 viewport | No horizontal scrolling, results and their order are preserved | FR-018 |

## Test commands

```bash
make test          # backend unit + integration + contract tests with coverage
make test-api      # contract tests against a running API
make e2e           # Playwright: guest ranking -> details -> compare -> register -> saved weights
make gen-criteria  # regenerate criteria constants; fails if the generated files drift
make lint          # ruff, eslint
make typecheck     # mypy --strict on domain/application, tsc --noEmit
```

Expected: `make test` green with domain and ranking coverage ≥ 80%; `make gen-criteria`
produces no diff; `make e2e` completes the single end-to-end flow.

## Manual spot check of the method

1. Request a ranking with equal weights on a five-model seed and record the order.
2. Raise the price weight to 60% and re-request.
3. The cheapest models should move up relative to step 1, and the detail view should attribute
   the change to the `price` contribution. If the order does not move, normalization or the
   preference thresholds are wrong (see research R1/R2).

## Troubleshooting

- **Port 8000 or 3000 busy**: change the host port mapping in `docker-compose.yml`.
- **API cannot reach the database**: `docker compose logs postgres`; confirm the DSN in
  `.env` uses the compose service name `postgres`, not `localhost`.
- **Frontend shows stale criteria labels**: run `make gen-criteria` and rebuild the web image;
  a drift test fails the build when generated constants are outdated.
- **File-watching misbehaves on a OneDrive-synced folder**: Docker bind mounts over OneDrive
  can miss change notifications. Rebuild the affected image (`docker compose build api web`)
  instead of relying on hot reload.
- **Seed reports rows skipped**: the seed is idempotent by `(brand, model_name)`; skipped rows
  are already present, not errors.
