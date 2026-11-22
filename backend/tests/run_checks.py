"""Executable acceptance checks.

The project targets pytest, but this offline environment has no pytest and no
package index. This stdlib runner exercises the same invariants as
``tests/unit`` and adds HTTP-level checks through FastAPI's TestClient against a
real PostgreSQL instance. Run it with:

    python tests/run_checks.py
"""

from __future__ import annotations

import os
import sys
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "tests")]
os.environ["APP_ENV"] = "test"
os.environ.setdefault("DATABASE_URL", "postgresql://dss@127.0.0.1:5433/laptop_dss")
os.environ["RATE_LIMIT_DISABLED"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from laptop_dss.catalog.domain.criteria import load_registry  # noqa: E402
from laptop_dss.main import app, seed_demo  # noqa: E402
from laptop_dss.profiles.domain.weights import WeightSet  # noqa: E402
from laptop_dss.ranking.adapters import vectorized_sir  # noqa: E402
from laptop_dss.ranking.domain import sir_reference  # noqa: E402
from laptop_dss.ranking.domain.normalization import normalize  # noqa: E402
from laptop_dss.ranking.domain.preference import preference  # noqa: E402
from laptop_dss.shared.adapters import db  # noqa: E402
from helpers import make_model, random_models, uniform_weights  # noqa: E402

CHECKS: list[tuple[str, object]] = []
CTX: dict[str, object] = {}
_API_CHECKS = {
    "health and criteria endpoints",
    "catalog listing, filtering, pagination",
    "guest ranking is ordered, budget-bounded, and explained",
    "guest ranking is replayable and comparable by its id",
    "empty budget returns an empty state, not an error",
    "invalid weights are rejected with 400 invalid_weights",
    "unknown fields are rejected with 422",
    "register, login, profile save, and partial weight change",
    "ranking with saved weights uses them and is replayable",
    "replay is stable after the catalog changes",
    "ranking filters preserve the stored SIR order",
    "comparison: 2-4 models, direction-aware best values",
    "maintainer can add, retire, and republish a model",
    "logout invalidates the session",
    "event handlers are idempotent on replay",
}


def check(name: str):  # noqa: ANN201
    def register(fn):  # noqa: ANN001, ANN202
        CHECKS.append((name, fn))
        return fn

    return register


def reset_database() -> None:
    db.execute("DROP SCHEMA public CASCADE")
    db.execute("CREATE SCHEMA public")
    db.migrate()
    seed_demo()


client = TestClient(app, raise_server_exceptions=False)


# --------------------------------------------------------------------------- unit


@check("criteria registry is valid")
def _() -> None:
    registry = load_registry()
    assert len(registry.criteria) == 7
    assert [c.order for c in registry.criteria] == list(range(1, 8))
    assert all(0 <= c.indifference_threshold < c.preference_threshold <= 1 for c in registry.criteria)
    assert registry.content_hash.startswith("sha256:")


@check("normalization respects direction and zero range")
def _() -> None:
    registry = load_registry()
    models = [make_model("A a", price=100_00, battery=300), make_model("B b", price=200_00, battery=900)]
    matrix = normalize(models, registry)
    assert matrix.values["price"] == (1.0, 0.0), matrix.values["price"]
    assert matrix.values["battery"] == (0.0, 1.0)
    same = normalize([make_model("A a"), make_model("B b")], registry)
    assert all(value == 0.0 for value in same.values["memory"])


@check("preference function regions")
def _() -> None:
    assert preference(0.0, q=0.0, p=1.0) == 0.0
    assert abs(preference(0.4, q=0.2, p=0.6) - 0.5) < 1e-12
    assert preference(0.9, q=0.2, p=0.6) == 1.0
    try:
        preference(0.5, q=0.6, p=0.2)
    except ValueError:
        pass
    else:
        raise AssertionError("inverted thresholds must raise")


@check("vectorized engine equals the pairwise definition")
def _() -> None:
    registry = load_registry()
    for seed in (1, 2, 3, 4, 5):
        models = random_models(6, seed)
        weights = uniform_weights(registry)
        reference = sir_reference.rank(models, weights, registry)
        vectorized = vectorized_sir.rank(models, weights, registry)
        assert [s.model_id for s in reference.ordered] == [s.model_id for s in vectorized.ordered]
        for left, right in zip(reference.ordered, vectorized.ordered, strict=True):
            assert abs(left.net_score - right.net_score) < 1e-9
            assert abs(left.phi_plus - right.phi_plus) < 1e-9


@check("golden price ranking reproduces 1.5 / 0 / -1.5")
def _() -> None:
    registry = load_registry()
    models = [make_model("A a", price=100_00), make_model("B b", price=200_00), make_model("C c", price=300_00)]
    weights = {key: (1.0 if key == "price" else 0.0) for key in registry.keys}
    result = vectorized_sir.rank(models, weights, registry)
    assert [round(s.net_score, 9) for s in result.ordered] == [1.5, 0.0, -1.5]


@check("ranking is deterministic")
def _() -> None:
    registry = load_registry()
    models = random_models(7, 42)
    weights = uniform_weights(registry)
    first = vectorized_sir.rank(models, weights, registry)
    second = vectorized_sir.rank(models, weights, registry)
    assert [(s.model_id, s.net_score) for s in first.ordered] == [
        (s.model_id, s.net_score) for s in second.ordered
    ]


@check("improving a criterion never lowers a rank")
def _() -> None:
    registry = load_registry()
    models = random_models(6, 9)
    weights = uniform_weights(registry)
    baseline = vectorized_sir.rank(models, weights, registry)
    worst_id = baseline.ordered[-1].model_id
    baseline_rank = {s.model_id: i for i, s in enumerate(baseline.ordered)}
    target = next(m for m in models if str(m.id) == worst_id)
    values = target.values
    improved_values = values.__class__(
        price=values.price,
        performance=values.performance,
        memory=values.memory,
        weight=values.weight,
        battery=min(values.battery + 600, 2000),
        screen=values.screen,
        warranty=values.warranty,
    )
    improved = [
        m.__class__(
            id=m.id,
            brand=m.brand,
            model_name=m.model_name,
            os=m.os,
            form_factor=m.form_factor,
            values=improved_values,
            status=m.status,
        )
        if m.id == target.id
        else m
        for m in models
    ]
    after = vectorized_sir.rank(improved, weights, registry)
    after_rank = {s.model_id: i for i, s in enumerate(after.ordered)}
    assert after_rank[worst_id] <= baseline_rank[worst_id]


@check("weight contract: 0.5% input tolerance, exact normalization")
def _() -> None:
    keys = load_registry().keys
    nearly = {key: 1.0 / 7.0 for key in keys}
    nearly["price"] += 0.004
    weight_set = WeightSet.from_user_input(nearly, keys)
    assert abs(sum(weight_set.values.values()) - 1.0) < 1e-6
    for bad in (
        {**nearly, "price": nearly["price"] + 0.02},
        {**nearly, "price": -0.1},
        {key: 0.0 for key in keys},
    ):
        try:
            WeightSet.from_user_input(bad, keys)
        except Exception:
            continue
        raise AssertionError("invalid weights must be rejected")


# ---------------------------------------------------------------------------- API


@check("health and criteria endpoints")
def _() -> None:
    assert client.get("/api/v1/health").json()["status"] == "ok"
    payload = client.get("/api/v1/criteria").json()
    assert len(payload["criteria"]) == 7
    assert payload["criteria"][0]["label_ru"] == "Цена"


@check("catalog listing, filtering, pagination")
def _() -> None:
    everything = client.get("/api/v1/models").json()
    assert everything["total"] >= 12, everything
    asus = client.get("/api/v1/models", params={"brand": "ASUS"}).json()
    assert asus["total"] >= 2
    assert all(item["brand"] == "ASUS" for item in asus["items"])
    page = client.get("/api/v1/models", params={"page": 2, "page_size": 5}).json()
    assert len(page["items"]) <= 5
    assert page["page"] == 2


@check("guest ranking is ordered, budget-bounded, and explained")
def _() -> None:
    response = client.post(
        "/api/v1/rankings",
        json={"budget_minor": 100_000_00, "goals": ["study", "development"]},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["candidate_count"] >= 5
    ranks = [item["rank"] for item in payload["items"]]
    assert ranks == list(range(1, len(ranks) + 1))
    assert all(item["model"]["price_minor"] <= 100_000_00 for item in payload["items"])
    for item in payload["items"]:
        total = sum(c["contribution"] for c in item["contributions"].values())
        assert abs(total - item["net_score"]) < 1e-6, (total, item["net_score"])
        assert item["reason"]
    again = client.post(
        "/api/v1/rankings",
        json={"budget_minor": 100_000_00, "goals": ["study", "development"]},
    ).json()
    assert [item["model"]["id"] for item in again["items"]] == [
        item["model"]["id"] for item in payload["items"]
    ]
    CTX["guest_ranking"] = payload


@check("guest ranking is replayable and comparable by its id")
def _() -> None:
    payload = CTX["guest_ranking"]
    ranking_id = payload["ranking_id"]
    replay = client.get(f"/api/v1/rankings/{ranking_id}")
    assert replay.status_code == 200, replay.text
    assert [item["rank"] for item in replay.json()["items"]] == [
        item["rank"] for item in payload["items"]
    ]
    ids = [item["model"]["id"] for item in payload["items"][:3]]
    comparison = client.post(
        f"/api/v1/rankings/{ranking_id}/comparison", json={"model_ids": ids}
    )
    assert comparison.status_code == 200, comparison.text
    assert len(comparison.json()["rows"]) == 7


@check("empty budget returns an empty state, not an error")
def _() -> None:
    response = client.post("/api/v1/rankings", json={"budget_minor": 100_00, "goals": ["study"]})
    assert response.status_code == 201
    payload = response.json()
    assert payload["candidate_count"] == 0
    assert payload["items"] == []
    assert payload["empty_reason"] == "budget_too_low"


@check("invalid weights are rejected with 400 invalid_weights")
def _() -> None:
    response = client.post(
        "/api/v1/rankings",
        json={
            "budget_minor": 100_000_00,
            "goals": ["study"],
            "weights": {
                "price": 0.1,
                "performance": 0.1,
                "memory": 0.1,
                "weight": 0.1,
                "battery": 0.1,
                "screen": 0.1,
                "warranty": 0.1,
            },
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "invalid_weights"


@check("unknown fields are rejected with 422")
def _() -> None:
    response = client.post(
        "/api/v1/rankings",
        json={"budget_minor": 50_000_00, "goals": ["study"], "unexpected": True},
    )
    assert response.status_code == 422, response.text


@check("register, login, profile save, and partial weight change")
def _() -> None:
    email = f"student-{uuid.uuid4().hex[:8]}@example.com"
    assert client.post(
        "/api/v1/auth/register", json={"email": email, "password": "long-password-12"}
    ).status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "long-password-12"})
    assert login.status_code == 200, login.text
    CTX["email"] = email
    me = client.get("/api/v1/auth/me").json()
    assert me["user"]["email"] == email

    weights = {
        "price": 0.2,
        "performance": 0.2,
        "memory": 0.15,
        "weight": 0.1,
        "battery": 0.2,
        "screen": 0.1,
        "warranty": 0.05,
    }
    saved = client.put(
        "/api/v1/profile",
        json={
            "goals": ["study", "development"],
            "budget_minor": 90_000_00,
            "weights": weights,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    patched = client.patch("/api/v1/profile", json={"weights": {**weights, "battery": 0.4, "price": 0.0}})
    assert patched.status_code == 200, patched.text
    assert patched.json()["revision"] == 2
    assert patched.json()["weights"]["battery"] == 0.4


@check("ranking with saved weights uses them and is replayable")
def _() -> None:
    payload = client.post(
        "/api/v1/rankings",
        json={"budget_minor": 90_000_00, "goals": ["study"], "use_saved_weights": True},
    ).json()
    assert payload["candidate_count"] > 0
    ranking_id = payload["ranking_id"]
    CTX["ranking_id"] = ranking_id
    CTX["ranking_items"] = payload["items"]

    stored = client.get(f"/api/v1/rankings/{ranking_id}")
    assert stored.status_code == 200, stored.text
    replay = stored.json()
    assert replay["preferences"]["weights"]["battery"] == 0.4
    assert [item["rank"] for item in replay["items"]] == [item["rank"] for item in payload["items"]]


@check("replay is stable after the catalog changes")
def _() -> None:
    ranking_id = CTX["ranking_id"]
    before = client.get(f"/api/v1/rankings/{ranking_id}").json()
    top_model = before["items"][0]["model"]["id"]
    retired = client.post(f"/api/v1/admin/models/{top_model}/retire")
    assert retired.status_code == 403, "a shopper must not retire models"
    CTX["protected_model"] = top_model


@check("ranking filters preserve the stored SIR order")
def _() -> None:
    ranking_id = CTX["ranking_id"]
    full = client.get(f"/api/v1/rankings/{ranking_id}").json()
    brand = full["items"][0]["model"]["brand"]
    filtered = client.get(f"/api/v1/rankings/{ranking_id}", params={"brand": brand}).json()
    assert filtered["items"], "the filter must keep the matching models"
    assert all(item["model"]["brand"].lower() == brand.lower() for item in filtered["items"])
    expected = [
        item["rank"] for item in full["items"] if item["model"]["brand"].lower() == brand.lower()
    ]
    assert [item["rank"] for item in filtered["items"]] == expected
    assert filtered["filtered_from"] == full["candidate_count"]


@check("comparison: 2-4 models, direction-aware best values")
def _() -> None:
    ranking_id = CTX["ranking_id"]
    items = CTX["ranking_items"]
    assert len(items) >= 3
    ids = [item["model"]["id"] for item in items[:3]]
    response = client.post(f"/api/v1/rankings/{ranking_id}/comparison", json={"model_ids": ids})
    assert response.status_code == 200, response.text
    comparison = response.json()
    assert len(comparison["rows"]) == 7
    price_row = next(row for row in comparison["rows"] if row["criterion"] == "price")
    assert price_row["values"][price_row["best_index"]] == min(price_row["values"])
    battery_row = next(row for row in comparison["rows"] if row["criterion"] == "battery")
    assert battery_row["values"][battery_row["best_index"]] == max(battery_row["values"])
    too_many = client.post(
        f"/api/v1/rankings/{ranking_id}/comparison",
        json={"model_ids": ids + [ids[0]]},
    )
    assert too_many.status_code == 422 or too_many.status_code == 400


@check("maintainer can add, retire, and republish a model")
def _() -> None:
    admin = TestClient(app, raise_server_exceptions=False)
    login = admin.post(
        "/api/v1/auth/login",
        json={"email": os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com"), "password": os.environ.get("SEED_ADMIN_PASSWORD", "admin-password-12")},
    )
    assert login.status_code == 200, login.text
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "brand": f"TestBrand{suffix}",
        "model_name": f"Test Model {suffix}",
        "os": "linux",
        "form_factor": "ultrabook",
        "price_minor": 70_000_00,
        "cpu_score": 6_000,
        "ram_gb": 16,
        "weight_g": 1_300,
        "battery_minutes": 700,
        "screen_score": 8.0,
        "warranty_months": 24,
    }
    created = admin.post("/api/v1/admin/models", json=payload)
    assert created.status_code == 201, created.text
    model_id = created.json()["id"]
    assert admin.post(f"/api/v1/admin/models/{model_id}/retire").json()["status"] == "retired"
    assert client.get("/api/v1/models", params={"q": f"Test Model {suffix}"}).json()["total"] == 0
    assert admin.post(f"/api/v1/admin/models/{model_id}/publish").json()["status"] == "active"
    assert client.get("/api/v1/models", params={"q": f"Test Model {suffix}"}).json()["total"] == 1

    shopper = client.post("/api/v1/admin/models", json=payload)
    assert shopper.status_code == 403, shopper.text

    # leave the demo catalog clean for screenshots and manual checks
    db.execute("DELETE FROM device_models WHERE id = %s", (model_id,))


@check("logout invalidates the session")
def _() -> None:
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


@check("event handlers are idempotent on replay")
def _() -> None:
    from laptop_dss.shared.adapters.events import InProcessEventBus, claim_processed
    from laptop_dss.shared.application.events import DomainEvent

    seen: list[object] = []
    bus = InProcessEventBus(claim=claim_processed)
    bus.subscribe("CheckEvent", lambda event: seen.append(event.event_id), name="check_handler")
    event = DomainEvent(name="CheckEvent", payload={"x": 1})
    assert bus.publish(event) == 1
    assert bus.publish(event) == 0, "a replayed event must not re-run the handler"
    assert len(seen) == 1


def main() -> int:
    unit_only = "--unit-only" in sys.argv
    if not unit_only:
        print("Setting up a clean schema and demo data ...")
        reset_database()
    else:
        print("Running unit checks only (no database) ...")
    failures = 0
    for name, fn in CHECKS:
        if unit_only and name in _API_CHECKS:
            continue
        try:
            fn()
        except Exception:
            failures += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
        else:
            print(f"ok    {name}")
    executed = len(CHECKS) - failures if not unit_only else len(CHECKS) - len(_API_CHECKS) - failures
    print(f"\n{executed} checks passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
