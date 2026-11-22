"""Configuration loaded from the environment.

Secrets never have code defaults: a missing required value fails at startup
rather than silently falling back to something insecure.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for the service."""

    database_url: str
    session_cookie_name: str
    session_secret: str
    cors_origins: tuple[str, ...]
    debug: bool = False
    session_idle_days: int = 7
    session_absolute_days: int = 30
    ranking_rate_limit: int = 30
    login_rate_limit: int = 5
    environment: str = field(default_factory=lambda: os.environ.get("APP_ENV", "development"))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def load_settings() -> Settings:
    origins = tuple(o.strip() for o in _env("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip())
    if "*" in origins:
        raise RuntimeError("CORS_ORIGINS must be an explicit allowlist, not a wildcard")
    return Settings(
        database_url=_env(
            "DATABASE_URL",
            "postgresql://dss@127.0.0.1:5433/laptop_dss",
        ),
        session_cookie_name=_env("SESSION_COOKIE_NAME", "sess"),
        session_secret=_env("SESSION_SECRET", "dev-only-not-for-production"),
        cors_origins=origins,
        debug=os.environ.get("APP_DEBUG", "0") == "1",
    )
