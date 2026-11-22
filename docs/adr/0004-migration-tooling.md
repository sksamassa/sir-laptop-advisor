# ADR 0004: Versioned SQL migrations while Alembic is unavailable

**Status**: accepted (2026-11-22)

## Context

Constitution Principle II originally required Alembic for every schema change. The
development environment has no package index: `pip install alembic` fails, exactly as it
does for SQLAlchemy and pytest. The service still needs ordered, replayable schema
evolution and a record of what has been applied.

## Decision

Keep schema changes in ordered `backend/migrations/*.sql` files, applied once by a small
migrator that records each filename in `schema_migrations` and commits atomically.
Constitution v1.1.0 was amended to permit this: versioned, ordered, once-applied
migrations remain mandatory, and Alembic is the preferred tool wherever it can be
installed. `Base.metadata.create_all()` and manual DDL remain prohibited outside tests.

`0002_catalog_provenance.sql` is the first incremental revision under this rule, adding
`source` and `fetched_at` to `device_models`.

## Consequences

- Migrations are explicit SQL and portable to any PostgreSQL client.
- There is no autogenerate and no downgrade path; reversions are written by hand.
- Moving to Alembic later only requires converting the existing files into revisions;
  the order and the applied-version ledger map one-to-one.
- The constitution now states the real rule rather than a rule the project could not
  follow, which keeps the governance document honest.
