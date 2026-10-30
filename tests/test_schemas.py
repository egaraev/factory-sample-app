"""Unit tests for the Pydantic task schemas in :mod:`app.schemas`."""

import pytest

from app.schemas import Task, TaskCreate, TaskUpdate


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