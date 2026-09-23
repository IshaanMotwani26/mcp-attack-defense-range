# syntax=docker/dockerfile:1

# ---- stage 1: build the React dashboard ----------------------------------
FROM node:20-slim AS frontend
WORKDIR /app/dashboard
# install deps first (layer-cached unless package files change)
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
# then build
COPY dashboard/ ./
RUN npm run build          # -> /app/dashboard/dist

# ---- stage 2: python backend ---------------------------------------------
# Match the project's pinned interpreter (.python-version = 3.14).
FROM python:3.14-slim
WORKDIR /app

# uv for dependency install from the committed lockfile
RUN pip install --no-cache-dir uv

# install ONLY dependencies (not the project itself — it has no build backend;
# we put the source on PYTHONPATH instead). Lockfile-exact, reproducible.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# application source
COPY api/ ./api/
COPY scanner/ ./scanner/
COPY servers/ ./servers/
COPY proxy/ ./proxy/
COPY agent/ ./agent/

# the compiled dashboard from stage 1
COPY --from=frontend /app/dashboard/dist ./dashboard/dist

# /app on the path so `api.server` imports regardless of how it's launched;
# run everything through the uv venv.
ENV PYTHONPATH=/app
ENV PORT=8000
EXPOSE 8000

# Render provides $PORT; bind 0.0.0.0 so the container is reachable.
CMD ["sh", "-c", "uv run uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
