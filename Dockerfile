# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Run backend
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --chown=app:app backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev

COPY --chown=app:app backend/ ./
COPY --chown=app:app --from=frontend-build /app/frontend/out ./static
RUN mkdir -p /app/data && chown -R app:app /app

USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/health || exit 1
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
