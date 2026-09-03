# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm AS base
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

FROM base AS development

COPY pyproject.toml uv.lock .python-version ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY ingestion/pyproject.toml ingestion/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package intertext-backend --no-install-workspace

COPY backend/ backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package intertext-backend
RUN useradd --create-home --uid 10001 intertext \
    && chown -R intertext:intertext /app/backend

USER intertext
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "alembic --config alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

FROM base AS production-builder

COPY pyproject.toml uv.lock .python-version ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY ingestion/pyproject.toml ingestion/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package intertext-backend --no-install-workspace

COPY backend/ backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package intertext-backend

FROM python:${PYTHON_VERSION}-slim-bookworm AS production

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 intertext
WORKDIR /app
COPY --from=production-builder --chown=intertext:intertext /app/.venv /app/.venv
COPY --from=production-builder --chown=intertext:intertext /app/backend /app/backend

USER intertext
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "alembic --config alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
