FROM python:3.14-slim-trixie

ENV PATH=/app/.venv/bin:${PATH} \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 101 é o user do nginx:
RUN groupadd --system --gid 101 nonroot \
    && useradd --system --create-home --gid 101 --uid 101 nonroot \
    && mkdir /app \
    && chown 101:101 /app \
    && mkdir /run/mge \
    && chown 101:101 /run/mge

USER nonroot

WORKDIR /app

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/home/nonroot/.cache/uv,uid=101,gid=101 \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/home/nonroot/.cache/uv,uid=101,gid=101 \
    uv sync --locked

CMD ["python", "-m", "back"]
