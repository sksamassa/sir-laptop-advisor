"""HTTP routes. Thin: validation, auth wiring, and delegation to use cases."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Mapping

import psycopg2
from fastapi import APIRouter, Depends, Query, Request, Response

from laptop_dss.api import deps
from laptop_dss.api.schemas import (
    ComparisonRequest,
    LoginRequest,
    ModelPatchRequest,
    ModelRequest,
    ProfilePatchRequest,
    ProfileRequest,
    RankingRequest,
    RegisterRequest,
)
from laptop_dss.catalog.adapters import repository as catalog_repo
from laptop_dss.catalog.domain.criteria import load_registry
from laptop_dss.config import load_settings
from laptop_dss.profiles.adapters import auth
from laptop_dss.profiles.domain.weights import WeightSet
from laptop_dss.ranking.adapters import repository as ranking_repo
from laptop_dss.ranking.application import compare as compare_uc
from laptop_dss.ranking.application import rank_laptops
from laptop_dss.shared.adapters import db
from laptop_dss.shared.domain.errors import (
    Conflict,
    NotFound,
    UpstreamUnavailable,
    ValidationError,
)

router = APIRouter(prefix="/api/v1")
settings = load_settings()


def _model_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "brand": row["brand"],
        "model_name": row["model_name"],
        "os": row["os"],
        "form_factor": row["form_factor"],
        "price_minor": int(row["price_minor"]),
        "values": {
            "price": int(row["price_minor"]),
            "performance": int(row["cpu_score"]),
            "memory": int(row["ram_gb"]),
            "weight": int(row["weight_g"]),
            "battery": int(row["battery_minutes"]),
            "screen": float(row["screen_score"]),
            "warranty": int(row["warranty_months"]),
        },
        "status": row["status"],
    }


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.session_idle_days * 24 * 3600,
        path="/",
    )


# --------------------------------------------------------------------------- health


@router.get("/health")
def health() -> dict[str, str]:
    db.fetch_one("SELECT 1 AS ok")
    return {"status": "ok", "db": "ok"}


# ------------------------------------------------------------------------- criteria


@router.get("/criteria")
def criteria() -> dict[str, Any]:
    registry = load_registry()
    return {
        "version": registry.version,
        "criteria": [
            {
                "key": criterion.key,
                "order": criterion.order,
                "label_ru": criterion.label_ru,
                "direction": criterion.direction,
                "unit": criterion.unit,
                "display_decimals": criterion.display_decimals,
                "indifference_threshold": criterion.indifference_threshold,
                "preference_threshold": criterion.preference_threshold,
            }
            for criterion in registry.criteria
        ],
        "vocabularies": {
            "goals": list(registry.goals),
            "os": list(registry.operating_systems),
            "form_factor": list(registry.form_factors),
        },
    }


# --------------------------------------------------------------------------- catalog


@router.get("/models")
def list_models(
    brand: str | None = None,
    os: str | None = None,
    form_factor: str | None = None,
    max_price_minor: int | None = Query(default=None, ge=1),
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = "price_asc",
) -> dict[str, Any]:
    rows, total = catalog_repo.list_models(
        brand=brand,
        os_name=os,
        form_factor=form_factor,
        max_price_minor=max_price_minor,
        query=q,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return {
        "items": [_model_payload(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "meta": catalog_repo.catalog_meta(),
    }


@router.get("/models/{model_id}")
def get_model(model_id: uuid.UUID) -> dict[str, Any]:
    row = catalog_repo.get_model(model_id)
    if row is None:
        raise NotFound("Модель не найдена")
    return _model_payload(row)


# ----------------------------------------------------------------------------- auth


@router.post("/auth/register", status_code=201)
def register(payload: RegisterRequest) -> dict[str, Any]:
    user = auth.register(payload.email, payload.password)
    return {"user_id": str(user["id"]), "role": user["role"]}


@router.post("/auth/login")
def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    issued = auth.login(payload.email, payload.password)
    _set_session_cookie(response, issued.token)
    return {"user": issued.user}


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    token = deps.session_token(request)
    if token:
        auth.logout(token)
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/auth/me")
def me(user: dict[str, Any] = Depends(deps.require_user)) -> dict[str, Any]:
    return {"user": user}


# -------------------------------------------------------------------------- profile


@router.get("/profile")
def get_profile(user: dict[str, Any] = Depends(deps.require_user)) -> dict[str, Any]:
    return auth.get_profile(user["id"])


@router.put("/profile")
def put_profile(
    payload: ProfileRequest,
    user: dict[str, Any] = Depends(deps.require_user),
) -> dict[str, Any]:
    weights = WeightSet.from_user_input(payload.weights, load_registry().keys)
    return auth.save_profile(
        user["id"],
        goals=list(payload.goals),
        budget_minor=payload.budget_minor,
        preferred_brand=payload.preferred_brand,
        preferred_os=payload.preferred_os,
        form_factor=payload.form_factor,
        weights=weights,
        partial=False,
    )


@router.patch("/profile")
def patch_profile(
    payload: ProfilePatchRequest,
    user: dict[str, Any] = Depends(deps.require_user),
) -> dict[str, Any]:
    current = auth.get_profile(user["id"])
    weights_raw = payload.weights if payload.weights is not None else current["weights"]
    weights = WeightSet.from_user_input(weights_raw, load_registry().keys)
    return auth.save_profile(
        user["id"],
        goals=list(payload.goals) if payload.goals is not None else current["goals"],
        budget_minor=payload.budget_minor or current["budget_minor"],
        preferred_brand=(
            payload.preferred_brand
            if payload.preferred_brand is not None
            else current["preferred_brand"]
        ),
        preferred_os=(
            payload.preferred_os if payload.preferred_os is not None else current["preferred_os"]
        ),
        form_factor=(
            payload.form_factor if payload.form_factor is not None else current["form_factor"]
        ),
        weights=weights,
        partial=True,
    )


# -------------------------------------------------------------------------- ranking


@router.post("/rankings", status_code=201)
def create_ranking(
    payload: RankingRequest,
    request: Request,
) -> dict[str, Any]:
    user = deps.current_user(request)
    registry = load_registry()
    weights: WeightSet | None = None
    if payload.weights is not None:
        weights = WeightSet.from_user_input(payload.weights, registry.keys)
    elif payload.use_saved_weights and user is not None:
        weights = auth.saved_weights(user["id"])
    if payload.use_saved_weights and user is None:
        raise deps.Unauthorized("Сохранённые веса доступны только после входа")

    budget = payload.budget_minor
    goals = list(payload.goals)

    return rank_laptops.create_ranking(
        budget_minor=budget,
        goals=goals,
        weights=weights,
        brand=payload.preferred_brand,
        os_name=payload.preferred_os,
        form_factor=payload.form_factor,
        user_id=uuid.UUID(user["id"]) if user else None,
    )


@router.get("/rankings")
def ranking_history(
    limit: int = Query(default=20, ge=1, le=100),
    user: dict[str, Any] = Depends(deps.require_user),
) -> dict[str, Any]:
    rows = ranking_repo.list_rankings(uuid.UUID(user["id"]), limit=limit)
    return {
        "items": [
            {
                "ranking_id": str(row["id"]),
                "created_at": row["created_at"].isoformat(),
                "candidate_count": row["candidate_count"],
                "algorithm_version": row["algorithm_version"],
                "criteria_version": row["criteria_version"],
            }
            for row in rows
        ]
    }


@router.get("/rankings/{ranking_id}")
def replay(
    ranking_id: uuid.UUID,
    request: Request,
    brand: str | None = None,
    os: str | None = None,
    form_factor: str | None = None,
    max_price_minor: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    stored = ranking_repo.get_ranking(ranking_id)
    user = deps.current_user(request)
    if stored is None:
        raise NotFound("Ранжирование не найдено")
    # Owner-only for account rankings; a guest ranking is addressed by its id.
    if stored["user_id"] is not None:
        if user is None or str(stored["user_id"]) != user["id"]:
            raise NotFound("Ранжирование не найдено")
    payload = rank_laptops.replay_ranking(ranking_id)
    assert payload is not None

    # FR-009: narrow a stored ranking for display. This is a post-hoc filter over
    # the stored items, never a re-ranking: SIR order and original ranks are kept,
    # which is the only way "preserve the SIR order" can hold given that
    # normalization depends on the candidate pool.
    filters = {
        "brand": brand.lower() if brand else None,
        "os": os,
        "form_factor": form_factor,
        "max_price_minor": max_price_minor,
    }
    if any(value is not None for value in filters.values()):
        payload["items"] = [
            item
            for item in payload["items"]
            if (filters["brand"] is None or item["model"]["brand"].lower() == filters["brand"])
            and (filters["os"] is None or item["model"]["os"] == filters["os"])
            and (
                filters["form_factor"] is None
                or item["model"]["form_factor"] == filters["form_factor"]
            )
            and (
                filters["max_price_minor"] is None
                or item["model"]["price_minor"] <= filters["max_price_minor"]
            )
        ]
        payload["filtered_from"] = stored["candidate_count"]
    return payload


@router.post("/rankings/{ranking_id}/comparison")
def comparison(
    ranking_id: uuid.UUID,
    payload: ComparisonRequest,
    request: Request,
) -> dict[str, Any]:
    user = deps.current_user(request)
    return compare_uc.compare(
        ranking_id, payload.model_ids, user_id=user["id"] if user else None
    )


# ------------------------------------------------------------------ admin catalog


@router.post("/admin/catalog/refresh")
def refresh_catalog(
    _: dict[str, Any] = Depends(deps.require_maintainer),
) -> dict[str, Any]:
    """Pull the catalog from the configured live source, falling back to CSV."""
    from laptop_dss.catalog.adapters import sources as catalog_sources

    configured = catalog_sources.configured_sources()
    if not configured:
        raise ValidationError(
            "Источник не настроен: задайте CATALOG_LIVE_URL, CATALOG_HTML_CONFIG или CATALOG_CSV_PATH"
        )
    result = catalog_sources.refresh(configured)
    if not result["source"]:
        raise UpstreamUnavailable(
            "Ни один источник каталога не ответил", errors=result["fallback_errors"]
        )
    return result


@router.post("/admin/models", status_code=201)
def create_model(
    payload: ModelRequest,
    _: dict[str, Any] = Depends(deps.require_maintainer),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["slug"] = catalog_repo.slugify(payload.brand, payload.model_name)
    try:
        row = catalog_repo.insert_model(data)
    except psycopg2.IntegrityError as exc:
        raise Conflict("Модель с таким названием уже существует") from exc
    return _model_payload(row)


@router.patch("/admin/models/{model_id}")
def update_model(
    model_id: uuid.UUID,
    payload: ModelPatchRequest,
    _: dict[str, Any] = Depends(deps.require_maintainer),
) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    if "model_name" in data or "brand" in data:
        current = catalog_repo.get_model(model_id)
        if current is None:
            raise NotFound("Модель не найдена")
        data["slug"] = catalog_repo.slugify(
            data.get("brand", current["brand"]), data.get("model_name", current["model_name"])
        )
    row = catalog_repo.update_model(model_id, data)
    if row is None:
        raise NotFound("Модель не найдена")
    return _model_payload(row)


@router.post("/admin/models/{model_id}/retire")
def retire_model(
    model_id: uuid.UUID,
    _: dict[str, Any] = Depends(deps.require_maintainer),
) -> dict[str, Any]:
    row = catalog_repo.set_status(model_id, "retired")
    if row is None:
        raise NotFound("Модель не найдена")
    return _model_payload(row)


@router.post("/admin/models/{model_id}/publish")
def publish_model(
    model_id: uuid.UUID,
    _: dict[str, Any] = Depends(deps.require_maintainer),
) -> dict[str, Any]:
    row = catalog_repo.set_status(model_id, "active")
    if row is None:
        raise NotFound("Модель не найдена")
    return _model_payload(row)


def utcnow() -> datetime:
    return datetime.now(UTC)


__all__ = ["router", "ValidationError"]
