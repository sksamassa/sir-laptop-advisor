"""FastAPI application: wiring, middleware, and error translation."""

from __future__ import annotations

import logging
import os
import secrets
import time
from collections import deque
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from laptop_dss.api.routes import router
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
    async def request_context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
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

    @app.on_event("startup")
    def on_startup() -> None:
        applied = db.migrate()
        if applied:
            logger.info("applied migrations: %s", ", ".join(applied))

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
    password = os.environ.get("SEED_ADMIN_PASSWORD", "admin-password-12")
    created_admin = False
    if profiles_repo.find_user_by_email(email) is None:
        profiles_repo.create_user(email, auth.hash_password(password), role="maintainer")
        created_admin = True
    return {"models_inserted": inserted, "admin_created": created_admin}

