"""FastAPI application: wiring, middleware, and error translation."""

from __future__ import annotations

import logging
import os
import secrets
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from laptop_dss.api.routes import router
from laptop_dss.catalog.adapters.criteria_source import load_registry
from laptop_dss.config import load_settings
from laptop_dss.profiles.adapters import auth
from laptop_dss.shared.adapters import db
from laptop_dss.shared.domain.errors import DomainError

logger = logging.getLogger("laptop_dss")


class Utf8JSONResponse(JSONResponse):
    """JSON with an explicit charset, as promised by contracts/api.md."""

    media_type = "application/json; charset=utf-8"


# (limit, window_seconds) per POST path; a coursework-scale, in-process guard.
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (5, 60),
    "/api/v1/auth/register": (3, 600),
    "/api/v1/rankings": (30, 60),
}
_hits: dict[tuple[str, str], deque[float]] = {}


def _rate_limited(client: str, path: str) -> bool:
    if os.environ.get("RATE_LIMIT_DISABLED") == "1":
        return False
    rule = RATE_LIMITS.get(path)
    if rule is None:
        return False
    limit, window = rule
    now = time.monotonic()
    bucket = _hits.setdefault((client, path), deque())
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="Laptop Selection DSS (SIR)",
        default_response_class=Utf8JSONResponse,
        version="0.1.0",
        description="Многокритериальный подбор ноутбука методом SIR",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = secrets.token_hex(8)
        started = time.perf_counter()
        if request.method == "POST" and _rate_limited(
            request.client.host if request.client else "unknown", request.url.path
        ):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Слишком много запросов, попробуйте позже",
                        "details": None,
                    }
                },
                headers={"X-Request-ID": request_id},
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Внутренняя ошибка сервиса",
                    "details": None,
                }
            },
        )

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        """Friendly landing so the platform's root probe is not a bare 404."""
        return {
            "service": "SIR laptop advisor API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    @app.on_event("startup")
    def on_startup() -> None:
        applied = db.migrate()
        if applied:
            logger.info("applied migrations: %s", ", ".join(applied))
        # Load the registry at boot: a missing or invalid criteria file must fail the
        # deploy instead of surfacing as a 500 on the first ranking request.
        registry = load_registry()
        logger.info(
            "criteria registry ready: version=%s hash=%s",
            registry.version,
            registry.content_hash,
        )
        # PaaS free tiers often have no shell, so allow a one-time bootstrap:
        # SEED_IF_EMPTY=1 seeds only when the catalog is empty.
        if os.environ.get("SEED_IF_EMPTY") == "1":
            from laptop_dss.catalog.adapters import repository as catalog_repo

            if catalog_repo.count() == 0:
                logger.info("catalog is empty; seeding demo data")
                logger.info("seed result: %s", seed_demo())
            else:
                logger.info("catalog already populated; SEED_IF_EMPTY skipped")

    app.include_router(router)
    return app


app = create_app()


def seed_demo() -> dict[str, Any]:
    """Idempotent demo data: catalog models plus one maintainer account."""
    import os

    from laptop_dss.catalog.adapters import repository as catalog_repo
    from laptop_dss.catalog.adapters.seed_data import DEMO_MODELS
    from laptop_dss.profiles.adapters import repository as profiles_repo

    inserted = catalog_repo.seed(DEMO_MODELS)
    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com")
    configured = os.environ.get("SEED_ADMIN_PASSWORD")
    if not configured:
        logger.warning(
            "SEED_ADMIN_PASSWORD is not set; the maintainer account uses the demo password"
        )
    password = configured or "admin-password-12"
    created_admin = False
    if profiles_repo.find_user_by_email(email) is None:
        profiles_repo.create_user(email, auth.hash_password(password), role="maintainer")
        created_admin = True
    return {"models_inserted": inserted, "admin_created": created_admin}
