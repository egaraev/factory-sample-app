"""Pydantic request/response schemas for the task and discount endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """Payload for creating a new task."""

    title: str
    done: bool = False


class TaskUpdate(BaseModel):
    """Payload for partially updating a task; fields left as ``None`` are unchanged."""

    title: Optional[str] = None
    done: Optional[bool] = None


class TaskComplete(BaseModel):
    """Payload for marking a task complete or incomplete.

    Unlike :class:`TaskUpdate`, the ``done`` flag is required so the completion
    endpoint cannot accept an empty body.
    """

    done: bool


class Task(BaseModel):
    """A task as returned by the API."""

    id: int
    title: str
    done: bool


class DiscountRequest(BaseModel):
    """Payload for the discount endpoint.

    ``order_total`` must be a positive number — zero, negative, or non-numeric
    input is rejected with ``422`` before any calculation happens.
    ``customer_tier`` is a plain string: anything other than exactly
    ``"gold"``/``"silver"`` simply earns no discount (treated as bronze).
    """

    order_total: float = Field(..., gt=0)
    customer_tier: str


class DiscountResponse(BaseModel):
    """Discount percentage returned by the discount endpoint.

    The field is named ``discount_percentage`` internally (see KAN-88), but is
    serialized as ``"discount"`` in API responses via ``serialization_alias``,
    so a default ``model_dump()`` still reports the field name while the JSON
    body served by FastAPI exposes it under its shorter wire name.
    """

    discount_percentage: float = Field(..., serialization_alias="discount")