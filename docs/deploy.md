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

## 2. API on Render (Web Service, Docker)

Point Render at this repository with **Root Directory `backend`**. The included
`Dockerfile` builds `requirements.txt` and serves:

```bash
uvicorn laptop_dss.main:app --host 0.0.0.0 --port $PORT --app-dir /app/src
```

Environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | the Neon/Supabase string above, with `sslmode=require` |
| `SESSION_SECRET` | 32+ random bytes (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
| `SESSION_COOKIE_NAME` | `sess` |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app` (only needed for direct API calls) |
| `APP_ENV` | `production` — this is what turns on the `Secure` cookie flag |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | demo maintainer; set a real password |

Seed once, from the Render shell:

```bash
python -c "from laptop_dss.main import seed_demo; seed_demo()"
```

Do not enable Render's autoscaling for this coursework build: session cleanup and the
rate limiter are per-process.

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

- **npm lockfile**: `frontend/package-lock.json` is produced by npm 12; Vercel's bundled
  npm may resolve peer trees differently. If the build fails with
  `lock file's picomatch@2.3.2 does not satisfy picomatch@4.0.7`, regenerate with
  `npx npm@10 install --package-lock-only` and redeploy.
- **Cold starts**: the Vercel rewrite proxies to the API, so the first request after idle
  pays the API host's cold-start cost. Render free instances sleep; expect a few seconds.
- **Serverless API is not an option here**: if you try Vercel Functions anyway, set a
  server-side connection pooler (Neon's `-pooler` host), disable the startup migration,
  and expect the rate limiter to be per-function.
