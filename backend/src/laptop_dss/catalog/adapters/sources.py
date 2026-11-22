"""Live catalog sources with graceful degradation.

Order of preference: a live HTTP source (JSON endpoint or an HTML page you are
allowed to read), then a CSV export, then the bundled demo snapshot. A refresh
applies the first source that yields valid rows; if every source fails, existing
data is kept untouched rather than replaced with nothing.

Retailer sites usually answer automated requests with 401/403 (DNS, M.Video) or
serve certificate errors behind interception, so the live source is configured
per deployment via environment variables instead of being hard-coded to one shop.
"""

from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from laptop_dss.catalog.adapters import repository as repo
from laptop_dss.catalog.domain.criteria import load_registry
from laptop_dss.catalog.domain.device import CriterionValues, DeviceModel
from laptop_dss.shared.domain.errors import DomainError

USER_AGENT = "LaptopDSS/0.1 (+coursework; contact the operator)"


class CatalogSourceError(RuntimeError):
    """The source is unreachable or its payload cannot be understood."""


def _to_float(value: Any, default: float = 0.0) -> float:
    """Accept numbers and formatted strings ("55 990", "1 400,5")."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.,-]", "", str(value)).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class RawRow:
    brand: str
    model_name: str
    os: str
    form_factor: str
    price_rub: float
    cpu_score: float
    ram_gb: float
    weight_g: float
    battery_minutes: float
    screen_score: float
    warranty_months: float


class CatalogSource(Protocol):
    name: str

    def fetch(self) -> list[RawRow]: ...


class JsonEndpointSource:
    """A JSON endpoint returning a list of objects.

    ``field_map`` maps a RawRow field to a dotted path inside each object, so any
    API or aggregator feed can be adapted without code changes.
    """

    def __init__(
        self,
        url: str,
        *,
        items_path: str = "products",
        field_map: dict[str, str] | None = None,
        name: str | None = None,
        fetch_json: Callable[[str], Any] | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.url = url
        self.items_path = items_path
        self.field_map = field_map or {}
        self.name = name or f"live:{url}"
        self._fetch_json = fetch_json or self._http_json
        self.timeout = timeout

    def _http_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise CatalogSourceError(f"HTTP {response.status} from {url}")
                # Feeds exported from spreadsheets often carry a UTF-8 BOM.
                return json.loads(response.read().decode("utf-8-sig"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CatalogSourceError(f"{url}: {exc}") from exc

    def _dig(self, payload: dict[str, Any], path: str) -> Any:
        value: Any = payload
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    def fetch(self) -> list[RawRow]:
        payload = self._fetch_json(self.url)
        items: Any = payload
        for part in self.items_path.split("."):
            if not isinstance(items, dict) or part not in items:
                raise CatalogSourceError(f"missing items path '{self.items_path}'")
            items = items[part]
        if not isinstance(items, list):
            raise CatalogSourceError("items path did not resolve to a list")
        return [self._row(item) for item in items if isinstance(item, dict)]

    def _row(self, item: dict[str, Any]) -> RawRow:
        values = {
            field: self._dig(item, path) for field, path in self.field_map.items()
        }
        required = {"brand", "model_name", "price_rub"}
        missing = [field for field in required if values.get(field) in (None, "")]
        if missing:
            raise CatalogSourceError(f"row is missing {', '.join(sorted(missing))}")
        price = _to_float(values.get("price_rub"))
        if price <= 0:
            raise CatalogSourceError(f"row has an unreadable price: {values.get('price_rub')!r}")
        return RawRow(
            brand=str(values.get("brand")),
            model_name=str(values.get("model_name")),
            os=str(values.get("os") or "windows"),
            form_factor=str(values.get("form_factor") or "laptop"),
            price_rub=price,
            cpu_score=_to_float(values.get("cpu_score")),
            ram_gb=_to_float(values.get("ram_gb")),
            weight_g=_to_float(values.get("weight_g")),
            battery_minutes=_to_float(values.get("battery_minutes")),
            screen_score=_to_float(values.get("screen_score")),
            warranty_months=_to_float(values.get("warranty_months")),
        )


class HtmlPageSource:
    """Reads a permitted HTML page with CSS selectors declared in JSON config.

    Config shape: {"url": ..., "item": "div.card", "fields": {"brand": ".brand",
    "model_name": ".title", "price_rub": {"selector": ".price", "regex": "[0-9 ]+"}}}
    """

    def __init__(self, config: dict[str, Any], *, fetch_html: Callable[[str], str] | None = None) -> None:
        self.url = str(config["url"])
        self.item = str(config["item"])
        self.fields: dict[str, Any] = dict(config.get("fields", {}))
        self.name = str(config.get("name") or f"html:{self.url}")
        self._fetch_html = fetch_html or self._http_html

    def _http_html(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise CatalogSourceError(f"{url}: {exc}") from exc

    def fetch(self) -> list[RawRow]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(self._fetch_html(self.url), "html.parser")
        rows: list[RawRow] = []
        for node in soup.select(self.item):
            values: dict[str, Any] = {}
            for field, spec in self.fields.items():
                selector = spec["selector"] if isinstance(spec, dict) else spec
                element = node.select_one(selector)
                if element is None:
                    values[field] = None
                    continue
                text = element.get_text(" ", strip=True)
                if isinstance(spec, dict) and spec.get("regex"):
                    match = re.search(spec["regex"], text)
                    text = match.group(0) if match else ""
                values[field] = text
            if values.get("brand") and values.get("model_name") and values.get("price_rub"):
                rows.append(self._row(values))
        if not rows:
            raise CatalogSourceError("no rows matched the configured selectors")
        return rows

    def _row(self, values: dict[str, Any]) -> RawRow:
        def number(field: str, default: float = 0.0) -> float:
            raw = values.get(field)
            if raw is None:
                return default
            cleaned = re.sub(r"[^0-9.,]", "", str(raw)).replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return default

        return RawRow(
            brand=str(values["brand"]).strip(),
            model_name=str(values["model_name"]).strip(),
            os="windows",
            form_factor="laptop",
            price_rub=number("price_rub"),
            cpu_score=number("cpu_score"),
            ram_gb=number("ram_gb"),
            weight_g=number("weight_g"),
            battery_minutes=number("battery_minutes"),
            screen_score=number("screen_score"),
            warranty_months=number("warranty_months", 12.0),
        )


class CsvSource:
    """A CSV export, used as the offline fallback."""

    REQUIRED = (
        "brand", "model_name", "os", "form_factor", "price_rub", "cpu_score",
        "ram_gb", "weight_g", "battery_minutes", "screen_score", "warranty_months",
    )

    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = f"csv:{path.name}"

    def fetch(self) -> list[RawRow]:
        rows: list[RawRow] = []
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = [c for c in self.REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                raise CatalogSourceError(f"CSV is missing columns: {', '.join(missing)}")
            for row in reader:
                rows.append(
                    RawRow(
                        brand=row["brand"].strip(),
                        model_name=row["model_name"].strip(),
                        os=row["os"].strip().lower(),
                        form_factor=row["form_factor"].strip().lower(),
                        price_rub=float(row["price_rub"].replace(" ", "").replace(",", ".")),
                        cpu_score=float(row["cpu_score"]),
                        ram_gb=float(row["ram_gb"]),
                        weight_g=float(row["weight_g"]),
                        battery_minutes=float(row["battery_minutes"]),
                        screen_score=float(row["screen_score"]),
                        warranty_months=float(row["warranty_months"]),
                    )
                )
        if not rows:
            raise CatalogSourceError("CSV contained no rows")
        return rows


def apply_rows(rows: list[RawRow], *, source: str) -> dict[str, Any]:
    """Validate and upsert rows, recording provenance on every touched model."""
    registry = load_registry()
    inserted = 0
    updated = 0
    errors: list[str] = []
    fetched_at = datetime.now(UTC)

    for row in rows:
        try:
            data = {
                "brand": row.brand,
                "model_name": row.model_name,
                "os": row.os,
                "form_factor": row.form_factor,
                "price_minor": int(round(row.price_rub * 100)),
                "cpu_score": int(row.cpu_score),
                "ram_gb": int(row.ram_gb),
                "weight_g": int(row.weight_g),
                "battery_minutes": int(row.battery_minutes),
                "screen_score": round(float(row.screen_score), 2),
                "warranty_months": int(row.warranty_months),
            }
            device = DeviceModel(
                id=uuid.uuid5(uuid.NAMESPACE_URL, f"{row.brand}|{row.model_name}"),
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
            data["slug"] = repo.slugify(data["brand"], data["model_name"])
        except (ValueError, TypeError, DomainError) as exc:
            errors.append(f"{row.brand} {row.model_name}: {exc}")
            continue

        existing = repo.find_by_natural_key(data["brand"], data["model_name"])
        if existing is None:
            repo.insert_model(data, source=source, fetched_at=fetched_at)
            inserted += 1
        else:
            repo.update_model(existing["id"], data, source=source, fetched_at=fetched_at)
            updated += 1

    return {
        "source": source,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "fetched_at": fetched_at.isoformat(),
    }


def configured_sources() -> list[CatalogSource]:
    """Build the source chain from environment configuration.

    ``CATALOG_LIVE_URL``      JSON feed of laptop rows (preferred)
    ``CATALOG_LIVE_ITEMS_PATH`` dotted path to the array (default ``products``)
    ``CATALOG_LIVE_FIELDS``   JSON object mapping RawRow fields to dotted paths
    ``CATALOG_HTML_CONFIG``   path to a JSON selector config for a permitted page
    ``CATALOG_CSV_PATH``      CSV export used as the fallback
    """
    import os

    sources: list[CatalogSource] = []
    live_url = os.environ.get("CATALOG_LIVE_URL")
    if live_url:
        fields = json.loads(os.environ.get("CATALOG_LIVE_FIELDS") or "{}")
        sources.append(
            JsonEndpointSource(
                live_url,
                items_path=os.environ.get("CATALOG_LIVE_ITEMS_PATH", "products"),
                field_map=fields,
            )
        )
    html_config = os.environ.get("CATALOG_HTML_CONFIG")
    if html_config:
        sources.append(HtmlPageSource(json.loads(Path(html_config).read_text(encoding="utf-8"))))
    csv_path = os.environ.get("CATALOG_CSV_PATH")
    if csv_path:
        sources.append(CsvSource(Path(csv_path)))
    return sources


def main(argv: list[str]) -> int:
    """CLI: refresh from CLI flags, else from environment, then print the result."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Refresh the catalog from a live source")
    parser.add_argument("--live-url")
    parser.add_argument("--items-path", default="products")
    parser.add_argument("--fields", help="JSON mapping of RawRow fields to dotted paths")
    parser.add_argument("--html-config")
    parser.add_argument("--csv")
    args = parser.parse_args(argv[1:])

    sources: list[CatalogSource] = []
    if args.live_url:
        import os

        fields_raw = args.fields or os.environ.get("CATALOG_LIVE_FIELDS") or "{}"
        sources.append(
            JsonEndpointSource(
                args.live_url,
                items_path=args.items_path,
                field_map=json.loads(fields_raw),
            )
        )
    if args.html_config:
        sources.append(HtmlPageSource(json.loads(Path(args.html_config).read_text(encoding="utf-8"))))
    if args.csv:
        sources.append(CsvSource(Path(args.csv)))
    sources = sources or configured_sources()

    if not sources:
        print(
            "no source configured: pass --live-url/--csv, or set CATALOG_LIVE_URL / CATALOG_CSV_PATH",
            file=sys.stderr,
        )
        return 2

    result = refresh(sources)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["source"] else 1


def refresh(sources: list[CatalogSource]) -> dict[str, Any]:
    """Try each source in order; the first that yields rows wins.

    Returns a result with ``fallback_errors`` describing why earlier sources were
    skipped. Existing data is never cleared by a failed refresh.
    """
    failures: list[str] = []
    for source in sources:
        try:
            rows = source.fetch()
            result = apply_rows(rows, source=source.name)
        except CatalogSourceError as exc:
            failures.append(f"{source.name}: {exc}")
            continue
        if result["inserted"] == 0 and result["updated"] == 0:
            failures.append(f"{source.name}: every row was invalid")
            continue
        result["fallback_errors"] = failures
        return result
    return {
        "source": None,
        "inserted": 0,
        "updated": 0,
        "errors": [],
        "fallback_errors": failures,
        "fetched_at": None,
    }


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
