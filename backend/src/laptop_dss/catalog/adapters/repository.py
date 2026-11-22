"""Catalog persistence (ports implemented with psycopg2)."""

from __future__ import annotations

import re
import uuid
from typing import Any, Mapping

from laptop_dss.catalog.adapters.criteria_source import load_registry
from laptop_dss.catalog.domain.device import CriterionValues, DeviceModel
from laptop_dss.shared.adapters import db

_COLUMNS = (
    "id, brand, model_name, slug, os, form_factor, price_minor, cpu_score, ram_gb, "
    "weight_g, battery_minutes, screen_score, warranty_months, status, published_at, retired_at"
)


def _to_domain(row: Mapping[str, Any]) -> DeviceModel:
    return DeviceModel(
        id=row["id"],
        brand=row["brand"],
        model_name=row["model_name"],
        os=row["os"],
        form_factor=row["form_factor"],
        values=CriterionValues(
            price=int(row["price_minor"]),
            performance=int(row["cpu_score"]),
            memory=int(row["ram_gb"]),
            weight=int(row["weight_g"]),
            battery=int(row["battery_minutes"]),
            screen=float(row["screen_score"]),
            warranty=int(row["warranty_months"]),
        ),
        status=row["status"],
    )


def slugify(brand: str, model_name: str) -> str:
    raw = f"{brand}-{model_name}".lower().translate(str.maketrans("ё", "е"))
    slug = re.sub(r"[^a-z0-9а-я]+", "-", raw).strip("-")
    return slug or "model"


def list_models(
    *,
    brand: str | None = None,
    os_name: str | None = None,
    form_factor: str | None = None,
    max_price_minor: int | None = None,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "price_asc",
) -> tuple[list[dict[str, Any]], int]:
    clauses = ["status = 'active'"]
    params: list[Any] = []
    if brand:
        clauses.append("lower(brand) = lower(%s)")
        params.append(brand)
    if os_name:
        clauses.append("os = %s")
        params.append(os_name)
    if form_factor:
        clauses.append("form_factor = %s")
        params.append(form_factor)
    if max_price_minor is not None:
        clauses.append("price_minor <= %s")
        params.append(max_price_minor)
    if query:
        clauses.append("(model_name ILIKE %s OR brand ILIKE %s)")
        params.extend([f"%{query}%", f"%{query}%"])
    where = " AND ".join(clauses)
    order = {
        "price_asc": "price_minor ASC, id ASC",
        "price_desc": "price_minor DESC, id ASC",
        "name": "model_name ASC, id ASC",
    }.get(sort, "price_minor ASC, id ASC")
    total_row = db.fetch_one(f"SELECT count(*) AS total FROM device_models WHERE {where}", params)
    total = int(total_row["total"]) if total_row else 0
    offset = (page - 1) * page_size
    rows = db.fetch_all(
        f"SELECT {_COLUMNS} FROM device_models WHERE {where} ORDER BY {order} LIMIT %s OFFSET %s",
        [*params, page_size, offset],
    )
    return rows, total


def get_model(model_id: uuid.UUID) -> dict[str, Any] | None:
    return db.fetch_one(f"SELECT {_COLUMNS} FROM device_models WHERE id = %s", (model_id,))


def find_by_natural_key(brand: str, model_name: str) -> dict[str, Any] | None:
    return db.fetch_one(
        f"SELECT {_COLUMNS} FROM device_models WHERE brand = %s AND model_name = %s",
        (brand, model_name),
    )


def eligible_by_budget(budget_minor: int) -> list[DeviceModel]:
    rows = db.fetch_all(
        f"SELECT {_COLUMNS} FROM device_models "
        "WHERE status = 'active' AND price_minor <= %s ORDER BY id ASC",
        (budget_minor,),
    )
    return [_to_domain(row) for row in rows]


def insert_model(
    data: Mapping[str, Any],
    *,
    source: str | None = None,
    fetched_at: object | None = None,
) -> dict[str, Any]:
    model_id = uuid.uuid4()
    row = db.fetch_one(
        "INSERT INTO device_models (id, brand, model_name, slug, os, form_factor, price_minor, "
        "cpu_score, ram_gb, weight_g, battery_minutes, screen_score, warranty_months, status, "
        "published_at, source, fetched_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
        "%s, %s, 'active', now(), %s, %s) "
        f"RETURNING {_COLUMNS}",
        (
            model_id,
            data["brand"],
            data["model_name"],
            data["slug"],
            data["os"],
            data["form_factor"],
            data["price_minor"],
            data["cpu_score"],
            data["ram_gb"],
            data["weight_g"],
            data["battery_minutes"],
            data["screen_score"],
            data["warranty_months"],
            source,
            fetched_at,
        ),
    )
    assert row is not None
    return row


def update_model(
    model_id: uuid.UUID,
    data: Mapping[str, Any],
    *,
    source: str | None = None,
    fetched_at: object | None = None,
) -> dict[str, Any] | None:
    allowed = (
        "brand",
        "model_name",
        "slug",
        "os",
        "form_factor",
        "price_minor",
        "cpu_score",
        "ram_gb",
        "weight_g",
        "battery_minutes",
        "screen_score",
        "warranty_months",
    )
    fields = [key for key in allowed if key in data]
    if not fields:
        return get_model(model_id)
    assignments = ", ".join(f"{key} = %s" for key in fields) + ", updated_at = now()"
    values = [data[key] for key in fields]
    if source is not None:
        assignments += ", source = %s"
        values.append(source)
    if fetched_at is not None:
        assignments += ", fetched_at = %s"
        values.append(fetched_at)
    return db.fetch_one(
        f"UPDATE device_models SET {assignments} WHERE id = %s RETURNING {_COLUMNS}",
        [*values, model_id],
    )


def catalog_meta() -> dict[str, Any]:
    """Where the visible catalog came from and how fresh it is."""
    row = db.fetch_one(
        "SELECT max(fetched_at) AS fetched_at, "
        "(SELECT source FROM device_models WHERE fetched_at IS NOT NULL "
        " ORDER BY fetched_at DESC, id LIMIT 1) AS source, "
        "count(*) FILTER (WHERE source IS NOT NULL) AS tracked, count(*) AS total "
        "FROM device_models"
    )
    if row is None:
        return {"source": None, "fetched_at": None, "tracked": 0, "total": 0}
    return {
        "source": row["source"],
        "fetched_at": row["fetched_at"].isoformat() if row["fetched_at"] else None,
        "tracked": int(row["tracked"]),
        "total": int(row["total"]),
    }


def set_status(model_id: uuid.UUID, status: str) -> dict[str, Any] | None:
    now_field = "retired_at" if status == "retired" else "published_at"
    return db.fetch_one(
        f"UPDATE device_models SET status = %s, {now_field} = now(), updated_at = now() "
        f"WHERE id = %s RETURNING {_COLUMNS}",
        (status, model_id),
    )


def count() -> int:
    row = db.fetch_one("SELECT count(*) AS total FROM device_models")
    return int(row["total"]) if row else 0


def cheapest_active_price() -> int | None:
    """Lowest price among active models; used to explain an empty budget."""
    row = db.fetch_one(
        "SELECT min(price_minor) AS price FROM device_models WHERE status = 'active'"
    )
    if row is None or row["price"] is None:
        return None
    return int(row["price"])


def seed(models: list[dict[str, Any]]) -> int:
    """Insert seed models idempotently by (brand, model_name)."""
    inserted = 0
    with db.connection() as conn, conn.cursor() as cur:
        for item in models:
            cur.execute(
                "INSERT INTO device_models (id, brand, model_name, slug, os, form_factor, "
                "price_minor, cpu_score, ram_gb, weight_g, battery_minutes, screen_score, "
                "warranty_months, status, published_at, source, fetched_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', now(), "
                "'seed', now()) "
                "ON CONFLICT (brand, model_name) DO UPDATE SET price_minor = EXCLUDED.price_minor, "
                "cpu_score = EXCLUDED.cpu_score, ram_gb = EXCLUDED.ram_gb, "
                "weight_g = EXCLUDED.weight_g, battery_minutes = EXCLUDED.battery_minutes, "
                "screen_score = EXCLUDED.screen_score, warranty_months = EXCLUDED.warranty_months, "
                "source = 'seed', fetched_at = now(), updated_at = now()",
                (
                    uuid.uuid4(),
                    item["brand"],
                    item["model_name"],
                    item["slug"],
                    item["os"],
                    item["form_factor"],
                    item["price_minor"],
                    item["cpu_score"],
                    item["ram_gb"],
                    item["weight_g"],
                    item["battery_minutes"],
                    item["screen_score"],
                    item["warranty_months"],
                ),
            )
            inserted += cur.rowcount
    return inserted


def registry():  # noqa: ANN201 - re-exported for convenience
    return load_registry()
