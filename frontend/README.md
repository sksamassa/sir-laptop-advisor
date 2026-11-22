# Frontend: SIR laptop selector

Next.js (App Router) + TypeScript + TailwindCSS. The browser talks to `/api/*`, which
Next rewrites to the FastAPI service (`API_ORIGIN`, default `http://127.0.0.1:8000`), so
the session cookie stays first-party and CORS is not needed in development.

## Run

```bash
# 1) API (from the repository root)
export PYTHONPATH=backend/src
python -m uvicorn laptop_dss.main:app --app-dir backend/src --port 8000

# 2) UI (this directory)
npm install
npm run dev            # http://localhost:3000
```

`npm run build && npm start` for a production build. `npm run typecheck` runs `tsc --noEmit`.

If the npm registry is slow or blocked, the environment used here needed:

```bash
npm install --allow-remote=all --maxsockets=1 \
  --cache ../.npm-cache --fetch-timeout=600000
```

## Screens

| Route | Covers |
|---|---|
| `/` | US1 + US4: budget, goals, soft preferences, weight sliders (live 100% check), ranked cards with SIR score, "Почему так?" contribution breakdown, Φ+/Φ−/SIR summary, 2–4 model comparison dialog |
| `/catalog` | US3: search, OS/form-factor chips, price ceiling, paginated cards with all seven criteria |
| `/profile` | US2: register/login, saved goals, budget, weights, revision badge, "use saved weights" toggle on the ranking form |

The UI is Russian-only with RUB formatting, and the layout is responsive from 390 px up.

## Design

Dark "aurora" backdrop, glass panels, violet→mint accent gradient, 2xl radii, soft shadows,
`rise` entrance animations, skeleton loaders, reduced-motion support. Tokens live in
`tailwind.config.ts` and `src/app/globals.css`.
