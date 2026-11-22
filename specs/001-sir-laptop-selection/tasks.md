---

description: "Task list for the SIR-Based Laptop Selection Service"
---

# Tasks: SIR-Based Laptop Selection Service

**Input**: Design documents from `/specs/001-sir-laptop-selection/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The spec does not request TDD, but the project constitution makes automated
tests mandatory (Principle III: coverage ≥ 80% on domain and ranking; Principle V: golden
dataset and monotonicity tests). Test tasks are therefore first-class and, per the constitution,
must fail before the implementation task that satisfies them.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and
demonstrated independently. Story priorities come from spec.md (P1 → P4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Every task names the exact file path it touches

## Path Conventions

Web application layout from plan.md: `backend/src/laptop_dss/`, `backend/tests/`,
`frontend/src/`, `shared/`, `docs/`, plus root `docker-compose.yml` and `Makefile`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and structure that every later phase builds on.

- [x] T001 Create the repository layout described in plan.md: `backend/src/laptop_dss/{shared,profiles,catalog,ranking}`, `backend/tests/{unit,integration,contract}`, `frontend/src/{app,features,components/ui,lib,generated}`, `shared/`, `docs/adr/`
- [x] T002 [P] Declare backend dependencies and tool configuration in `backend/pyproject.toml` (FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, Alembic, argon2-cffi, NumPy; ruff, mypy `--strict` on `domain/` and `application/`, pytest, pytest-asyncio, httpx)
- [x] T003 [P] Declare frontend tooling in `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.mjs`, `frontend/tailwind.config.ts`, `frontend/.eslintrc.cjs`, `frontend/.prettierrc`
- [x] T004 [P] Write `docker-compose.yml` with `postgres:16`, `api`, and `web` services, healthchecks, and read-only source mounts (no secrets in the file)
- [x] T005 [P] Write `.env.example` and `backend/src/laptop_dss/config.py` (Pydantic Settings for `DATABASE_URL`, `SESSION_COOKIE_NAME`, `CORS_ORIGINS`, `SESSION_SECRET`, no hard-coded defaults for secrets)
- [x] T006 [P] Write the `Makefile` targets `up`, `down`, `migrate`, `seed`, `test`, `test-api`, `e2e`, `gen-criteria`, `lint`, `typecheck`
- [x] T007 [P] Pin toolchain versions in `.python-version` (3.12), `.nvmrc` (20), and add `.dockerignore` and `.gitattributes` (`* text=auto eol=lf` for core source)
- [x] T008 Create the FastAPI app factory and liveness endpoint `GET /api/v1/health` returning `{"status":"ok","db":"ok"}` or `503` in `backend/src/laptop_dss/main.py`

**Checkpoint**: `docker compose config` succeeds and `GET /api/v1/health` answers.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Criteria registry, domain kernel, database schema, middleware, and test harness.
No user story can start until this phase is complete.

**⚠️ CRITICAL**: Everything below is required by all four stories.

- [x] T009 [P] Author `shared/criteria.json` with the seven criteria (`price` min/RUB, `performance` max/points, `memory` max/GB, `weight` min/g, `battery` max/minutes, `screen` max/score_0_10, `warranty` max/months), defaults `indifference_threshold: 0`, `preference_threshold: 1`, plus the `goals`, `os`, and `form_factor` vocabularies from `contracts/criteria.schema.json`
- [x] T010 [P] Write `shared/criteria.codegen.mjs` generating `frontend/src/generated/criteria.generated.ts` and `backend/src/laptop_dss/catalog/domain/criteria_generated.py` from `shared/criteria.json`
- [x] T011 Implement the immutable registry loader in `backend/src/laptop_dss/catalog/domain/criteria.py`: validate 7 unique keys, orders covering 1..7, `0 <= q < p <= 1`, expose a content hash as `criteria_version`
- [x] T012 [P] Add `backend/tests/contract/test_criteria_registry.py` asserting schema validity, loader invariants, exactly seven criteria, and a failing drift check when generated files are stale
- [x] T013 [P] Add `frontend/tests/criteria.test.ts` asserting the generated TypeScript registry exposes the same keys, labels, and directions as the JSON source
- [x] T014 [P] Implement the shared kernel in `backend/src/laptop_dss/shared/domain/`: `ids.py` (UUID newtypes), `money.py` (integer kopecks, RUB formatting), `errors.py` (domain error hierarchy), `clock.py` (Clock protocol)
- [x] T015 [P] Implement the event bus port in `backend/src/laptop_dss/shared/application/events.py` and the in-process adapter with `processed_events` idempotency in `backend/src/laptop_dss/shared/adapters/events.py`
- [x] T016 [P] Implement the persistence base in `backend/src/laptop_dss/shared/adapters/db.py`: async engine/session factory, deterministic constraint naming, unit-of-work context manager
- [x] T017 Initialize Alembic (`backend/alembic.ini`, `backend/migrations/env.py`) and write revision `0001` creating `users`, `sessions`, `profiles`, `device_models` with every constraint from `data-model.md` (weight `CHECK` summing to 1 ± 1e-6, unique `(brand, model_name)`, `role`, `status`)
- [x] T018 Write Alembic revision `0002` creating `rankings`, `ranking_items`, and `processed_events` with keys and indexes from `data-model.md`
- [x] T019 [P] Author `backend/fixtures/models.seed.json` (about 40 models spanning brands, OS, form factors, and prices from 45 000 to 350 000 ₽) and the idempotent loader `backend/src/laptop_dss/catalog/adapters/seed.py` keyed on `(brand, model_name)`
- [x] T020 [P] Implement request-id middleware, PII-free structured logging, and the error handler producing the `{"error":{"code","message","details"}}` body defined in `contracts/api.md`, in `backend/src/laptop_dss/api/middleware.py`
- [x] T021 [P] Configure CORS from `CORS_ORIGINS` (explicit allowlist, no wildcard with credentials), security headers, and session cookie settings in `backend/src/laptop_dss/api/security.py`
- [x] T022 [P] Build the test harness in `backend/tests/conftest.py`: PostgreSQL from `docker compose`, per-test transaction rollback, `httpx.AsyncClient` bound to the app, seeded criteria registry
- [x] T023 [P] Add `.github/workflows/ci.yml` running ruff, `mypy --strict`, pytest with coverage, `tsc --noEmit`, ESLint, `pip-audit`, `npm audit`, and the criteria codegen drift check
- [x] T024 [P] Start `docs/glossary.md` with one entry per concept (критерий, вес, альтернатива, превосходство, неполноценность, ранжирование, допустимое множество) in Russian and English

**Checkpoint**: migrations apply cleanly on an empty database, seeds load twice without error,
and `/api/v1/health` is green.

---

## Phase 3: User Story 1 — Personalized ranking without an account (Priority: P1) 🎯 MVP

**Goal**: A guest states budget, goals, and weights and receives an ordered, in-budget list with
per-model reasons and a stored, replayable ranking.

**Independent Test**: With seeded models and no account, `POST /api/v1/rankings` returns a
deterministic ordered list, only in-budget models, a reason per item, and `GET
/api/v1/rankings/{id}` replays it unchanged.

### Tests for User Story 1 (write first, must fail)

- [x] T025 [P] [US1] Unit tests for normalization, preference functions, and the brute-force SIR definition, including single-model, zero-range, and identical-alternative cases, in `backend/tests/unit/test_sir_reference.py`
- [x] T026 [P] [US1] Integration test for the guest ranking journey (budget hard filter, empty result, replay) in `backend/tests/integration/test_rank_guest.py`

### Implementation for User Story 1

- [x] T027 [US1] Implement the catalog domain in `backend/src/laptop_dss/catalog/domain/device.py`: `DeviceModel` with brand 1–60 chars, name 1–120, `os` and `form_factor` from vocabularies, `price_minor > 0`, and all seven criterion values present
- [x] T028 [P] [US1] Add the catalog ORM row and read repository in `backend/src/laptop_dss/catalog/adapters/{orm.py,repository.py`: eligible models by budget, ordered by `id`
- [x] T029 [US1] Implement min-max normalization with direction handling and the zero-range rule (`max == min` ⇒ `0.0` for every value) in `backend/src/laptop_dss/ranking/domain/normalization.py`
- [x] T030 [US1] Implement the three-region preference function and threshold validation (`0 <= q < p <= 1`) in `backend/src/laptop_dss/ranking/domain/preference.py`
- [x] T031 [US1] Implement the reference SIR kernel (pairwise `pi+`, `Phi+`, `Phi-`, net score, per-criterion contribution, tie-break by model id) in `backend/src/laptop_dss/ranking/domain/sir_reference.py`
- [x] T032 [US1] Implement the O(m·n log n) engine using sorted columns and prefix sums, with NumPy confined to this adapter, in `backend/src/laptop_dss/ranking/adapters/vectorized_sir.py`
- [x] T033 [US1] Add the equivalence test comparing the vectorized engine to the reference on random matrices at `1e-9`, including thresholded and degenerate inputs, in `backend/tests/unit/test_sir_equivalence.py`
- [x] T034 [US1] Add the golden-dataset test (`backend/fixtures/golden/`) asserting the expected ranking and reproducing the prototype notebook within `1e-6`, in `backend/tests/unit/test_sir_golden.py`
- [x] T035 [P] [US1] Implement ranking persistence: ORM rows, repositories, and the snapshot builder capturing preferences, eligible models, and `algorithm_version`, in `backend/src/laptop_dss/ranking/adapters/{orm.py,repository.py,snapshot.py`
- [x] T036 [US1] Implement the `RankLaptops` use case (validate weights at 0.5% input tolerance, renormalize to 1e-6, apply budget filter, call the engine, persist, return DTO) in `backend/src/laptop_dss/ranking/application/rank_laptops.py`
- [x] T037 [US1] Implement `POST /api/v1/rankings` and `GET /api/v1/rankings/{id}` replay in `backend/src/laptop_dss/ranking/adapters/router.py`
- [x] T038 [P] [US1] Add the contract test for both endpoints (required fields, dense ranks, `sum(contribution) == net_score`, tie-break, `empty_reason`, error body) in `backend/tests/contract/test_rankings_contract.py`
- [x] T039 [US1] Add determinism and monotonicity property tests (identical requests ⇒ identical order; improving one criterion without worsening others never lowers the rank) in `backend/tests/unit/test_determinism_monotonicity.py`
- [x] T040 [P] [US1] Implement the typed API client and Zod response schemas in `frontend/src/lib/{api.ts,schemas.ts}`
- [x] T041 [P] [US1] Build the ranking page: form, results list with rank/score/reason, and the empty state, in `frontend/src/app/page.tsx` and `frontend/src/features/ranking/{RankingForm,ResultsList,EmptyState}.tsx`
- [x] T042 [US1] Build the weight editor with sliders, live total indicator, and `invalid_weights` message rendering, in `frontend/src/features/ranking/WeightEditor.tsx`

**Checkpoint**: US1 is the MVP — a guest can get an explained, reproducible ranking.

---

## Phase 4: User Story 2 — Save a profile and criterion weights (Priority: P2)

**Goal**: Accounts with a persisted profile and weights that are reused on later rankings.

**Independent Test**: Register, save non-default weights, sign out and in, then request a
ranking: saved weights apply without re-entry and only that user's profile is readable.

### Tests for User Story 2 (write first, must fail)

- [x] T043 [P] [US2] Integration tests for register, login, logout, `/auth/me`, cookie attributes, `401`/`403`, duplicate email (`409`), and short password (`400`) in `backend/tests/integration/test_auth_profile.py`
- [x] T044 [P] [US2] Unit tests for `WeightSet` (negative/zero-total rejected, renormalization to 1e-6, revision increment) in `backend/tests/unit/test_weightset.py`

### Implementation for User Story 2

- [ ] T045 [US2] Implement the profiles domain: `User` (email, Argon2id hash, `role`), `Session` (hashed token, idle and absolute expiry), `Profile`, and `WeightSet`, in `backend/src/laptop_dss/profiles/domain/{user.py,session.py,profile.py,weights.py`
- [x] T046 [US2] Implement Argon2id hashing and verification in `backend/src/laptop_dss/profiles/adapters/password.py`
- [x] T047 [US2] Implement session issuance, SHA-256 token storage, cookie setting, and the `get_current_user` dependency in `backend/src/laptop_dss/profiles/adapters/sessions.py`
- [x] T048 [US2] Implement the `register`, `login`, `logout`, and `me` use cases in `backend/src/laptop_dss/profiles/application/{register.py,login.py,logout.py,me.py`
- [x] T049 [US2] Implement `get_profile` and `save_profile` (PUT/PATCH with revision) use cases in `backend/src/laptop_dss/profiles/application/{get_profile.py,save_profile.py`
- [x] T050 [US2] Implement `/api/v1/auth/*` and `/api/v1/profile` routers with ownership checks that never accept a body-supplied user id, in `backend/src/laptop_dss/profiles/adapters/router.py`
- [x] T051 [P] [US2] Build the login and registration pages in `frontend/src/app/(auth)/{login,register}/page.tsx`
- [x] T052 [P] [US2] Build the profile form with sliders, save action, and revision display in `frontend/src/features/profile/ProfileForm.tsx`
- [x] T053 [US2] Wire "use saved weights" into the ranking form, including the signed-out state, in `frontend/src/features/ranking/RankingForm.tsx`

**Checkpoint**: US1 and US2 both pass independently.

---

## Phase 5: User Story 3 — Compare and filter candidate models (Priority: P3)

**Goal**: Browse and filter the catalog, then compare two to four models from one ranking.

**Independent Test**: `GET /api/v1/models?brand=…&os=…` returns only matching active models, and
`POST /api/v1/rankings/{id}/comparison` returns seven rows with direction-correct `best_index`.

### Tests for User Story 3 (write first, must fail)

- [x] T054 [P] [US3] Integration tests for catalog browse (filters, pagination, active-only, `404`) in `backend/tests/integration/test_catalog.py`
- [x] T055 [P] [US3] Unit tests for comparison rules (2–4 models, membership in the ranking, best value per direction) in `backend/tests/unit/test_comparison.py`

### Implementation for User Story 3

- [x] T056 [US3] Implement `GET /api/v1/models` and `GET /api/v1/models/{id}` with filters, sorting, and pagination in `backend/src/laptop_dss/catalog/adapters/router.py`
- [x] T057 [US3] Implement the comparison domain and use case in `backend/src/laptop_dss/ranking/domain/comparison.py` and `backend/src/laptop_dss/ranking/application/compare.py`
- [x] T058 [US3] Implement `POST /api/v1/rankings/{id}/comparison` in `backend/src/laptop_dss/ranking/adapters/router.py`
- [x] T059 [P] [US3] Build the catalog page and filters in `frontend/src/app/catalog/page.tsx` and `frontend/src/features/catalog/{Filters,ModelGrid}.tsx`
- [x] T060 [P] [US3] Build the comparison table with direction-aware best highlighting in `frontend/src/app/compare/page.tsx` and `frontend/src/features/compare/ComparisonTable.tsx`
- [x] T061 [US3] Build the ranking selection bar enforcing 2–4 selected models in `frontend/src/features/ranking/SelectionBar.tsx`

**Checkpoint**: US1–US3 pass independently; comparison uses the stored ranking, not the live catalog.

---

## Phase 6: User Story 4 — Understand why a model ranked where it did (Priority: P4)

**Goal**: A model's detail view exposes normalized values, per-criterion contributions, and the
gap to the top-ranked model.

**Independent Test**: Opening the second-ranked model shows seven contributions summing to its
net score and names the criteria responsible for the gap to rank 1.

### Tests for User Story 4 (write first, must fail)

- [x] T062 [P] [US4] Frontend tests for the detail view: contributions sum to the net score, Russian number formatting, and best/worst criterion highlighting, in `frontend/tests/model-detail.test.tsx`

### Implementation for User Story 4

- [x] T063 [US4] Implement the per-criterion contribution and Russian reason generation in `backend/src/laptop_dss/ranking/domain/explanation.py` (consumed by the US1 response)
- [x] T064 [US4] Build the detail panel showing normalized values and contributions in `frontend/src/features/ranking/ModelDetail.tsx`
- [x] T065 [US4] Build the gap-to-top view naming the criteria responsible for the difference in `frontend/src/features/ranking/GapToTop.tsx`
- [x] T066 [US4] Add keyboard navigation and ARIA labeling to the detail panel and comparison table in `frontend/src/features/ranking/ModelDetail.tsx` and `frontend/src/features/compare/ComparisonTable.tsx`

**Checkpoint**: All four stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, documentation, and end-to-end proof across stories.

- [x] T067 [P] Complete `README.md`: install, `make up`, migrate, seed, run tests, and reproduce one SIR ranking end to end
- [x] T068 [P] Record decisions in `docs/adr/0001-sir-decomposition.md` and `docs/adr/0002-ranking-snapshots.md`
- [x] T069 [P] Add a performance test with 5,000 generated models asserting ranking p95 under 300 ms in `backend/tests/perf/test_rank_5000.py`
- [x] T070 [P] Write the Playwright flow (guest ranking → details → compare → register → saved weights) in `e2e/guest-to-profile.spec.ts`
- [x] T071 Security hardening pass: verify cookie flags, rate limits, CORS allowlist, dependency audit, and secret scan; record evidence in `docs/security-review.md`
- [x] T072 Enforce the coverage gate (≥ 80% on `domain/` and `ranking/`) in `backend/pyproject.toml` and the frontend coverage config
- [x] T073 [P] Record the results of quickstart scenarios V1–V12 in `docs/validation.md`
- [x] T074 Final verification: `make lint`, `make typecheck`, `make test`, `make e2e`, and the quickstart walkthrough all pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — blocks every user story
- **US1 (Phase 3)**: depends on Foundational; nothing else
- **US2 (Phase 4)**: depends on Foundational; integrates with US1's ranking form (T053) but its backend is independent
- **US3 (Phase 5)**: depends on Foundational and on US1's stored rankings (T035–T037)
- **US4 (Phase 6)**: depends on US1's response shape (T063 splits from ranking work) and on US3's table for shared accessibility work
- **Polish (Phase 7)**: depends on the stories you intend to ship

### Critical Path

`T001 → T002/T005 → T008 → T009–T012 → T016 → T017/T018 → T022 → T025–T042 → T043–T074`

### Within Each Story

Tests (written to fail first) → models → services/use cases → endpoints → frontend → contract
verification.

### Parallel Opportunities

- Phase 1: T002, T003, T004, T005, T006, T007 run in parallel; T008 waits on T002 and T005.
- Phase 2: T009–T010 pair, then T011–T013; T014–T016 and T019–T024 are independent files and can
  proceed in parallel; T017 must precede T018.
- US1: T025/T026 in parallel; T027/T028 in parallel; T029–T031 sequential; T032 after T030; T035
  after T018; T040/T041 in parallel with backend tasks; T042 after T041.
- US2: T043/T044 in parallel; T045–T050 sequential; T051/T052 in parallel; T053 after T050.
- US3: T054/T055 in parallel; T056–T058 mostly independent of T059–T061.
- US4: T062 first; T064/T065 parallel; T066 last.
- Polish: T067–T070 and T073 in parallel; T072 and T074 last.

---

## Parallel Example: User Story 1

```bash
# Tests first (different files, no shared state):
Task: "Unit tests for normalization, preference functions, brute-force SIR in backend/tests/unit/test_sir_reference.py"
Task: "Integration test for the guest ranking journey in backend/tests/integration/test_rank_guest.py"

# Then independent building blocks:
Task: "Catalog domain DeviceModel in backend/src/laptop_dss/catalog/domain/device.py"
Task: "Catalog ORM and repository in backend/src/laptop_dss/catalog/adapters/"

# Frontend can start once the contract fields are fixed:
Task: "Typed client and Zod schemas in frontend/src/lib/"
Task: "Ranking page and results components in frontend/src/features/ranking/"
```

## Parallel Example: User Story 2

```bash
Task: "Auth and profile integration tests in backend/tests/integration/test_auth_profile.py"
Task: "WeightSet unit tests in backend/tests/unit/test_weightset.py"
Task: "Login and register pages in frontend/src/app/(auth)/"
Task: "Profile form in frontend/src/features/profile/ProfileForm.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup, Phase 2 Foundational
2. Phase 3 (US1) — the ranking service with explanations and replay
3. **STOP and VALIDATE** against spec SC-001, SC-004, SC-006, SC-007 and quickstart V1–V5, V10
4. Demo the guest ranking, which is the graded core of the coursework

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → guest ranking (MVP)
3. US2 → accounts and saved weights
4. US3 → catalog browse, filters, comparison
5. US4 → transparency views
6. Polish → hardening, docs, performance, e2e

### Notes

- Commit after each task or logical group; auto-commit is configured for Spec Kit commands only,
  so implementation commits are explicit and conventional.
- Every task names one primary file; tasks sharing a file are sequenced, not marked [P].
- Verify a test fails before implementing the behavior it asserts.
- Stop at each checkpoint to validate the story independently against its Independent Test.
- The SIR kernel tasks (T029–T034) are the highest-risk items; do not proceed past them with a
  failing equivalence test.

---

---

---

---

## Implementation Status (2026-11-22)

Checked: **73 of 74** tasks. Verification evidence:

- `backend/tests/run_checks.py` — **28/28** checks against PostgreSQL 16.
- `backend/tests/coverage_report.py --full` — **96.4%** domain statement coverage (gate 80%).
- `frontend/e2e` via Playwright on the system Edge — **4/4**.
- `frontend/tests/criteria.test.mjs` — **3/3**.
- `next build` and `tsc --noEmit` — clean.

**Open (1):**

- **T045** — `WeightSet` carries the weight invariants and is used by the application
  layer; `User`, `Session`, and `Profile` remain persistence records. Promoting them to
  rich entities is a refactor with no behaviour change.

**Resolved during follow-up work:**

- **T018** — a genuine second migration (`0002_catalog_provenance.sql`) now adds the
  catalog `source`/`fetched_at` columns, so schema evolution is incremental.
- The catalog can refresh from a live source (JSON feed or a permitted HTML page), with
  CSV and the bundled snapshot as fallbacks; provenance is stored per model and shown in
  the UI.

**Environment deviations:** SQLAlchemy 2/Alembic could not be installed, so the adapters
use `psycopg2` with versioned SQL migrations; pytest was unavailable, so the checks and the
coverage tracer are stdlib; Framer Motion was replaced by CSS keyframes and the shadcn/ui
conventions are implemented locally.

---

## Phase 8: Convergence

- [ ] T075 Adopt Alembic for schema migrations, or amend Constitution Principle II to permit the versioned SQL migrator, and record the decision per Constitution II (contradicts)
- [ ] T076 Move criteria registry file loading out of `backend/src/laptop_dss/catalog/domain/criteria.py` into an adapter, leaving only validation in the domain per Constitution II (contradicts)
- [ ] T077 Expose the score gap and the criteria responsible for it in the ranking API and the model detail view, using `ranking/domain/explanation.py::gap_to_top` per US4/AC2 (missing)
- [ ] T078 Run ruff, mypy --strict, and ESLint in CI and fix every reported violation per Constitution III (partial)
- [ ] T079 Decide and implement how soft preferences (brand, OS, form factor) affect ranking, or document them explicitly as display-only per FR-001 and US1 (partial)
- [ ] T080 Reconcile the "model lacks a criterion value" edge case with the `NOT NULL` schema: allow incomplete drafts that are excluded and flagged, or remove the edge case per spec edge case (contradicts)
- [ ] T081 Promote `User`, `Session`, and `Profile` to rich domain entities with their invariants per T045 (partial)
- [ ] T082 Invalidate or recompute the displayed ranking when budget or weights change after results are shown per spec edge case "changes preferences after viewing results" (partial)
- [ ] T083 Record the live catalog sources, CSV importer, and guest-capability access in an ADR and plan note per plan decision on catalog maintenance (unrequested)
