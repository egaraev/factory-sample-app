"""Unit tests for the Pydantic task schemas in :mod:`app.schemas`."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    DiscountRequest,
    DiscountResponse,
    Task,
    TaskComplete,
    TaskCreate,
    TaskUpdate,
)


def test_task_create_requires_title():
    with pytest.raises(ValueError):
        TaskCreate()  # type: ignore[call-arg]


def test_task_create_defaults_done_to_false():
    task = TaskCreate(title="Buy milk")

    assert task.title == "Buy milk"
    assert task.done is False


def test_task_create_accepts_explicit_done_flag():
    done = TaskCreate(title="Walk dog", done=True)
    not_done = TaskCreate(title="Buy milk", done=False)

    assert done.done is True
    assert not_done.done is False


def test_task_update_allows_empty_body():
    update = TaskUpdate()

    assert update.title is None
    assert update.done is None


def test_task_update_supports_partial_bodies():
    title_only = TaskUpdate(title="New title")
    assert title_only.title == "New title"
    assert title_only.done is None

    done_only = TaskUpdate(done=True)
    assert done_only.title is None
    assert done_only.done is True


def test_task_complete_requires_done():
    with pytest.raises(ValueError):
        TaskComplete()  # type: ignore[call-arg]


def test_task_complete_constructs_with_explicit_done_flag():
    completed = TaskComplete(done=True)
    not_completed = TaskComplete(done=False)

    assert completed.done is True
    assert not_completed.done is False


def test_task_requires_all_fields():
    with pytest.raises(ValueError):
        Task(id=1, title="Buy milk")  # type: ignore[call-arg]


def test_task_exposes_all_fields():
    task = Task(id=3, title="Walk dog", done=True)

    assert task.id == 3
    assert task.title == "Walk dog"
    assert task.done is True


def test_task_serializes_all_three_fields():
    task = Task(id=3, title="Walk dog", done=True)
    if hasattr(task, "model_dump"):  # Pydantic v2
        dumped = task.model_dump()
    else:  # Pydantic v1
        dumped = task.dict()

    assert dumped == {"id": 3, "title": "Walk dog", "done": True}


def test_discount_request_accepts_positive_order_total():
    request = DiscountRequest(order_total=150.0, customer_tier="gold")

    assert request.order_total == 150.0
    assert request.customer_tier == "gold"


@pytest.mark.parametrize("order_total", [0, -0.01, -5])
def test_discount_request_rejects_non_positive_order_total(order_total):
    with pytest.raises(ValidationError):
        DiscountRequest(order_total=order_total, customer_tier="gold")


@pytest.mark.parametrize("customer_tier", ["gold", "silver", "bronze", "platinum"])
def test_discount_request_accepts_any_string_customer_tier(customer_tier):
    request = DiscountRequest(order_total=1.0, customer_tier=customer_tier)

    assert request.customer_tier == customer_tier


def test_discount_response_requires_discount():
    with pytest.raises(ValueError):
        DiscountResponse()  # type: ignore[call-arg]


def test_discount_response_serializes_discount():
    response = DiscountResponse(discount=15.0)

    assert response.discount == 15.0
    if hasattr(response, "model_dump"):  # Pydantic v2
        dumped = response.model_dump()
    else:  # Pydantic v1
        dumped = response.dict()

    assert dumped == {"discount": 15.0}


def test_discount_response_wire_name_matches_endpoint_contract():
    """Lock the on-the-wire key so schema and endpoint behavior agree."""
    response = DiscountResponse(discount=10.0)

    if hasattr(response, "model_dump"):  # Pydantic v2
        by_alias = response.model_dump(by_alias=True)
        json_body = response.model_dump_json()
    else:  # Pydantic v1
        by_alias = response.dict(by_alias=True)
        json_body = response.json()

    assert by_alias == {"discount": 10.0}
    assert json_body in ('{"discount": 10.0}', '{"discount":10.0}')