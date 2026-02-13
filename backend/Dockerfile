# ============================================================
# Stage 1: Builder — install dependencies with uv (layer-cached)
# ============================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Install deps first (cached unless pyproject.toml/uv.lock change)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Then copy project source and install it
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================================
# Stage 2: Dev — hot-reload with volume mounts
# ============================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm AS dev

WORKDIR /app

# Install system deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl && \
    rm -rf /var/lib/apt/lists/*

# Copy built venv from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

# Install Playwright browser
ENV PATH="/app/.venv/bin:$PATH"
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# ============================================================
# Stage 3: Production — minimal runtime image
# ============================================================
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble AS production

WORKDIR /app

# Copy the uv-built virtual environment and project
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./
COPY --from=builder /app/app ./app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Install Playwright Chromium browser binary
RUN playwright install chromium

# Non-root user for production
RUN useradd --create-home appuser
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
