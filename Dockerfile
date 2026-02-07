# ── Build stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./

# Install dependencies into an in-project .venv (no dev deps)
RUN poetry config virtualenvs.in-project true \
    && poetry install --only main --no-root --no-interaction

# ── Runtime stage ────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy the pre-built virtual environment
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY app/ app/
COPY openapi.yaml main.py ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "main.py"]
