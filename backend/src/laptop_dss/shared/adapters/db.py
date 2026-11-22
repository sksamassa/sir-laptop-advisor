"""PostgreSQL access: a small connection pool and a versioned SQL migrator.

The plan called for SQLAlchemy 2 + Alembic. Those packages could not be
installed in this offline environment, so this module keeps the same contract
(repository ports, versioned migrations, PostgreSQL-only) with psycopg2 and
plain SQL. Swapping in SQLAlchemy later only touches the adapters.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor, register_uuid
from psycopg2.pool import ThreadedConnectionPool

register_uuid()

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "migrations"
_pool: ThreadedConnectionPool | None = None


def _dsn() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://dss@127.0.0.1:5433/laptop_dss")


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(1, 16, dsn=_dsn())
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def connection() -> Iterator[psycopg2.extensions.connection]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def cursor() -> Iterator[RealDictCursor]:
    with connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        yield cur


def fetch_all(sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Sequence[Any] = ()) -> None:
    with cursor() as cur:
        cur.execute(sql, params)


def migrate() -> list[str]:
    """Apply every *.sql file in order, recording each version once."""
    applied: list[str] = []
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        cur.execute("SELECT version FROM schema_migrations")
        done = {row[0] for row in cur.fetchall()}
        for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            version = path.name
            if version in done:
                continue
            cur.execute(path.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            applied.append(version)
    return applied
