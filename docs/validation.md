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
ok    guest ranking is ordered, budget-bounded, and explained
ok    guest ranking is replayable and comparable by its id
ok    empty budget returns an empty state, not an error
ok    invalid weights are rejected with 400 invalid_weights
ok    unknown fields are rejected with 422
ok    register, login, profile save, and partial weight change
ok    ranking with saved weights uses them and is replayable
ok    replay is stable after the catalog changes
ok    ranking filters preserve the stored SIR order
ok    comparison: 2-4 models, direction-aware best values
ok    maintainer can add, retire, and republish a model
ok    logout invalidates the session
ok    event handlers are idempotent on replay

23 checks passed, 0 failed
```

## UI validation

- `cd frontend && npx tsc --noEmit` — clean.
- `npm run build` — 4 routes, prerendered; First Load JS 103–110 kB.
- Interactive flow in headless Edge over the DevTools protocol
  (`frontend/scripts/capture.mjs`): submit → 8 ranked cards with Russian reasons →
  "Почему так?" contribution panel → select 3 → comparison dialog with
  direction-aware best values. Mobile 390 px checked on `/catalog` and `/`.
- Screens: `01-form`, `02-results`, `03-details`, `04-selected`, `05-compare`,
  `06-mobile-catalog` (captured to the temp folder; not committed).

**Not yet validated**: automated browser suite (Playwright), ESLint, and a full
accessibility audit.

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
