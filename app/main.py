"""Minimal FastAPI application.

Scaffold entry point for the sample-app API (KAN-4/KAN-5). Provides a single
greeting endpoint to prove the run/test/CI loop end-to-end; real features are
deferred to follow-up epics.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="factory-sample-app")


class Greeting(BaseModel):
    message: str


@app.get("/hello", response_model=Greeting)
def hello() -> Greeting:
    """Return a static JSON greeting."""
    return Greeting(message="Hello, World!")