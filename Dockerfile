# Two stages: "build" installs the packages with uv, "runtime" only copies the
# finished virtual environment, so the image has no uv, compiler or cache in it.

FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer is reused until pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Then the project itself.
COPY README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN uv sync --locked --no-dev --no-editable


FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Run as a normal user, not root.
RUN useradd --create-home --uid 1000 app

COPY --from=build --chown=app:app /app/.venv ./.venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app docker/entrypoint.sh ./entrypoint.sh

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

# No secrets here: DATABASE_URL, JWT_SECRET_KEY etc. come from the environment
# (docker compose passes them from .env).
ENTRYPOINT ["sh", "./entrypoint.sh"]
CMD ["uvicorn", "loan_application.main:app", "--host", "0.0.0.0", "--port", "8000"]
