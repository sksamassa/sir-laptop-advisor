# Laptop Selection DSS (SIR) — developer entry points.
# Requires Python 3.12 and a reachable PostgreSQL (see README).

PY ?= python
export PYTHONPATH := backend/src

.PHONY: help api migrate seed test test-unit lint typecheck gen-criteria check-criteria

help:
	@echo "api            run the FastAPI app on :8000"
	@echo "migrate        apply backend/migrations/*.sql"
	@echo "seed           load demo catalog and maintainer account"
	@echo "test           run the executable acceptance checks (needs PostgreSQL)"
	@echo "test-unit      run the checks that need no database"
	@echo "gen-criteria   regenerate criteria constants from shared/criteria.json"
	@echo "check-criteria fail if generated constants are stale"

api:
	$(PY) -m uvicorn laptop_dss.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend/src

migrate:
	$(PY) -c "from laptop_dss.shared.adapters import db; print(db.migrate())"

seed:
	$(PY) -c "from laptop_dss.main import seed_demo; print(seed_demo())"

test:
	cd backend && $(PY) tests/run_checks.py

test-unit:
	cd backend && $(PY) tests/run_checks.py --unit-only

coverage:
	cd backend && $(PY) tests/coverage_report.py --full

e2e:
	cd frontend && npm test

criteria-test:
	cd frontend && npm run test:criteria

import-prices:
	cd backend && $(PY) -m laptop_dss.catalog.adapters.import_catalog $(CSV)

gen-criteria:
	node shared/criteria.codegen.mjs

check-criteria:
	node shared/criteria.codegen.mjs --check

lint:
	cd backend && $(PY) -m ruff check src tests

typecheck:
	cd backend && $(PY) -m mypy
