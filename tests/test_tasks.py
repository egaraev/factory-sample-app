"""API-level tests for the task CRUD endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


@pytest.fixture(autouse=True)
def isolated_storage_file(tmp_path, monkeypatch):
    """Point storage at a temporary file and restore it after each test."""
    original = storage.DATA_FILE
    storage.set_data_file(tmp_path / "tasks.json")
    yield
    storage.set_data_file(original)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _create_task(client, title, done=False):
    response = client.post("/tasks", json={"title": title, "done": done})
    assert response.status_code == 201
    return response.json()


def test_create_task_returns_201_and_defaults_done_to_false(client):
    response = client.post("/tasks", json={"title": "Buy milk"})

    assert response.status_code == 201
    body = response.json()

    assert body["id"] == 1
    assert body["title"] == "Buy milk"
    assert body["done"] is False


def test_create_task_accepts_explicit_done_flag(client):
    _create_task(client, "Walk dog", done=True)

    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "Walk dog", "done": True}
    ]


def test_list_tasks_returns_all_tasks_in_id_order(client):
    first = _create_task(client, "First")
    second = _create_task(client, "Second", done=True)
    third = _create_task(client, "Third")

    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == [first, second, third]


def test_get_task_returns_existing_task(client):
    task = _create_task(client, "Buy milk", done=True)

    response = client.get(f"/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json() == task


def test_get_task_returns_not_found_for_missing_id(client):
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_update_task_changes_title_and_done_status(client):
    task = _create_task(client, "Original title")

    updated_title = client.put(
        f"/tasks/{task['id']}", json={"title": "Updated title"}
    )

    assert updated_title.status_code == 200
    body = updated_title.json()
    assert body["id"] == task["id"]
    assert body["title"] == "Updated title"
    assert body["done"] is False

    updated_done = client.put(f"/tasks/{task['id']}", json={"done": True})

    assert updated_done.status_code == 200
    body = updated_done.json()
    assert body["title"] == "Updated title"
    assert body["done"] is True


def test_update_task_returns_not_found_for_missing_id(client):
    response = client.put("/tasks/999", json={"title": "Missing task"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_delete_task_removes_task_and_returns_no_content(client):
    task = _create_task(client, "Delete me")

    response = client.delete(f"/tasks/{task['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{task['id']}").status_code == 404
    assert client.get("/tasks").json() == []


def test_delete_task_returns_not_found_for_missing_id(client):
    response = client.delete("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_tasks_are_persisted_to_json_file_and_visible_after_restart(client, tmp_path: Path):
    task = _create_task(client, "Persist me")
    data_file = tmp_path / "tasks.json"

    assert data_file.exists()
    assert '"title": "Persist me"' in data_file.read_text(encoding="utf-8")

    with TestClient(app) as restarted_client:
        response = restarted_client.get(f"/tasks/{task['id']}")

        assert response.status_code == 200
        assert response.json() == task
