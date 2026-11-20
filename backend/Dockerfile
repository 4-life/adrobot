FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/

WORKDIR /app
# uv's download cache is a BuildKit cache mount (another filesystem): copy, don't hardlink.
ENV UV_LINK_MODE=copy

# --locked installs exactly uv.lock and fails the build if it's out of date with
# pyproject.toml. Dependencies only: the services run `python -m ...` from /app.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations

ENV PATH="/app/.venv/bin:$PATH"

# The services run as this user, not root - they only read /app.
RUN useradd --system --uid 10001 --no-create-home app

FROM base AS runner
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
