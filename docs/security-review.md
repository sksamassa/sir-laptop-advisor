# Security review record

Date: 2026-11-22. Scope: backend service as implemented in `backend/`.

## Implemented controls

| Control | Where | Evidence |
|---|---|---|
| Password hashing with Argon2id, minimum 12 characters | `profiles/adapters/auth.py` | `PasswordHasher` default parameters; short passwords rejected with `400` |
| Opaque 256-bit session tokens, stored only as SHA-256 digests | `profiles/adapters/auth.py`, `sessions.token_hash bytea` | Raw token exists only in the cookie |
| `HttpOnly; SameSite=Lax` cookie, `Secure` in production, 7-day idle / 30-day absolute expiry | `api/routes.py::_set_session_cookie`, `profiles/adapters/repository.py` | Session row deleted on logout; tests assert `401` after logout |
| Identity derived from the session only; no client-supplied user id | `api/deps.py` | Profile and ranking endpoints use the cookie user |
| Ownership and role checks | `api/routes.py` (replay), `ranking/application/compare.py`, `api/deps.py::require_maintainer` | Shopper retiring a model returns `403`; another user's ranking returns `404` |
| Strict input validation (`extra="forbid"`) | `api/schemas.py` | Unknown field returns `422` |
| Parameterized SQL everywhere | all repositories | No string interpolation of user values |
| Explicit CORS allowlist, wildcard rejected at startup | `config.py` | Startup raises if `CORS_ORIGINS` contains `*` |
| PII-free logs (ids, route, status, duration only) | `main.py` request middleware | No email, password, cookie, or weight values logged |
| Uniform login failure message | `profiles/adapters/auth.py` | Unknown email and wrong password both return `401` with the same message |
| Rate limiting on login, register, and ranking | `main.py::RATE_LIMITS` | `429` with a Russian message |

## Not audited here

- `pip-audit` / `npm audit` and secret scanning are wired in CI
  (`.github/workflows/ci.yml`) but could not run in this offline environment.
- TLS termination and cookie `Secure` behaviour are deployment concerns; this
  checkout runs over plain HTTP locally.
- Penetration testing, CSRF review of the Next.js client, and load testing are
  outstanding with the frontend work.

## Residual risks

1. Guest rankings are addressable by their 122-bit random id so a visitor can replay
   and compare their own result without an account. The id is an unguessable
   capability, but it is a bearer token: anyone given the link can read that ranking's
   preferences. Account-owned rankings remain owner-only.
2. The demo maintainer password is seeded from an environment variable with a
   known default; production must set `SEED_ADMIN_PASSWORD` and remove the demo
   account.
3. Rate limiting is in-process and per-worker; a multi-worker deployment needs a
   shared store.
4. Session cleanup runs on demand (`purge_expired_sessions`) but is not
   scheduled.
