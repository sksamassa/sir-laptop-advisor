# Deploying: Vercel for the UI, a long-running host for the API

## The decision

**Vercel hosts the Next.js frontend. It should not host this FastAPI backend.**

The API is a stateful, long-running process: a `psycopg2` connection pool, migrations
at startup, an in-process rate limiter, and cookie sessions written to PostgreSQL.
Vercel's Python runtime is serverless, so each invocation is a fresh function: the pool
is recreated per cold start, startup migrations race, and concurrent functions can
exhaust the database's connection limit. Put the API on Render, Railway, or Fly.io and
give it a managed PostgreSQL (Neon or Supabase, both have free tiers).

```text
Browser ──► Vercel (Next.js) ──/api/* rewrite──► Render (FastAPI) ──► Neon (PostgreSQL)
```

The rewrite in `frontend/next.config.mjs` keeps the browser on one origin, so the session
cookie is first-party and CORS never enters the picture for UI traffic.

## Dashboard or CLI?

**Use the dashboard's Git integration as the primary path, and the CLI for env vars,
preview deploys, and logs.** Git integration gives you automatic production deploys on
`main` and a preview URL per pull request for free; the CLI is for things you cannot do
in a browser form.

```bash
npm i -g vercel
vercel link                              # bind this checkout to the project
vercel env add API_ORIGIN production     # https://<api-host>
vercel --prod                            # manual production deploy
vercel logs <deployment-url>             # inspect a failing build
```

If you prefer not to install anything, `npx vercel` runs the same CLI.

## 1. PostgreSQL (Neon or Supabase)

Create a database and copy the connection string. It must include TLS:

```text
postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

The service applies its own versioned SQL migrations on start
(`0001_init.sql`, `0002_catalog_provenance.sql`), so do not use ORM `create_all`.

## 2. API on Render

**Fastest path — Blueprint:** push `render.yaml`, then in Render choose
*New → Blueprint*, pick this repository, and apply. It creates the free PostgreSQL
instance and the Docker web service with generated secrets; Render prompts once for
`CORS_ORIGINS` (you can enter the Vercel URL later).

**Manual path:** *New → Web Service*, connect the repository, and set:

| Field | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Docker (detected from `backend/Dockerfile`) |
| Instance Type | Free |
| Health Check Path | `/api/v1/health` |

Then *New → Postgres* (database `laptop_dss`, user `dss`), copy its **Internal Database
URL**, and add the environment variables below to the web service.

| Variable | Value |
|---|---|
| `DATABASE_URL` | Render's internal database URL, or a Neon string with `sslmode=require` |
| `SESSION_SECRET` | 32+ random bytes (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
| `SESSION_COOKIE_NAME` | `sess` |
| `APP_ENV` | `production` — this turns on the `Secure` cookie flag |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app` (only needed for direct API calls) |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | demo maintainer; set a real password |

Seed once, from the Render *Shell* tab (Starter plan and above):

```bash
python -c "from laptop_dss.main import seed_demo; seed_demo()"
```

Render's **free** plan has no shell. Use either of these instead:

- **Self-seed on boot** (recommended): set `SEED_IF_EMPTY=1` together with the
  `SEED_ADMIN_*` variables, then redeploy. The service seeds only when the catalog is
  empty and logs `catalog is empty; seeding demo data`. Remove the flag afterwards so an
  intentionally emptied catalog is not repopulated.
- **Seed from your machine** against the same database:

  ```powershell
  $env:DATABASE_URL = "postgresql://…neon…?sslmode=require"
  $env:SEED_ADMIN_EMAIL = "you@example.com"
  $env:SEED_ADMIN_PASSWORD = "a-strong-password"
  $env:PYTHONPATH = "backend/src"
  python -c "from laptop_dss.main import seed_demo; print(seed_demo())"
  ```

  Both paths are idempotent: re-running updates prices by `(brand, model_name)` and never
  duplicates rows.

Migrations run automatically at startup (`0001_init.sql`, `0002_catalog_provenance.sql`);
the logs show `applied migrations: …` on first boot.

The container binds `${PORT}` (Render sets it, default 10000) and falls back to 8000
locally, so no manual port mapping is needed.

### Cold starts and the Vercel proxy

Render's free web service sleeps after ~15 minutes idle. Waking it takes 30–50 seconds,
which **exceeds Vercel's Hobby function timeout** (10 s) — so the first request through
the `/api/*` rewrite can return a 504 while the second succeeds. For a demo, either:

- ping `https://<api-host>/api/v1/health` every 10 minutes (a free cron/uptime monitor), or
- upgrade the Render instance so it never sleeps.

Do not enable autoscaling: session cleanup and the rate limiter are per-process.

## 3. Frontend on Vercel

- Import the repository, **Root Directory `frontend`**, framework preset Next.js.
- Node 22.
- Environment variable for **Production and Preview**: `API_ORIGIN=https://<api-host>`.

`next.config.mjs` reads `API_ORIGIN` **at build time** — the rewrite is compiled into the
routes manifest. Changing the API host therefore requires a redeploy, not just an env
edit.

## 4. Verify after deploying

```bash
curl https://<api-host>/api/v1/health          # {"status":"ok","db":"ok"}
curl https://<app>.vercel.app/api/v1/criteria  # seven criteria through the proxy
```

Then in the browser: submit a ranking, open "Почему так?", and sign in — the `sess`
cookie must appear as `HttpOnly; Secure; SameSite=Lax` on the Vercel host.

## Known pitfalls

- **npm lockfile**: `npm ci` can reject this lockfile on CI runners even though
  npm 10.9 and npm 12 accept it locally — `fdir`'s `picomatch` peer is hoisted differently
  per platform, so lockfile *validation* is environment-dependent. CI and Vercel both
  install with `npm install`; use `npm ci` locally when you want strict validation.
- **Cold starts**: the Vercel rewrite proxies to the API, so the first request after idle
  pays the API host's cold-start cost. Render free instances sleep; expect a few seconds.
- **Serverless API is not an option here**: if you try Vercel Functions anyway, set a
  server-side connection pooler (Neon's `-pooler` host), disable the startup migration,
  and expect the rate limiter to be per-function.
