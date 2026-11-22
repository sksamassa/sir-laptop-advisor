# Implementation Plan: SIR-Based Laptop Selection Service

**Branch**: `001-sir-laptop-selection` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-sir-laptop-selection/spec.md`

## Summary

Build a Russian-language web service that ranks laptops for a shopper's budget, usage goals,
and per-criterion weights using the SIR (Superiority and Inferiority Ranking) multi-criteria
method, with per-criterion explanation of every result. The backend is a Python 3.12 /
FastAPI / PostgreSQL application organized into three bounded contexts (`profiles`,
`catalog`, `ranking`); the frontend is a Next.js/TypeScript app. The SIR kernel is exact and
deterministic: pairwise superiority/inferiority indices with per-criterion preference
functions, aggregated to a net flow, computed in O(m·n log n) per ranking by per-criterion
decomposition instead of an O(n²) matrix. Every presented ranking is stored with its
preference and catalog snapshots plus an algorithm version so it can be reproduced.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript 5.x on Node.js 20 LTS (frontend)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic, asyncpg,
argon2-cffi, NumPy (ranking adapter only), pytest + pytest-asyncio + httpx; Next.js (App
Router), React, TailwindCSS, shadcn/ui, Zod, Framer Motion, Vitest + Testing Library

**Storage**: PostgreSQL 16 (single instance); criteria registry stored as a versioned JSON
file in the repository, not in the database

**Testing**: pytest (unit, integration, contract), Playwright (end-to-end), Vitest + Testing
Library (frontend); ruff, mypy `--strict` on `domain/` and `application/`, ESLint, `tsc
--noEmit`

**Target Platform**: Linux containers via Docker Compose for local use and demonstration;
modern desktop and mobile browsers (latest two versions of Chrome, Safari, Firefox, Edge)

**Project Type**: web service — JSON API backend plus server-rendered/SPA frontend

**Performance Goals**: ranking response p95 ≤ 300 ms for 5,000 eligible models; catalog read
p95 ≤ 200 ms; first contentful paint ≤ 2 s on a typical laptop and ≤ 3 s on a typical
smartphone

**Constraints**: exact SIR (no weighted-sum substitute), deterministic ordering, per-criterion
explainability in every ranking response, Russian-only UI, RUB prices, single-node deployment,
no browser-side secrets

**Scale/Scope**: ≤ 5,000 device models, ≤ 1,000 registered users, ~15 screens, one feature
release

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Plan evidence | Status |
|-----------|------|---------------|--------|
| I. Security & Privacy by Design | Auth, secrets, ownership, input validation, parameterized SQL, CORS, PII-free logs, dependency scanning | Argon2id passwords; opaque 256-bit session tokens stored hashed, delivered in `HttpOnly; SameSite=Lax` cookies; every profile/ranking read derives the user from the session and never trusts a body-supplied user id; Pydantic v2 on the backend and Zod on the frontend reject unknown fields; SQLAlchemy Core/ORM only; explicit CORS allowlist; structured logs with ids, not emails; `pip-audit`/`npm audit` gates | PASS |
| II. Maintainability Through Bounded Contexts | Context-first layout, framework-free domain, ports for cross-context work, Alembic-only schema changes, idempotent handlers | `backend/src/laptop_dss/{profiles,catalog,ranking}` each split into `domain/`, `application/`, `adapters/`; `domain/` imports no FastAPI/SQLAlchemy/pandas; use cases are single classes with typed DTOs; repositories are ports; Alembic owns DDL; in-process event bus with a `processed_events` table for idempotency | PASS |
| III. Code Quality & Type Safety | Lint/format/type gates, coverage, glossary, Conventional Commits | ruff + ruff format; `mypy --strict` on `domain/` and `application/`; `tsc --noEmit`; domain+ranking coverage ≥ 80%; `docs/glossary.md` seeded from the criteria registry; commit messages already conventional via the git extension | PASS |
| IV. SIR Method Correctness & Explainability | Full SIR, one criteria registry, weight contract, contributions, deterministic tie-break, degenerate-input tests | Exact SIR with per-criterion preference functions and net flow; single `shared/criteria.json` registry consumed by backend and code-generated for the frontend; weights validated at the 0.5% input tolerance then renormalized so the stored sum is 1 within 1e-6; responses carry normalized values and per-criterion contributions; ties break by model id; degenerate cases covered by tests | PASS |
| V. Verified Data & Reproducibility | Idempotent seeds, golden + monotonicity tests, notebook as prototype, pinned env, one-command bring-up | Versioned idempotent seed migrations; golden-dataset ranking test plus a monotonicity property test; notebook stays a prototype and its output is reproduced by the service within 1e-6; pinned dependencies and lockfiles; `docker compose up` brings up database, API, and web; rankings stored with snapshots and `algorithm_version` for replay | PASS |

**Result**: all five gates pass. No violations to justify.

**Open conflict resolved in the plan**: the spec allows a 0.5% weight tolerance while
Principle IV requires 1e-6. Resolution: the 0.5% tolerance applies to user-entered input;
the domain renormalizes weights to sum exactly to 1 before ranking, and asserts 1e-6
internally. No constitutional change needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-sir-laptop-selection/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── api.md              # HTTP interface contract
│   └── criteria.schema.json # Criteria registry contract
└── tasks.md             # Phase 2 output (/speckit-tasks - not created here)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── alembic.ini
├── migrations/                 # Alembic revisions (schema + seeds)
├── src/laptop_dss/
│   ├── main.py                 # FastAPI app factory, composition root
│   ├── config.py               # settings from environment, no secrets in code
│   ├── shared/
│   │   ├── domain/             # ids, money, errors, clock port
│   │   ├── application/        # event bus port, unit-of-work port
│   │   └── adapters/           # SQLAlchemy session, in-process bus, clock
│   ├── profiles/
│   │   ├── domain/             # User, Session, Profile, WeightSet rules
│   │   ├── application/        # register, login, logout, save/get profile use cases
│   │   └── adapters/           # ORM models, repositories, auth router, hasher
│   ├── catalog/
│   │   ├── domain/             # DeviceModel, Criterion, CriteriaRegistry
│   │   ├── application/        # list models, get model, maintain catalog
│   │   └── adapters/           # ORM, repository, catalog router
│   └── ranking/
│       ├── domain/             # sir_reference.py, scoring, explanation, DTOs
│       ├── application/        # rank use case, replay, comparison
│       └── adapters/           # vectorized_sir.py (NumPy), persistence, router
├── fixtures/
│   ├── criteria.json -> ../../shared/criteria.json  (loaded, not copied)
│   ├── models.seed.json        # representative catalog
│   └── golden/                 # golden dataset + expected ranking
└── tests/
    ├── unit/                   # domain + SIR kernels
    ├── integration/            # use cases against a real PostgreSQL
    └── contract/               # API responses match contracts/api.md
frontend/
├── package.json
├── src/
│   ├── app/                    # App Router routes: /, /profile, /ranking, /compare, /catalog, /login
│   ├── features/               # profile, ranking, compare, catalog, auth
│   ├── components/ui/          # shadcn/ui primitives
│   ├── lib/                    # typed API client, Zod schemas, formatting (RUB, ru-RU)
│   └── generated/              # criteria.generated.ts from shared/criteria.json
└── tests/
shared/
├── criteria.json               # single criteria registry (source of truth)
└── criteria.codegen.mjs        # generates frontend TS types + backend constants
docs/
├── glossary.md                 # one term per concept, ru/en
└── adr/                        # architecture decision records
docker-compose.yml
README.md
```

**Structure Decision**: web application layout (backend + frontend) with context-first
packages inside each side. `shared/criteria.json` is the single authored definition of the
seven criteria; the frontend TypeScript module and the backend constants are generated from
it by `shared/criteria.codegen.mjs`, so adding a criterion touches one authored file plus
tests and a migration for the new stored value.

## Complexity Tracking

> No constitutional violations. Two design choices are recorded here because they add
> structure that a reviewer will notice, and each is justified by a requirement.

| Choice | Why Needed | Simpler Alternative Rejected Because |
|--------|------------|--------------------------------------|
| Ranking stores `catalog_snapshot` and `preference_snapshot` as JSONB | FR-016 and SC-008 require reproducing a shown ranking exactly, including after catalog edits | Recomputing from live tables would silently change historical results after any catalog update |
| `shared/` kernel (ids, money, clock, errors) shared by all three contexts | Money and identifiers are needed in every context and duplicating them would diverge | A full shared domain model would couple contexts; the kernel is deliberately limited to value types and ports |

## Phase 0: Research Output

See [research.md](./research.md). All technical unknowns are resolved there; no
`NEEDS CLARIFICATION` markers remain.

## Phase 1: Design Output

- [data-model.md](./data-model.md) — entities, tables, validation rules, snapshot strategy.
- [contracts/api.md](./contracts/api.md) — HTTP endpoints, payloads, status codes, auth rules.
- [contracts/criteria.schema.json](./contracts/criteria.schema.json) — criteria registry schema.
- [quickstart.md](./quickstart.md) — runnable validation scenarios mapped to success criteria.

## Post-Design Constitution Re-check

| Principle | Post-design status | Notes |
|-----------|--------------------|-------|
| I. Security | PASS | Session-token storage hashed; ownership resolved from session in the ranking and profile use cases; API contract forbids body-supplied user ids |
| II. Maintainability | PASS | Data model and contracts keep `ranking` dependent on `catalog` only through a published DTO, not on its tables |
| III. Code Quality | PASS | Contracts give the API test surface; coverage gate applies to the SIR kernel and domain rules |
| IV. SIR Correctness | PASS | Data model records `algorithm_version` and per-criterion contributions; tie-break rule stated in the contract |
| V. Reproducibility | PASS | Snapshots + version make replay exact; seeds are idempotent migrations |

## Risks and Mitigations

- **Min-max normalization is pool-dependent**: adding a model can reorder an old ranking.
  Mitigated by storing snapshots per ranking (replay is stable) and documenting that a live
  ranking always reflects the current catalog.
- **Threshold tuning changes results**: preference thresholds live in the registry and are
  versioned through `algorithm_version`; changing defaults requires a new algorithm version
  and a regenerated golden dataset.
- **O(m·n log n) derivation must equal the pairwise definition**: a brute-force O(n²·m)
  reference implementation is kept for tests and compared on random matrices at 1e-9.
- **OneDrive-synced workspace on Windows**: file watching and Docker volume mounts can be
  slow; the compose file mounts source read-only and relies on rebuilds, and the quickstart
  documents running from a local clone if hot reload misbehaves.
