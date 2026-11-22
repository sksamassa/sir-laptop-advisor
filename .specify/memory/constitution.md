# Laptop Selection DSS (SIR) Constitution

Scope: a decision-support web service that ranks laptops for study and work using the SIR
(Superiority and Inferiority Ranking) multi-criteria method over seven criteria: price, CPU
performance, RAM, weight, battery life, screen quality, and warranty. The system stores user
profiles with per-criterion weights and explains every ranking it produces. Principles below
apply to all backend, frontend, data, and research artifacts in this repository, including the
prototype notebook in `_notebook/`.

## Core Principles

### I. Security & Privacy by Design (NON-NEGOTIABLE)

The service holds personal profiles and steers purchase decisions, so security is a
precondition for shipping, not a hardening phase.

- Passwords MUST be hashed with Argon2id (bcrypt cost >= 12 only as a documented fallback);
  plaintext or reversible storage of credentials is prohibited.
- Secrets (database DSN, signing keys, API tokens) MUST come from environment variables or a
  secret store. `.env` files MUST be git-ignored, and secrets MUST NOT appear in notebook
  cells, commits, logs, fixtures, or screenshots.
- Every endpoint that reads or mutates a profile MUST authenticate the caller and authorize
  ownership. The service MUST derive the user identity from the session or token and MUST NOT
  trust a client-supplied user identifier.
- All inbound data MUST be validated at the trust boundary: Zod schemas on the frontend,
  typed Pydantic models on the backend; unknown fields MUST be rejected, not ignored.
- SQL MUST be parameterized through SQLAlchemy/asyncpg. String-concatenated or f-string SQL is
  prohibited.
- Sessions MUST use `HttpOnly`, `SameSite` cookies or short-lived tokens over HTTPS; CORS MUST
  use an explicit origin allowlist and MUST NOT combine wildcard origins with credentials.
- Logs and error responses MUST NOT contain PII (email, budget, brand preferences) or stack
  traces in production. User-visible errors MUST be generic; diagnostics stay server-side.
- Dependency and secret scanning (`pip-audit`, `npm audit`, secret scan) MUST run in CI, and
  any high or critical finding blocks merge until resolved or explicitly waived in writing.

Rationale: a ranking service that leaks or corrupts profiles fails both its users and its
course requirements; these controls are cheap to add early and expensive to retrofit.

### II. Maintainability Through Bounded Contexts

The coursework requires DDD and event-driven architecture, so module boundaries are structural
commitments, not style preferences.

- Code MUST be organized by bounded context (for example `profiles/`, `catalog/`, `ranking/`),
  each split into domain, application (use cases), and adapters layers.
- The domain layer MUST NOT import frameworks or I/O: no FastAPI, SQLAlchemy, pandas, or HTTP
  clients inside `domain/`. Domain rules MUST be testable with no database and no network.
- Contexts MUST NOT import each other's internals. Cross-context collaboration goes through
  explicit ports, published DTOs, or domain events; a shared kernel is allowed only if small,
  documented, and stable.
- Each use case MUST be one named function or class with explicit typed input and output DTOs.
  Business logic MUST NOT live in route handlers, ORM models, or React components.
- Persistence MUST go through repository ports. Schema changes MUST be applied through
  versioned, ordered migrations that are recorded once and replayed identically. Alembic is
  the default tool; where Alembic cannot be installed, a repository-owned SQL migrator with
  a `schema_migrations` ledger is permitted (see ADR 0004). `Base.metadata.create_all()` and
  manual DDL are prohibited outside tests.
- Event handlers MUST be idempotent and MUST record processed event identifiers so replays do
  not double-apply ranking or profile updates.
- Every public module MUST state its purpose and owning context in a module docstring; every
  magic number MUST become a named constant with units.

Rationale: the ranking method will change and criteria will be added; clear seams keep those
changes localized and keep the DDD/event architecture requirement genuinely satisfied.

### III. Code Quality & Type Safety

Readable, typed, and tested code is the baseline quality bar for this project.

- Python MUST pass `ruff` (lint and format) and `mypy --strict` on `domain/` and
  `application/`; the frontend MUST pass `tsc --noEmit`, ESLint, and Prettier.
- Every function and method signature MUST be annotated. Use of `Any`, `# type: ignore`, or
  `@ts-ignore` MUST carry an adjacent comment explaining why the escape is necessary.
- Automated tests are mandatory: `pytest` for backend and model logic, a frontend test runner
  for user-facing flows. Domain and ranking modules MUST keep line coverage >= 80%.
- `print()` MUST NOT be used for diagnostics; use structured logging with levels, and log
  identifiers rather than payloads.
- Dead code, commented-out blocks, and unused dependencies MUST be removed before merge.
- Domain vocabulary MUST match `docs/glossary.md` one-to-one across backend, database columns,
  API fields, and UI copy; a concept MUST have exactly one name per layer.
- Commits MUST follow Conventional Commits and stay focused; a pull request SHOULD stay under
  400 changed lines and MUST be self-reviewed against this constitution before merge.

Rationale: type errors and ad-hoc naming are the dominant defect sources in a bilingual
(Python/TypeScript) coursework service that must be defended verbally.

### IV. SIR Method Correctness & Explainability

The system's credibility rests on implementing SIR correctly and showing the reasoning.

- The ranking pipeline MUST implement the SIR method as defined in the reference text
  (`материалы/Jason_Papathanasiou,_Nikolaos_Ploskas_Multiple_Criteria_Decision.pdf`): per
  criterion normalization by direction, pairwise superiority and inferiority indices,
  aggregation into SIR outranking scores, and a final total ranking.
- Simplified substitutes (plain weighted sum, TOPSIS, ELECTRE hybrids) MUST NOT be labeled or
  presented as SIR. Any approximation MUST be documented, named as an approximation, and
  approved in `plan.md`.
- The seven criteria C1..C7 and their optimization directions MUST be defined once, in a single
  machine-readable registry consumed by both backend and frontend; adding or reordering a
  criterion MUST require editing that one file plus tests.
- User weights MUST be validated as non-negative, normalized to 1 within 1e-6, and persisted
  with the profile revision that produced a ranking.
- Every ranking response MUST be explainable: it MUST include normalized criterion values and
  each alternative's contribution to its score, and the UI MUST surface why a laptop placed
  where it did.
- Ranking MUST be deterministic: identical dataset plus identical weights yields an identical
  order, and tie-breaking MUST be explicit (stable, documented ordering by model identifier).
- Degenerate inputs (single alternative, zero range on a criterion, identical alternatives)
  MUST be handled explicitly and covered by tests; `ZeroDivisionError` and `NaN` ordering MUST
  never reach users.

Rationale: a decision-support tool that cannot justify its output is indistinguishable from a
random list, and the SIR implementation itself is the graded artifact.

### V. Verified Data & Reproducibility

Results must be reproducible by a reviewer on a clean machine, from stored data, without
tribal knowledge.

- Laptop data and the criteria registry MUST be loaded through versioned, idempotent seeds or
  migrations. Manual database edits and undocumented CSV swaps are prohibited.
- Every algorithm change MUST ship with a golden-dataset test asserting the expected ranking,
  plus a monotonicity test: improving one criterion without worsening any other MUST NOT lower
  an alternative's rank.
- The notebook in `_notebook/` is for exploration only. Production logic MUST live in the
  backend package and MUST reproduce the validated notebook results within 1e-6 on the
  reference dataset.
- The environment MUST be reproducible: pinned dependencies in `pyproject.toml`/lockfile,
  documented Python and Node versions, and a single documented command (Docker Compose or
  equivalent) that starts database, API, and web.
- `README.md` MUST state how to install, run tests, seed data, and reproduce one worked SIR
  ranking end to end.
- Scientific and library figures used in the report MUST be generated from the repository
  state, not hand-edited, and their source command MUST be recorded next to them.

Rationale: reproducibility is the difference between an auditable method implementation and a
demo that only works on the author's machine.

## Technology & Data Constraints

- Backend language: Python 3.12+ with FastAPI and Pydantic v2. Persistence uses SQLAlchemy
  2.x (async) and Alembic where those packages are installable; where they are not, the
  `psycopg2` repository adapters and the versioned SQL migrator are the sanctioned
  alternative (ADR 0004).
- Frontend: Next.js with TypeScript, TailwindCSS, shadcn/ui, Zod, and Framer Motion. Server
  state MUST be fetched through typed API clients; secrets MUST never be embedded in the
  browser bundle.
- Analytics, scoring, and numerical routines MUST use `numpy`/`pandas` only inside the ranking
  adapter, never as a substitute for explicit domain rules.
- Data contract: seven criteria with fixed directions (price and weight minimized, the rest
  maximized); profile weights normalized to 1; all timestamps stored in UTC; money stored as
  integer minor units or `Decimal`, never `float`.
- The repository MUST remain runnable without proprietary services; every external dependency
  MUST have a documented free-tier or local substitute.

## Development Workflow & Quality Gates

- Work MUST follow Spec Kit order: constitution, then `/speckit-specify`, `/speckit-plan`,
  `/speckit-tasks`, then `/speckit-implement`. Implementation MUST NOT start before the spec
  and plan exist and pass their checks.
- `plan.md` MUST include a Constitution Check table naming each principle and how the plan
  satisfies it; any deviation MUST appear in Complexity Tracking with justification, owner,
  and expiry.
- Pull request gate: lint, typecheck, tests, coverage threshold, migration check, and secret
  scan MUST all pass. A reviewer MUST verify the Security and SIR Correctness principles
  explicitly.
- Changes touching authentication, authorization, secrets, or personal data MUST include a
  short threat note in the pull request describing the failure mode considered.
- Definition of done: feature works end to end against seeded data, is tested, is documented,
  and demos one ranking with visible explanation.
- The constitution MUST be re-read at the end of each feature and before final coursework
  submission; drift MUST be corrected by amendment rather than by silent exception.

## Governance

This constitution supersedes conflicting local habits, notebook shortcuts, and informal course
conventions. When guidance conflicts, this document wins until amended.

- Amendments MUST be proposed through `/speckit-constitution` with the exact replacement text,
  the rationale, and the principles affected. Ratification belongs to the project author
  (student maintainer); a proposed amendment is not binding until ratified and the Sync Impact
  Report is reviewed.
- Versioning follows semantic versioning: MAJOR for incompatible governance changes, principle
  removal, or redefinition of meaning; MINOR for a new principle or section, or materially
  expanded guidance; PATCH for clarifications, wording, and typo fixes that do not change
  obligations.
- Compliance is reviewed at every plan (`Constitution Check`), every pull request, and every
  feature close-out. A violation blocks merge; an intentional exception MUST be recorded in
  `plan.md` Complexity Tracking with justification, approver, and expiry date.
- Complexity MUST be justified in `plan.md`; simplicity is the default and unjustified layers,
  abstractions, or dependencies MUST be removed.
- This document is the runtime source of truth for development practice; `.specify/` artifacts
  MUST NOT redefine its rules. Related guidance belongs in `docs/` and `README.md`.

**Version**: 1.1.0 | **Ratified**: 2026-11-22 | **Last Amended**: 2026-11-22
