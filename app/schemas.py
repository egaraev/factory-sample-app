"""Pydantic request/response schemas for the task endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    """Payload for creating a new task."""

    title: str
    done: bool = False


class TaskUpdate(BaseModel):
    """Payload for partially updating a task; fields left as ``None`` are unchanged."""

    title: Optional[str] = None
    done: Optional[bool] = None


class Task(BaseModel):
    """A task as returned by the API."""

    id: int
    title: str
    done: bool