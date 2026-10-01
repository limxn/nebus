# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.5.11 AS uv

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# --- dependencies stage ---
FROM base AS deps
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# --- runtime stage ---
FROM base AS runtime
COPY --from=uv /uv /uvx /bin/
COPY --from=deps /app/.venv /app/.venv
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
