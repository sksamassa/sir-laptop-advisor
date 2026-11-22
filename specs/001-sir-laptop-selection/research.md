# Phase 0 Research: SIR-Based Laptop Selection Service

**Feature**: `001-sir-laptop-selection` | **Date**: 2026-11-22

All technical unknowns from the plan's Technical Context are resolved below. Each entry
records the decision, why it was chosen, and what was rejected.

## R1. SIR formulation and exact, fast computation

**Decision**: Implement SIR as defined for additive per-criterion preference functions.
Normalize every criterion to `[0, 1]` with direction applied so that larger is always better.
For criterion `j` with weight `w_j` and normalized values `v_j`, define the preference
function over a difference `d = v_j(a) - v_j(b)`:

```text
p_j(d) = 0                       if d <= q_j
p_j(d) = (d - q_j) / (p_j - q_j) if q_j < d < p_j
p_j(d) = 1                       if d >= p_j
```

The pairwise superiority index, global superiority flow, inferiority flow, and net score are:

```text
pi+(a, b) = sum_j w_j * p_j(v_j(a) - v_j(b))
Phi+(a)   = sum_{b != a} pi+(a, b)
Phi-(a)   = sum_{b != a} pi+(b, a)
Score(a)  = Phi+(a) - Phi-(a)          # rank by descending Score
```

Because `pi+` is additive over criteria, `Phi+` decomposes into independent one-dimensional
sums, one per criterion:

```text
Phi+(a) = sum_j w_j * S_j(v_j(a)),   S_j(x) = sum_b p_j(x - s_b)
```

where `s_1 <= ... <= s_n` is the sorted column for criterion `j`. Sorting `s` once and
keeping prefix sums lets `S_j(x)` be evaluated with two binary searches, splitting the sorted
values into the three `p_j` regions. Total cost is `O(m * n log n)` for `n` models and `m`
criteria — no pairwise matrix is ever materialized. The result is identical to the
`O(n^2 * m)` definition (not an approximation); a brute-force reference implementation is
kept in tests and compared on random matrices at `1e-9`.

**Rationale**: The spec requires exact SIR, results within 3 seconds for 5,000 models, and
reproducible replay. The decomposition satisfies all three and removes the memory wall.

**Alternatives considered**:
- *Dense pairwise matrix*: `5000^2 * 7` float64 values ≈ 1.4 GB and seconds of compute.
  Rejected on memory and latency.
- *NumPy broadcast in chunks*: workable but still materializes millions of pairs per
  criterion; more code, more memory, no benefit over the prefix-sum form.
- *Weighted sum*: violates Principle IV and misrepresents the method.

**Reference**: Papathanasiou & Ploskas, *Multiple Criteria Decision Analysis*
(`материалы/Jason_Papathanasiou,_Nikolaos_Ploskas_Multiple_Criteria_Decision.pdf`), SIR
chapter; Xu (2001) for the original formulation. The prototype notebook implements the
special case `q_j = 0, p_j = 1`; the service generalizes it and keeps that case as the
default so notebook results reproduce within `1e-6`.

## R2. Normalization strategy

**Decision**: Min-max normalization per criterion over the *eligible* candidate set (models
that pass budget and filters), direction-aware: for maximized criteria `(x - min)/(max -
min)`, for minimized criteria `(max - x)/(max - min)`. If `max == min`, every value becomes
`0.0`, so that criterion contributes no differences and cannot destabilize the ranking.

**Rationale**: Min-max is what the prototype does, keeps every criterion on the same
`[0, 1]` scale where thresholds have meaning, and needs no external anchors.

**Alternatives considered**: z-score (unbounded, makes `q`/`p` units arbitrary); fixed
per-criterion scales (requires authoritative minima/maxima for a changing catalog);
normalizing against budget only for price (asymmetric treatment of the other six).

**Consequence accepted**: normalization is pool-dependent, so a live ranking reflects the
current candidate set. Historical results stay stable because each ranking stores its
snapshot (R7).

## R3. Weight contract

**Decision**: The API accepts weights as non-negative decimals or percentages with a
`0.5%` tolerance on the total (spec FR-003). The domain then renormalizes them so the sum is
`1` within `1e-6` (constitution Principle IV) before any ranking, and rejects zero-total or
negative inputs. Stored weights are `numeric(9,6)`.

**Rationale**: Users reason in percentages and will not hit an exact 100.000%; the
constitution's `1e-6` requirement is about the internal invariant, not user input.

**Alternatives considered**: strict 100.000% input (hostile to users, fails FR-003);
no normalization (floating error accumulates into scores).

## R4. Preference thresholds

**Decision**: Thresholds `q_j` (indifference) and `p_j` (preference) live in
`shared/criteria.json` per criterion, validated as `0 <= q_j < p_j <= 1`. Defaults are
`q_j = 0` and `p_j = 1` (pure linear preference), which reproduces the prototype. Narrower
thresholds can be set per criterion without code changes.

**Rationale**: Defaults keep behavior explainable and equal to the validated prototype;
the registry leaves room to sharpen discrimination once real catalog data is available.

**Alternatives considered**: hard-coding one global threshold pair (hides the decision);
expert-tuning per criterion now (no data to justify values, and it would change the golden
results).

## R5. Authentication and session handling

**Decision**: Email + password accounts, passwords hashed with Argon2id. On login the server
issues a 256-bit random opaque session token, stores only its SHA-256 digest in `sessions`,
and sets it in an `HttpOnly; SameSite=Lax; Secure` cookie. Idle timeout 7 days, absolute
lifetime 30 days. Logout deletes the session row. Authorization always resolves the user from
the session; no endpoint accepts a user id from the request body or query.

**Rationale**: Opaque tokens are revocable server-side and need no signing-key rotation;
constitution Principle I forbids client-trusted identity.

**Alternatives considered**: JWT (revocation requires extra state, key management);
OAuth/social login (out of scope for the coursework); local storage tokens (XSS exposure,
forbidden by Principle I).

## R6. Single criteria registry

**Decision**: `shared/criteria.json` is the only authored definition of the seven criteria:
key, Russian label, direction, unit, thresholds, and display decimals. A small Node script
`shared/criteria.codegen.mjs` generates `frontend/src/generated/criteria.generated.ts` and
`backend/src/laptop_dss/catalog/domain/criteria_generated.py`. Both are committed and
checked by a test that regenerates them and fails on drift. The registry is validated by
`contracts/criteria.schema.json` at build time and by a Pydantic model at load time.

**Rationale**: Principle IV requires one machine-readable registry; codegen keeps the
frontend and backend in lockstep without a shared runtime service.

**Alternatives considered**: a `criteria` database table (schema change per addition, and
the constitution wants one file); duplicating constants in TypeScript and Python (drift,
explicitly forbidden).

## R7. Ranking persistence and replay

**Decision**: Each ranking stores: normalized preference snapshot (weights, goals, budget,
filters), the eligible-model snapshot (id, name, price, seven raw values, in deterministic
id order), `algorithm_version` (for example `sir-1.0.0`), and computed `ranking_items`
(rank, model id, `phi_plus`, `phi_minus`, `net_score`, per-criterion contributions). Replay
returns the stored rows after verifying the stored algorithm version is readable.

**Rationale**: FR-016 and SC-008 require reproducing a displayed ranking after the catalog
changes; recomputation would silently change history.

**Alternatives considered**: event sourcing the catalog (correct but far more machinery);
storing only a catalog version counter (breaks when records are retired without versioning).

## R8. Domain events

**Decision**: An in-process event bus dispatches domain events (`ProfileSaved`,
`ModelPublished`, `ModelRetired`, `RankingComputed`). Handlers are synchronous subscribers
registered in the composition root; each handler records its `(event_id, handler)` pair in
`processed_events` before applying effects, and skips already-processed pairs.

**Rationale**: The coursework requires DDD with an event-driven flavor; Principle II requires
idempotent handlers. A broker and outbox are unnecessary for a single-node coursework
deployment.

**Alternatives considered**: outbox + broker (operational weight with no requirement);
direct calls without events (fails the architecture requirement).

## R9. API shape and frontend data flow

**Decision**: JSON over HTTPS under `/api/v1`, resource-oriented, with an OpenAPI document
generated by FastAPI and checked against `contracts/api.md` in a contract test. The frontend
uses Next.js App Router: server components fetch through a typed client on the server,
interactive forms validate with Zod on the client and revalidate on the server. No API base
URL, token, or secret is exposed to the browser bundle.

**Rationale**: Server-side fetching keeps the session cookie off the client and improves the
first paint, which SC-004 measures.

**Alternatives considered**: client-only SPA fetching (worse first paint, token handling in
browser); GraphQL or tRPC (unneeded coupling for a small resource set).

## R10. Money, dates, and determinism

**Decision**: Prices are integers in kopecks in the database and API, formatted `ru-RU` for
display; timestamps are UTC ISO-8601 with `Z`. Scores are computed in `float64`, summed in
deterministic order (sorted candidate ids), stored with 6 decimals, and compared by rank —
never by float equality. Tie-break: equal net score orders by model id ascending.

**Rationale**: Principle IV forbids floating money and requires deterministic ordering;
float ties are expected across near-identical models.

**Alternatives considered**: `Decimal` throughout scoring (slower, and SIR is defined over
real arithmetic); float prices (rounding bugs).

## R11. Testing strategy

**Decision**: Four layers. (1) Unit tests for domain rules and both SIR kernels, including
the brute-force equivalence test and degenerate inputs. (2) Integration tests for use cases
against a real PostgreSQL started by Docker Compose (no SQLite substitution). (3) Contract
tests asserting every response matches `contracts/api.md` and that generated criteria modules
are current. (4) One Playwright end-to-end flow: guest ranking → open details → compare two
models → register → save profile → re-rank with saved weights.

**Rationale**: The domain must be testable without I/O (Principle II), while persistence and
SQL behavior need the real database. Playwright covers the only flow the grader will exercise
manually.

**Alternatives considered**: SQLite for integration (hides PostgreSQL-specific behavior);
snapshot-only frontend tests (miss the integration risk); broad e2e suite (slow, flaky).

## R12. Local environment and reproducibility

**Decision**: Docker Compose with three services (postgres, api, web). The API image installs
from a lockfile; the web image builds a production Next.js build. Seeding is an Alembic
data-migration pair (`seed_models`, `seed_admin`) that is idempotent by natural key. A
`Makefile` exposes `make up`, `make migrate`, `make seed`, `make test`, `make gen-criteria`.
Python and Node versions are pinned in `.python-version` and `.nvmrc`.

**Rationale**: Principle V requires a single documented command and pinned dependencies;
OneDrive-synced workspaces can break file-watch mounts, so the compose file mounts source
read-only for the API and relies on image rebuilds.

**Alternatives considered**: bare-metal setup instructions only (unreproducible across
machines); mounting the whole OneDrive folder into containers (slow, permission issues).
