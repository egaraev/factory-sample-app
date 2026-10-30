"""API-level tests for the task CRUD endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db_file(tmp_path, monkeypatch):
    """Point storage at a temporary database file and restore it after each test."""
    original = storage.DB_PATH
    storage.set_db_path(tmp_path / "tasks.db")
    yield
    storage.set_db_path(original)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _create_task(client, title, done=False):
    response = client.post("/tasks", json={"title": title, "done": done})
    assert response.status_code == 201
    return response.json()


def _tables(db_path: Path) -> set:
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def test_startup_creates_database_before_first_request(tmp_path: Path):
    """KAN-26: a fresh DB_PATH must be fully set up before any request is served."""
    db_file = tmp_path / "fresh" / "tasks.db"
    storage.set_db_path(db_file)

    with TestClient(app) as test_client:
        # The startup hook (not the first request) must have created the file,
        # its parent directory, and the tasks table.
        assert db_file.parent.is_dir()
        assert db_file.exists()
        assert "tasks" in _tables(db_file)

        # The first request hits an already-initialized database and sees an
        # empty list — no lazy setup is visible to the caller.
        response = test_client.get("/tasks")

        assert response.status_code == 200
        assert response.json() == []


def test_startup_fails_fast_when_db_path_is_unusable(tmp_path: Path):
    """KAN-26: a misconfigured DB_PATH must fail at startup, not on first write."""
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("a regular file blocking the database path")
    storage.set_db_path(blocker / "tasks.db")

    with pytest.raises(RuntimeError, match="Could not initialize the task database"):
        with TestClient(app) as test_client:  # pragma: no cover - startup raises
            test_client.get("/tasks")


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


def test_tasks_are_persisted_to_sqlite_file_and_visible_after_restart(
    client, tmp_path: Path
):
    """KAN-28: tasks must persist to the SQLite file and be visible after restart.

    Creates a task through the API, then verifies persistence by querying the
    temporary SQLite file directly (rather than parsing JSON) before simulating
    a process restart with a fresh ``TestClient`` pointed at the same storage
    path.
    """
    task = _create_task(client, "Persist me")
    db_file = tmp_path / "tasks.db"

    assert db_file.exists()

    # Query the temporary SQLite file directly: the committed row must match
    # what the API returned (``done`` is stored as 0/1 in the database).
    import sqlite3

    conn = sqlite3.connect(str(db_file))
    try:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    finally:
        conn.close()

    assert rows == [(task["id"], task["title"], int(task["done"]))]

    # A fresh ``TestClient`` against the same path simulates a restart: it sees
    # exactly what was committed to the SQLite file.
    with TestClient(app) as restarted_client:
        response = restarted_client.get(f"/tasks/{task['id']}")

        assert response.status_code == 200
        assert response.json() == task


def test_task_data_survives_simulated_process_restart(client, tmp_path: Path):
    """KAN-15: Task data must not live only in memory; it must survive a restart.

    Creates several tasks through the API, simulates a process restart by
    discarding all in-process state (a fresh ``TestClient`` pointed at the
    same storage file), and asserts that every task — including the
    auto-increment id counter — is still present and correct.
    """
    first = _create_task(client, "Buy oat milk")
    second = _create_task(client, "Walk the dog", done=True)

    db_file = tmp_path / "tasks.db"
    assert db_file.exists()

    # Simulate a process restart: create a brand-new TestClient.  Because
    # the storage module opens a fresh database connection on every call (no
    # in-memory cache), the fresh client sees exactly what was committed to
    # the SQLite file — nothing is carried over from the previous "process".
    with TestClient(app) as restarted_client:
        # All previously created tasks are still present, in order.
        list_response = restarted_client.get("/tasks")
        assert list_response.status_code == 200
        assert list_response.json() == [first, second]

        # Each task is retrievable by id with all fields intact.
        for expected in (first, second):
            detail_response = restarted_client.get(f"/tasks/{expected['id']}")
            assert detail_response.status_code == 200
            assert detail_response.json() == expected

        # The auto-increment counter persisted: a new task gets the sequential
        # id rather than colliding with the pre-restart tasks.
        third = _create_task(restarted_client, "Created after restart")
        assert third["id"] == max(first["id"], second["id"]) + 1

    # The SQLite file is the authoritative source of truth: it contains every
    # task (including the one created post-restart) and the next id will keep
    # increasing.
    import sqlite3

    conn = sqlite3.connect(str(db_file))
    try:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
        next_id = conn.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = 'tasks'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert [row[0] for row in rows] == [first["id"], second["id"], third["id"]]
    assert next_id == third["id"]