"""Order discount calculation and its HTTP endpoint.

``calculate_discount`` is a pure, framework-independent function (mirroring
how :mod:`app.storage` stays independent of FastAPI), so the tier/total rules
can be unit-tested and reused without any HTTP layer. The router below wires
that same function into the API as ``POST /discount``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas import DiscountRequest, DiscountResponse

router = APIRouter(tags=["discount"])


def calculate_discount(order_total: float, customer_tier: str) -> float:
    """Return the discount percentage to apply to an order.

    Rules (the 100 boundary is inclusive):

    - ``"gold"``: 15% if ``order_total >= 100``, else 5%
    - ``"silver"``: 10% if ``order_total >= 100``, else 0%
    - ``"bronze"`` (and any other/unrecognized tier): 0% regardless of total

    Tier matching is a simple exact match; only the literal strings
    ``"gold"`` and ``"silver"`` earn a discount.

    Raises:
        ValueError: If ``order_total`` is zero or negative.
    """
    if order_total <= 0:
        raise ValueError("order_total must be positive")

    if customer_tier == "gold":
        return 15.0 if order_total >= 100 else 5.0
    if customer_tier == "silver":
        return 10.0 if order_total >= 100 else 0.0
    # "bronze" and any other unrecognized tier get no discount.
    return 0.0


@router.post("/discount", response_model=DiscountResponse)
def get_discount(payload: DiscountRequest):
    """Return the discount percentage for an order total and customer tier."""
    try:
        discount = calculate_discount(payload.order_total, payload.customer_tier)
    except ValueError as exc:
        # The request schema already rejects non-positive totals with 422;
        # this keeps calculate_discount's documented contract intact for any
        # other path by translating the error into an HTTP response.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return DiscountResponse(discount_percentage=discount)
