"""Direct unit tests for the JSON file-backed task storage module."""

from pathlib import Path

import pytest

import app.storage as storage


@pytest.fixture(autouse=True)
def isolated_storage_file(tmp_path, monkeypatch):
    """Point storage at a temporary file and restore it after each test."""
    original = storage.DATA_FILE
    storage.set_data_file(tmp_path / "tasks.json")
    yield
    storage.set_data_file(original)


def test_create_task_persists_and_reloads():
    task = storage.create_task("Buy milk")

    assert task["id"] == 1
    assert task["title"] == "Buy milk"
    assert task["done"] is False

    stored = storage.get_task(1)
    assert stored == task


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


def test_update_task_can_change_title_and_done_status():
    task = storage.create_task("Original title")

    updated_title = storage.update_task(task["id"], title="New title")
    assert updated_title["title"] == "New title"
    assert updated_title["done"] is False

    updated_done = storage.update_task(task["id"], done=True)
    assert updated_done["title"] == "New title"
    assert updated_done["done"] is True


def test_update_task_returns_none_for_missing_task():
    assert storage.update_task(999, title="Missing", done=True) is None


def test_delete_task_removes_task_and_persists_change():
    task = storage.create_task("Delete me")

    assert storage.delete_task(task["id"]) is True
    assert storage.get_task(task["id"]) is None
    assert storage.list_tasks() == []


def test_delete_task_returns_false_for_missing_task():
    assert storage.delete_task(999) is False


def test_storage_file_is_initialized_and_visible_on_disk(tmp_path: Path):
    data_file = tmp_path / "nested" / "tasks.json"
    task = storage.create_task("Persisted", file_path=data_file)

    assert data_file.exists()
    on_disk = data_file.read_text(encoding="utf-8")

    assert f'"id": {task["id"]}' in on_disk
    assert '"title": "Persisted"' in on_disk


def test_storage_can_reload_data_after_restart_simulation(tmp_path: Path):
    data_file = tmp_path / "tasks.json"
    task = storage.create_task("Across restart", file_path=data_file)

    # Simulate a process restart by re-reading from disk through fresh calls.
    assert storage.get_task(task["id"], file_path=data_file) == task
    next_id_before_restart = task["id"]

    after_restart = storage.create_task("After restart", file_path=data_file)
    assert after_restart["id"] == next_id_before_restart + 1
