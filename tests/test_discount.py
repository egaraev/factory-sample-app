"""Spec tests for KAN-87 (and the KAN-86 endpoint slice).

These tests lock the contract for ``app.discount.calculate_discount`` — the
pure business logic, importable from ``app.discount`` before any HTTP layer
exists — and for the discount endpoint wired into the existing FastAPI app.
The implementation has to satisfy these, not the other way around.
"""

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.discount import calculate_discount
from app.main import app


@pytest.fixture(autouse=True)
def isolated_storage_file(tmp_path):
    """Point storage at a per-test temporary SQLite database file.

    Opening ``TestClient(app)`` as a context manager runs the app's startup
    hook, which eagerly initializes the configured DB path — so even though
    the discount endpoint itself is stateless, every test here must redirect
    storage to ``tmp_path`` first (same convention as ``tests/test_tasks.py``).
    """
    original = storage.DB_PATH
    storage.set_db_path(tmp_path / "tasks.db")
    try:
        yield
    finally:
        storage.set_db_path(original)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# KAN-87: pure function contract — app.discount.calculate_discount
# ---------------------------------------------------------------------------

# (order_total, customer_tier) -> expected discount percentage.
DISCOUNT_CASES = [
    # gold: 15% at/above the $100 boundary, 5% below it.
    (99.99, "gold", 5),
    (100, "gold", 15),
    (100.00, "gold", 15),
    (100.01, "gold", 15),
    (120, "gold", 15),
    (999, "gold", 15),
    (1, "gold", 5),
    (0.99, "gold", 5),
    # silver: 10% at/above the boundary, 0% below it.
    (99.99, "silver", 0),
    (100, "silver", 10),
    (100.01, "silver", 10),
    (250, "silver", 10),
    (5, "silver", 0),
    (1, "silver", 0),
    # bronze: 0% regardless of order_total — the boundary is irrelevant.
    (99.99, "bronze", 0),
    (100, "bronze", 0),
    (5000, "bronze", 0),
]


@pytest.mark.parametrize(("order_total", "tier", "expected"), DISCOUNT_CASES)
def test_calculate_discount_tier_and_total_matrix(order_total, tier, expected):
    assert calculate_discount(order_total, tier) == expected


# "bronze (or any other tier)": every unrecognized tier string is bronze-
# equivalent — 0% regardless of total. Tier matching is a simple exact match,
# so anything that is not literally "gold"/"silver" falls through to 0%.
UNKNOWN_TIERS = ("bronze", "platinum", "diamond", "member", "", "GOLD")


@pytest.mark.parametrize("tier", UNKNOWN_TIERS)
def test_unrecognized_tier_always_gets_zero_discount(tier):
    for order_total in (1, 99.99, 100, 100.01, 1000):
        assert calculate_discount(order_total, tier) == 0


@pytest.mark.parametrize("order_total", (0, 0.0, -0.01, -1, -100, -99999))
def test_calculate_discount_raises_value_error_for_non_positive_total(order_total):
    with pytest.raises(ValueError):
        calculate_discount(order_total, "gold")

    # The check applies to every tier, not just the discounting ones.
    with pytest.raises(ValueError):
        calculate_discount(order_total, "silver")

    with pytest.raises(ValueError):
        calculate_discount(order_total, "bronze")


def test_calculate_discount_returns_a_number():
    # Guard against stringified percentages or other non-numeric returns; the
    # value must be directly comparable as a number (float per the signature).
    result = calculate_discount(150, "gold")
    assert isinstance(result, (int, float))
    assert not isinstance(result, bool)
    assert result == 15


# ---------------------------------------------------------------------------
# KAN-86 endpoint: POST /discount on the existing FastAPI app
# ---------------------------------------------------------------------------

DISCOUNT_ENDPOINT_CASES = [
    # (order_total, customer_tier, expected percentage in the response body)
    (150.0, "gold", 15),
    (99.99, "gold", 5),
    (100.0, "silver", 10),
    (50.0, "silver", 0),
    (100.0, "bronze", 0),
    (250.0, "platinum", 0),
]


@pytest.mark.parametrize(("order_total", "tier", "expected"), DISCOUNT_ENDPOINT_CASES)
def test_discount_endpoint_returns_computed_percentage(client, order_total, tier, expected):
    response = client.post(
        "/discount", json={"order_total": order_total, "customer_tier": tier}
    )

    assert response.status_code == 200
    assert response.json()["discount"] == expected


def test_discount_endpoint_boundary_is_inclusive_at_100(client):
    gold = client.post(
        "/discount", json={"order_total": 100, "customer_tier": "gold"}
    )
    silver = client.post(
        "/discount", json={"order_total": 100, "customer_tier": "silver"}
    )

    assert gold.status_code == 200
    assert gold.json()["discount"] == 15

    assert silver.status_code == 200
    assert silver.json()["discount"] == 10


# Request validation: order_total must be a positive number, rejected by the
# schema (422) before any calculation happens.
@pytest.mark.parametrize("order_total", (0, -5, -0.01))
def test_discount_endpoint_rejects_non_positive_order_total(client, order_total):
    response = client.post(
        "/discount", json={"order_total": order_total, "customer_tier": "gold"}
    )

    assert response.status_code == 422


@pytest.mark.parametrize("order_total", ("abc", None))
def test_discount_endpoint_rejects_non_numeric_order_total(client, order_total):
    response = client.post(
        "/discount", json={"order_total": order_total, "customer_tier": "gold"}
    )

    assert response.status_code == 422


def test_discount_endpoint_rejects_missing_fields(client):
    missing_total = client.post("/discount", json={"customer_tier": "gold"})
    assert missing_total.status_code == 422

    missing_tier = client.post("/discount", json={"order_total": 150})
    assert missing_tier.status_code == 422

    empty_body = client.post("/discount", json={})
    assert empty_body.status_code == 422