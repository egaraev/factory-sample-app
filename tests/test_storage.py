"""Direct unit tests for the SQLite-backed task storage module."""

from pathlib import Path
from typing import Any, Dict

import pytest

import app.storage as storage


@pytest.fixture(autouse=True)
def isolated_storage_file(tmp_path):
    """Point storage at a per-test temporary SQLite database file.

    Every test gets its own ``tmp_path``-based ``.db`` file through
    :func:`app.storage.set_db_path`, and the previous module-level path is
    restored afterwards (in a ``finally``) so no shared or real database file
    is ever touched, even if the test raises.
    """
    original = storage.DB_PATH
    storage.set_db_path(tmp_path / "tasks.db")
    try:
        yield
    finally:
        storage.set_db_path(original)


def _tables(db_path: Path) -> set:
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def _task_rows(db_path: Path):
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    finally:
        conn.close()


def test_create_task_persists_and_reloads(tmp_path: Path):
    task = storage.create_task("Buy milk")
    db_file = tmp_path / "tasks.db"

    assert task["id"] == 1
    assert task["title"] == "Buy milk"
    assert task["done"] is False
    assert isinstance(task["id"], int)
    assert isinstance(task["done"], bool)

    stored = storage.get_task(1)
    assert stored == task

    assert db_file.exists()
    assert "tasks" in _tables(db_file)
    assert _task_rows(db_file) == [(1, "Buy milk", 0)]


def test_create_task_defaults_done_to_false_but_allows_true():
    not_done = storage.create_task("Write docs")
    done = storage.create_task("Ship release", done=True)

    assert not_done["done"] is False
    assert done["done"] is True


def test_list_tasks_returns_all_tasks_in_id_order():
    first = storage.create_task("First")
    second = storage.create_task("Second")
    third = storage.create_task("Third")

    tasks = storage.list_tasks()
    assert [task["id"] for task in tasks] == [first["id"], second["id"], third["id"]]


def test_get_task_returns_none_for_missing_task():
    storage.create_task("Existing task")
    assert storage.get_task(999) is None


def test_update_task_can_change_title_and_done_status(tmp_path: Path):
    task = storage.create_task("Original title")

    updated_title = storage.update_task(task["id"], title="New title")
    assert updated_title["title"] == "New title"
    assert updated_title["done"] is False

    updated_done = storage.update_task(task["id"], done=True)
    assert updated_done["title"] == "New title"
    assert updated_done["done"] is True

    db_file = tmp_path / "tasks.db"
    assert _task_rows(db_file) == [(task["id"], "New title", 1)]


def test_update_task_returns_none_for_missing_task():
    assert storage.update_task(999, title="Missing", done=True) is None


def test_delete_task_removes_task_and_persists_change(tmp_path: Path):
    task = storage.create_task("Delete me")

    assert storage.delete_task(task["id"]) is True
    assert storage.get_task(task["id"]) is None
    assert storage.list_tasks() == []

    db_file = tmp_path / "tasks.db"
    assert _task_rows(db_file) == []


def test_delete_task_returns_false_for_missing_task():
    assert storage.delete_task(999) is False


def test_db_file_is_initialized_and_visible_on_disk(tmp_path: Path):
    db_file = tmp_path / "nested" / "tasks.db"
    task: Dict[str, Any] = storage.create_task("Persisted", db_path=db_file)

    assert db_file.exists()
    assert "tasks" in _tables(db_file)

    import sqlite3

    conn = sqlite3.connect(str(db_file))
    try:
        stored = conn.execute("SELECT id, title, done FROM tasks").fetchall()
        next_id = conn.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = 'tasks'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert stored == [(task["id"], "Persisted", 0)]
    assert next_id == task["id"]


def test_storage_can_reload_data_after_restart_simulation(tmp_path: Path):
    db_file = tmp_path / "tasks.db"
    task = storage.create_task("Across restart", db_path=db_file)

    # Simulate a process restart by re-reading through fresh connections.
    assert storage.get_task(task["id"], db_path=db_file) == task
    next_id_before_restart = task["id"]

    after_restart = storage.create_task("After restart", db_path=db_file)
    assert after_restart["id"] == next_id_before_restart + 1

    import sqlite3

    conn = sqlite3.connect(str(db_file))
    try:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
        next_id = conn.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = 'tasks'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert rows == [
        (task["id"], "Across restart", 0),
        (after_restart["id"], "After restart", 0),
    ]
    assert next_id == after_restart["id"]


def test_ids_are_never_reused_after_deletion():
    # KAN-24: AUTOINCREMENT must keep handing out fresh ids even after all
    # current rows are gone.
    first = storage.create_task("First")
    second = storage.create_task("Second")
    assert storage.delete_task(first["id"]) is True
    assert storage.delete_task(second["id"]) is True

    third = storage.create_task("Third")
    assert third["id"] == second["id"] + 1


def test_db_path_overrides_module_default(tmp_path: Path):
    db_file = tmp_path / "override.db"
    task = storage.create_task("Via override", db_path=db_file)

    assert storage.get_task(task["id"], db_path=db_file) == task
    # The module-level default database must not have picked up the row.
    assert storage.list_tasks() == []


def test_module_default_path_is_used_when_no_db_path_given(tmp_path: Path):
    default_db = tmp_path / "default.db"
    storage.set_db_path(default_db)

    task = storage.create_task("Default path")
    stored = storage.get_task(task["id"])
    assert stored == task
    assert default_db.exists()