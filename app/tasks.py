"""FastAPI router for task CRUD endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from app import storage
from app.schemas import Task, TaskCreate, TaskUpdate

router = APIRouter(tags=["tasks"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=Task)
def create_task(payload: TaskCreate):
    task = storage.create_task(title=payload.title, done=payload.done)
    return Task(**task)


@router.get("/tasks", response_model=List[Task])
def list_tasks():
    tasks = storage.list_tasks()
    return [Task(**task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = storage.get_task(task_id)
    if task is None:
        raise _not_found()
    return Task(**task)


@router.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    updated = storage.update_task(task_id, title=payload.title, done=payload.done)
    if updated is None:
        raise _not_found()
    return Task(**updated)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    deleted = storage.delete_task(task_id)
    if not deleted:
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)