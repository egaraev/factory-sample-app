"""JSON-file-backed persistence for tasks.

The storage layer is intentionally small and dependency-free: it stores the
task list and an incrementing id counter in a JSON file, guarded by a lock so
concurrent requests cannot corrupt the file. The backing path can be changed
through :data:`DATA_FILE`, :func:`set_data_file`, or the optional ``file_path``
argument accepted by each public function (useful in tests).
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Default location of the persisted JSON file. Tests should redirect this to a
# temporary path rather than touching real data.
DATA_FILE: Union[str, Path] = os.environ.get("TASKS_DATA_FILE", "data/tasks.json")

_lock = threading.Lock()


def set_data_file(path: Union[str, Path]) -> None:
    """Set the JSON file used by subsequent storage calls."""
    global DATA_FILE
    with _lock:
        DATA_FILE = path


def _resolve_path(file_path: Optional[Union[str, Path]]) -> Path:
    return Path(file_path if file_path is not None else DATA_FILE)


def _empty_store() -> Dict[str, Any]:
    return {"next_id": 1, "tasks": []}


def _normalize(data: Any) -> Dict[str, Any]:
    if data is None or data == {}:
        return _empty_store()

    if not isinstance(data, dict):
        raise ValueError("Task storage file must contain a JSON object")

    normalized = {
        "next_id": int(data.get("next_id", 1) or 1),
        "tasks": [dict(task) for task in data.get("tasks", [])],
    }

    if normalized["next_id"] < 1:
        normalized["next_id"] = 1

    max_task_id = 0
    for task in normalized["tasks"]:
        try:
            task_id = int(task.get("id"))
        except (TypeError, ValueError):
            continue
        if task_id > max_task_id:
            max_task_id = task_id
        if "done" not in task:
            task["done"] = False

    normalized["next_id"] = max(normalized["next_id"], max_task_id + 1)
    return normalized


def _write_store(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def _load_store(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return _empty_store()

    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    return _normalize(data)


def list_tasks(file_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """Return all tasks ordered by id."""
    with _lock:
        path = _resolve_path(file_path)
        data = _load_store(path)
        return sorted((dict(task) for task in data["tasks"]), key=lambda task: int(task.get("id", 0)))


def get_task(task_id: Any, file_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Return a single task by id, or ``None`` when it does not exist."""
    with _lock:
        path = _resolve_path(file_path)
        data = _load_store(path)

    try:
        task_id = int(task_id)
    except (TypeError, ValueError):
        return None

    for task in data["tasks"]:
        if int(task.get("id", -1)) == task_id:
            return dict(task)
    return None


def create_task(
    title: str,
    done: bool = False,
    file_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Create a new task and persist it."""
    with _lock:
        path = _resolve_path(file_path)
        data = _load_store(path)

        task_id = data["next_id"]
        task = {"id": task_id, "title": title, "done": bool(done)}

        data["tasks"].append(task)
        data["next_id"] = task_id + 1
        _write_store(path, data)
        return dict(task)


def update_task(
    task_id: Any,
    title: Optional[str] = None,
    done: Optional[bool] = None,
    file_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Update a task's title and/or done status.

    Returns the updated task, or ``None`` when the task does not exist.
    """
    with _lock:
        path = _resolve_path(file_path)
        data = _load_store(path)

        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return None

        for index, task in enumerate(data["tasks"]):
            if int(task.get("id", -1)) != task_id:
                continue

            if title is not None:
                task["title"] = title
            if done is not None:
                task["done"] = bool(done)

            data["tasks"][index] = dict(task)
            _write_store(path, data)
            return dict(task)

        return None


def delete_task(task_id: Any, file_path: Optional[Union[str, Path]] = None) -> bool:
    """Delete a task by id. Returns ``True`` when a task was removed."""
    with _lock:
        path = _resolve_path(file_path)
        data = _load_store(path)

        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return False

        remaining = [task for task in data["tasks"] if int(task.get("id", -1)) != task_id]
        if len(remaining) == len(data["tasks"]):
            return False

        data["tasks"] = remaining
        _write_store(path, data)
        return True
