"""SQLite-backed persistence for tasks.

The storage layer is intentionally small and dependency-free (``sqlite3`` from
the standard library): it stores tasks in a single ``tasks`` table, guarded by
a lock so concurrent requests cannot corrupt the database. The backing file can
be changed through :data:`DB_PATH`, :func:`set_db_path`, or the optional
``db_path`` argument accepted by each public function (useful in tests).

Every call opens a short-lived connection to the configured path, makes sure
the schema exists, performs its operation, commits, and closes — mirroring the
old "load / mutate / write" pattern, so a restarted process always sees
previously committed data. ``AUTOINCREMENT`` guarantees that ids are never
reused after deletion, preserving the old "next id only increases" behavior.

The application's startup hook calls :func:`initialize_db` once at boot so the
database file and schema exist before the first request is served, and a
misconfigured or unwritable ``DB_PATH`` fails fast at startup rather than on
the first write (see KAN-26).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Default location of the SQLite database file (overridable with the
# ``DB_PATH`` environment variable). Tests should redirect this to a temporary
# path rather than touching real data.
DB_PATH: str = os.environ.get("DB_PATH", "data/tasks.db")

_lock = threading.Lock()


def set_db_path(path: Union[str, Path]) -> None:
    """Set the SQLite database path used by subsequent storage calls."""
    global DB_PATH
    with _lock:
        DB_PATH = str(path)


def initialize_db(db_path: Optional[Union[str, Path]] = None) -> str:
    """Eagerly create the database file, its parent directory, and the schema.

    Called from the app's startup hook so a fresh deploy (empty/missing DB
    file) is fully initialized before the first request arrives, and an
    unwritable or otherwise unusable path raises a clear ``RuntimeError`` at
    boot instead of failing on the first write. Returns the resolved path.

    Note that ``:memory:`` databases cannot be "created on disk"; initializing
    one is a no-op by design (its schema is recreated by each connection).
    """
    path = _resolve_path(db_path)
    with _lock:
        try:
            conn = _connect(path)
            conn.close()
        except (OSError, sqlite3.Error) as exc:
            raise RuntimeError(
                f"Could not initialize the task database at {path!r}: {exc}. "
                "Check that the DB_PATH location exists and is writable."
            ) from exc
    return path


def _resolve_path(db_path: Optional[Union[str, Path]]) -> str:
    return str(db_path if db_path is not None else DB_PATH)


def _connect(path: str) -> sqlite3.Connection:
    """Open a connection to *path*, ensuring the schema exists.

    Parent directories are created as needed, except for ``:memory:``, which
    is handled directly by :mod:`sqlite3`.
    """
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    # Default cursor returns plain tuples; switch to Row so results can be
    # indexed by column name (see ``_row_to_task``).
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tasks ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, "
        "done INTEGER NOT NULL DEFAULT 0)"
    )
    conn.commit()
    return conn


def _row_to_task(row: sqlite3.Row) -> Dict[str, Any]:
    # id is already an int from SQLite; normalise for consistency with the old
    # JSON-backed implementation (dicts of id/title/done).
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def list_tasks(
    done: Optional[bool] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return tasks ordered by id, optionally filtered by completion status.

    ``done`` defaults to ``None``, meaning no filtering and every task is
    returned (the historical behavior). Pass ``True`` or ``False`` to return
    only tasks whose stored ``done`` flag matches that status; the match is
    applied with the same ``int(bool(...))`` conversion used when writing the
    column, since SQLite stores the flag as 0/1.
    """
    path = _resolve_path(db_path)
    conn = _connect(path)
    try:
        if done is None:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE done = ? ORDER BY id",
                (int(bool(done)),),
            ).fetchall()
    finally:
        conn.close()

    return [_row_to_task(row) for row in rows]


def get_task(task_id: Any, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Return a single task by id, or ``None`` when it does not exist."""
    try:
        task_id = int(task_id)
    except (TypeError, ValueError):
        return None

    path = _resolve_path(db_path)
    conn = _connect(path)
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return _row_to_task(row)


def create_task(
    title: str,
    done: bool = False,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Create a new task and persist it."""
    with _lock:
        path = _resolve_path(db_path)
        conn = _connect(path)
        try:
            cursor = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                (title, int(bool(done))),
            )
            task_id = int(cursor.lastrowid)
            conn.commit()
        finally:
            conn.close()

    return {"id": task_id, "title": title, "done": bool(done)}


def update_task(
    task_id: Any,
    title: Optional[str] = None,
    done: Optional[bool] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Update a task's title and/or done status.

    Returns the updated task, or ``None`` when the task does not exist.
    """
    with _lock:
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return None

        path = _resolve_path(db_path)
        conn = _connect(path)
        try:
            assignments: List[str] = []
            params: List[Any] = []
            if title is not None:
                assignments.append("title = ?")
                params.append(title)
            if done is not None:
                assignments.append("done = ?")
                params.append(int(bool(done)))

            if assignments:
                conn.execute(
                    f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?",
                    (*params, task_id),
                )

            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            conn.commit()
        finally:
            conn.close()

    if row is None:
        return None
    return _row_to_task(row)


def delete_task(task_id: Any, db_path: Optional[Union[str, Path]] = None) -> bool:
    """Delete a task by id. Returns ``True`` when a task was removed."""
    with _lock:
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return False

        path = _resolve_path(db_path)
        conn = _connect(path)
        try:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        finally:
            conn.close()

    return deleted