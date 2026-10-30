# factory-sample-app

Minimal FastAPI service with a single `/hello` endpoint returning a static
JSON greeting. This is a proof-of-pipeline scaffold; persistence, frontend,
and additional endpoints are deferred to follow-up epics.

## Prerequisites

- Python 3.9+ (with `pip`)
- `curl` for manual verification (preinstalled on most systems)

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Start the service locally with one command:

```bash
uvicorn app.main:app --reload
```

The server listens on `http://127.0.0.1:8000` and reloads automatically on
code changes. Interactive API docs are served at
`http://127.0.0.1:8000/docs`. Stop the server with `Ctrl+C`.

## Verify manually

With the server running, request the greeting endpoint in a second terminal:

```bash
curl http://127.0.0.1:8000/hello
```

Expected response:

```json
{"message": "Hello, World!"}
```

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
README.md
```