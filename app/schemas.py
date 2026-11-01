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

    Unlike :class:`TaskUpdate`, the ``done` flag is required so the completion
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

    ``order_total`` must be a positive number (``gt=0``) — zero, negative, or
    non-numeric input is rejected with ``422`` before any calculation happens.
    ``customer_tier`` is a plain string: anything other than exactly
    ``"gold"``/``"silver"`` simply earns no discount (treated as bronze).
    """

    order_total: float = Field(..., gt=0)
    customer_tier: str


class DiscountResponse(BaseModel):
    """Discount percentage returned by the discount endpoint.

    The field name and the on-the-wire key are the same string,
    ``discount_percentage`` — there is deliberately no alias on this model, so
    FastAPI's response body is ``{"discount_percentage": ...}`` (matching the
    endpoint contract and README).
    """

    discount_percentage: float = Field(...)