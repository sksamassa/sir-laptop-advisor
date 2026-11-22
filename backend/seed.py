"""Seed the configured database with the demo catalog and a maintainer account.

Usage (from anywhere, no PYTHONPATH or Cyrillic path typing needed):

    Set-Location <repo>
    $env:DATABASE_URL = "postgresql://…"
    python backend/seed.py

``DATABASE_URL`` is required: without it the service would silently fall back to the
local development database, which is exactly how a "seeded" production API ends up
empty. The script prints the host and database it is about to write to.

Safe to run repeatedly: models are upserted by (brand, model_name) and the admin
account is only created when the email is not present.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from laptop_dss.main import seed_demo  # noqa: E402
from laptop_dss.shared.adapters import db  # noqa: E402

if __name__ == "__main__":
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit(
            "DATABASE_URL is not set. Refusing to seed the local default database.\n"
            "Copy the connection string from Neon (or Render) and set DATABASE_URL first."
        )
    print(f"target: {db.describe_target(dsn)}")
    print(seed_demo())
