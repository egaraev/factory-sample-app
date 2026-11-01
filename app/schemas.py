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

    The Pydantic field is named ``discount_percentage`` (KAN-88), but it is
    serialized on the wire as ``"discount"`` via its alias — so a plain
    :meth:`model_dump` reports the field name, while JSON serialization (which
    uses aliases by default) emits the shorter ``"discount"`` key. This keeps
    the endpoint contract stable: both this schema and the endpoint tests/README
    agree the response body is ``{"discount": ...}``.
    """

    discount_percentage: float = Field(..., alias="discount")