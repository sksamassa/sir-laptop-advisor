"""Seed the configured database with the demo catalog and a maintainer account.

Usage (from anywhere, no PYTHONPATH needed):

    python backend/seed.py

Reads the same environment variables as the service:
    DATABASE_URL, SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD

Safe to run repeatedly: models are upserted by (brand, model_name) and the admin
account is only created when the email is not present.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from laptop_dss.main import seed_demo  # noqa: E402

if __name__ == "__main__":
    print(seed_demo())
