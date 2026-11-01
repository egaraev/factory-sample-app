from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import storage
from app.discount import router as discount_router
from app.tasks import router as task_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup hook that prepares persistence before any request is served.

    Eagerly creates the configured database file, its parent directory, and
    the ``tasks`` table so the first request after a fresh deploy does not pay
    lazy-initialization cost — and a misconfigured or unwritable ``DB_PATH``
    fails fast at startup instead of surfacing on the first ``POST /tasks``.
    """
    storage.initialize_db()
    yield


app = FastAPI(title="factory-sample-app", lifespan=lifespan)


@app.get("/hello")
def hello():
    return {"message": "Hello, World!"}


app.include_router(task_router)
app.include_router(discount_router)