# factory-sample-app

Minimal FastAPI service with a `/hello` endpoint and a small JSON-backed task
list API. This is a proof-of-pipeline scaffold; persistence, frontend, and
additional endpoints are deferred to follow-up epics.

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

## Task API

Tasks are stored in `data/tasks.json` by default, so they persist across
service restarts. The file is created automatically on the first write. You
can override the storage location with the `TASKS_DATA_FILE` environment
variable.

### Create a task

`POST /tasks` accepts a title and an optional done flag:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
```

Expected response (`201 Created`):

```json
{"id": 1, "title": "Buy milk", "done": false}
```

To create a task that is already done:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Walk dog", "done": true}'
```

### List all tasks

`GET /tasks` returns all tasks in id order:

```bash
curl http://127.0.0.1:8000/tasks
```

Expected response (`200 OK`):

```json
[
  {"id": 1, "title": "Buy milk", "done": false},
  {"id": 2, "title": "Walk dog", "done": true}
]
```

### Get one task

`GET /tasks/{task_id}` returns a single task or `404 Not Found` when the id
does not exist:

```bash
curl http://127.0.0.1:8000/tasks/1
```

Expected response (`200 OK`):

```json
{"id": 1, "title": "Buy milk", "done": false}
```

Not-found response (`404 Not Found`):

```json
{"detail": "Task not found"}
```

### Update a task

`PUT /tasks/{task_id}` accepts any subset of `title` and `done`. Fields left
out are unchanged. Missing tasks return `404 Not Found`:

```bash
curl -X PUT http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy oat milk"}'

curl -X PUT http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done": true}'
```

Expected response after the first update (`200 OK`):

```json
{"id": 1, "title": "Buy oat milk", "done": false}
```

Expected response after the second update (`200 OK`):

```json
{"id": 1, "title": "Buy oat milk", "done": true}
```

Not-found response (`404 Not Found`):

```json
{"detail": "Task not found"}
```

### Delete a task

`DELETE /tasks/{task_id}` deletes the task and returns `204 No Content` with
no body. Missing tasks return `404 Not Found`:

```bash
curl -X DELETE http://127.0.0.1:8000/tasks/1
```

Success response:

```text
204 No Content
```

Not-found response (`404 Not Found`):

```json
{"detail": "Task not found"}
```

## Test

```bash
pytest
```

## Project structure

```
app/
  __init__.py
  main.py          # FastAPI app + /hello endpoint + task router wiring
  schemas.py       # Pydantic models for task request/response payloads
  storage.py       # JSON-file-backed persistence layer
  tasks.py         # Task CRUD API routes
tests/
  test_hello.py    # endpoint test
  test_schemas.py  # schema tests
  test_storage.py  # persistence layer tests
  test_tasks.py    # task endpoint tests
requirements.txt
README.md
```