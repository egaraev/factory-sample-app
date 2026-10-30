# Runtime-only image for the FastAPI task-list service.
#
# Installs just enough to run (fastapi + uvicorn via requirements.txt — no
# dev/test deps), serves on a fixed port 8000, and keeps the SQLite task
# database in a mounted /data volume so persistence works without any app code
# changes.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime deps only — requirements-dev.txt (pytest, httpx) is deliberately not
# installed and is also excluded from the build context by .dockerignore.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Dedicated non-root runtime user. /data is created ahead of time and owned by
# that user, so an empty named volume mounted at /data inherits writable
# permissions; a host directory must be writable by uid 1000.
RUN groupadd -g 1000 app \
    && useradd --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data \
    && chown -R app:app /data

USER app

# Fixed, documented storage location. Overridable at runtime with
# `docker run -e DB_PATH=...` pointing at any (mounted) path.
ENV DB_PATH=/data/tasks.db

VOLUME ["/data"]
EXPOSE 8000

# Production ASGI server — no --reload, container entrypoint is the service.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]