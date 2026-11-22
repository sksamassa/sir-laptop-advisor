# Validation record

Date: 2026-11-22. Environment: Windows, Python 3.12.2, PostgreSQL 16.2.
Command: `cd backend && python tests/run_checks.py` (stdout below, abridged).

```text
Setting up a clean schema and demo data ...
ok    criteria registry is valid
ok    normalization respects direction and zero range
ok    preference function regions
ok    vectorized engine equals the pairwise definition
ok    golden price ranking reproduces 1.5 / 0 / -1.5
ok    ranking is deterministic
ok    improving a criterion never lowers a rank
ok    weight contract: 0.5% input tolerance, exact normalization
ok    health and criteria endpoints
ok    catalog listing, filtering, pagination
ok    catalog can be refreshed from a CSV of real prices
ok    guest ranking is ordered, budget-bounded, and explained
ok    guest ranking is replayable and comparable by its id
ok    empty budget returns an empty state, not an error
ok    a student budget of 30 000 RUB finds affordable models
ok    a 20 000 RUB budget still returns laptops
ok    invalid weights are rejected with 400 invalid_weights
ok    unknown fields are rejected with 422
ok    register, login, profile save, and partial weight change
ok    ranking with saved weights uses them and is replayable
ok    replay is stable after the catalog changes
ok    ranking filters preserve the stored SIR order
ok    comparison: 2-4 models, direction-aware best values
ok    maintainer can add, retire, and republish a model
ok    logout invalidates the session
ok    domain validation and error branches
ok    event handlers are idempotent on replay

27 checks passed, 0 failed
```

## UI validation

- `cd frontend && npx tsc --noEmit` — clean.
- `npm run build` — 4 routes, prerendered; First Load JS 103–110 kB.
- Interactive flow in headless Edge over the DevTools protocol
  (`frontend/scripts/capture.mjs`): submit → 8 ranked cards with Russian reasons →
  "Почему так?" contribution panel → select 3 → comparison dialog with
  direction-aware best values. Mobile 390 px checked on `/catalog` and `/`.
- Screens: `01-form`, `02-results`, `03-details`, `04-selected`, `05-compare`,
  `06-mobile-catalog`, `07-budget-30000`, `08-budget-20000`, `09-budget-10000`.
  The last three prove the market-range fix: 30 000 ₽ and 20 000 ₽ both return
  ranked laptops (the catalog now starts at 15 990 ₽), and 10 000 ₽ explains that
  the cheapest model is 15 990 ₽.

**Not yet validated**: ESLint and a full accessibility audit.

## Automated browser tests

`cd frontend && npx playwright test` (Playwright drives the system Edge, no browser
download needed):

```text
4 passed (14.0s)
  ok  a guest receives a ranked, explained shortlist
  ok  three models can be compared from the ranking
  ok  catalog lists models and filters by operating system
  ok  profile asks for sign-in when anonymous
```

Generated criteria constants are checked separately:
`node frontend/tests/criteria.test.mjs` → **3/3** (keys, labels, directions,
threshold pairs, exactly seven criteria in order).

## Coverage

`python backend/tests/coverage_report.py --full` (standard-library tracer, since
pytest-cov cannot be installed):

```text
100.0%  catalog/domain/device.py            (42/42)
 90.8%  catalog/domain/criteria.py          (79/87)
100.0%  ranking/domain/normalization.py     (29/29)
100.0%  ranking/domain/preference.py        (13/13)
 98.4%  ranking/domain/sir_reference.py     (61/62)
 95.1%  ranking/domain/explanation.py       (39/41)
 97.1%  profiles/domain/weights.py          (34/35)
100.0%  shared/domain/errors.py             (39/39)
100.0%  shared/domain/ids.py                (18/18)
 85.7%  shared/domain/money.py              (12/14)

domain statement coverage: 96.3% (366/380) — PASS (gate 80%)
```

## Performance (SC-004)

`cd backend && python tests/perf/test_rank_5000.py`:

```text
models: 5000 (built in 146 ms)
ranking runs: [215, 209, 244, 220, 254] ms
median: 219.5 ms
p95:    260.9 ms
PASS
```

## What each group proves

- **SIR correctness** (`vectorized engine equals the pairwise definition`): the
  `O(m·n log n)` engine and the `O(n²·m)` reference produce the same order,
  net scores, flows, and contributions within `1e-9` on random matrices.
- **Golden case**: with only price active, three models at 10 000 / 20 000 /
  30 000 ₽ yield net scores `1.5 / 0.0 / -1.5`, which is the hand-computed
  `3v - Σv` value.
- **Constitution gates**: determinism (`SC-007`), monotonicity (Principle IV),
  weight contract (0.5% input tolerance → exact normalization), strict input
  validation (`extra="forbid"`), ownership and role checks.
- **Spec coverage exercised over HTTP**: FR-003, FR-005, FR-006, FR-007,
  FR-008, FR-009 (display filters preserve stored order), FR-010, FR-011 …
  FR-016, plus the empty-budget and invalid-weight edge cases.

## Not yet validated

- Frontend screens (Next.js not installable offline).
- `ruff`, `mypy --strict`, `pytest`, coverage gate (packages unavailable).
- Playwright end-to-end flow and the 5 000-model performance check.
