# syntax=docker/dockerfile:1
# uv-based image (ships uv + Python 3.12) — deterministic builds for Coolify.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    # SQLite lives on a mounted volume so editions survive redeploys.
    DATABASE_URL=sqlite:////data/ai_news.db

# 1) Install dependencies first (cached unless the lockfile changes).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2) Copy the app.
COPY . .

# Run as a non-root user; /data must stay writable (SQLite volume).
RUN useradd --system --create-home --uid 1000 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

# Coolify can override the port via $PORT; defaults to 8000.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/api/health')" || exit 1

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
