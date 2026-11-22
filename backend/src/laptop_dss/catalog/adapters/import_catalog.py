"""Load real catalog data from a CSV file.

The spec keeps live retailer feeds out of scope and gives catalog maintenance to a
maintainer, so this is the practical path to real prices: export a sheet from any
retailer, import it here, and the catalog becomes real data without touching code.

Usage:
    python -m laptop_dss.catalog.adapters.import_catalog prices.csv

CSV columns (header required, UTF-8):
    brand,model_name,os,form_factor,price_rub,cpu_score,ram_gb,weight_g,
    battery_minutes,screen_score,warranty_months

Rows are validated with the same domain rules as the admin API. Import is
idempotent by (brand, model_name): an existing model is updated, a new one is
inserted. Invalid rows are reported by line number and skipped; the process exits
non-zero when any row failed.
"""

from __future__ import annotations

import csv
import sys
import uuid
from pathlib import Path
from typing import Any

from laptop_dss.catalog.adapters import repository as repo
from laptop_dss.catalog.adapters.criteria_source import load_registry
from laptop_dss.catalog.domain.device import CriterionValues, DeviceModel
from laptop_dss.shared.domain.errors import DomainError

REQUIRED_COLUMNS = (
    "brand",
    "model_name",
    "os",
    "form_factor",
    "price_rub",
    "cpu_score",
    "ram_gb",
    "weight_g",
    "battery_minutes",
    "screen_score",
    "warranty_months",
)


def _parse_row(row: dict[str, str]) -> dict[str, Any]:
    price_rub = float(row["price_rub"].replace(" ", "").replace("\u00a0", "").replace(",", "."))
    return {
        "brand": row["brand"].strip(),
        "model_name": row["model_name"].strip(),
        "os": row["os"].strip().lower(),
        "form_factor": row["form_factor"].strip().lower(),
        "price_minor": int(round(price_rub * 100)),
        "cpu_score": int(float(row["cpu_score"])),
        "ram_gb": int(float(row["ram_gb"])),
        "weight_g": int(float(row["weight_g"])),
        "battery_minutes": int(float(row["battery_minutes"])),
        "screen_score": float(row["screen_score"]),
        "warranty_months": int(float(row["warranty_months"])),
    }


def import_csv(path: Path) -> dict[str, Any]:
    registry = load_registry()
    inserted = 0
    updated = 0
    errors: list[str] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(missing)}")

        for line, row in enumerate(reader, start=2):
            try:
                data = _parse_row(row)
                data["slug"] = repo.slugify(data["brand"], data["model_name"])
                device = DeviceModel(
                    id=uuid.uuid5(uuid.NAMESPACE_URL, f"{data['brand']}|{data['model_name']}"),
                    brand=data["brand"],
                    model_name=data["model_name"],
                    os=data["os"],
                    form_factor=data["form_factor"],
                    values=CriterionValues(
                        price=data["price_minor"],
                        performance=data["cpu_score"],
                        memory=data["ram_gb"],
                        weight=data["weight_g"],
                        battery=data["battery_minutes"],
                        screen=data["screen_score"],
                        warranty=data["warranty_months"],
                    ),
                )
                device.validate_vocabularies(registry)
            except (ValueError, KeyError, TypeError, DomainError) as exc:
                errors.append(f"line {line}: {exc}")
                continue

            existing = repo.find_by_natural_key(data["brand"], data["model_name"])
            if existing is None:
                repo.insert_model(data)
                inserted += 1
            else:
                repo.update_model(existing["id"], data)
                updated += 1

    return {"inserted": inserted, "updated": updated, "errors": errors}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m laptop_dss.catalog.adapters.import_catalog <file.csv>")
        return 2
    result = import_csv(Path(argv[1]))
    print(f"inserted: {result['inserted']}, updated: {result['updated']}")
    for error in result["errors"]:
        print(error, file=sys.stderr)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
