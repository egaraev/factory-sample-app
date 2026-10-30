# factory-sample-app

Minimal FastAPI service with a single `/hello` endpoint returning a static
JSON greeting. This is a proof-of-pipeline scaffold; persistence, frontend,
and additional endpoints are deferred to follow-up epics.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/hello` (interactive docs at `/docs`).

## Test

```bash
pytest
```

## Project structure

```
app/
  __init__.py
  main.py          # FastAPI app + /hello endpoint
tests/
  test_hello.py    # endpoint test
requirements.txt
```