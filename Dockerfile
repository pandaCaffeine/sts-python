# building layer
FROM python:3.13.1-alpine AS builder
LABEL org.opencontainers.image.authors="adream74@gmail.com"

RUN pip install poetry==2.1.0

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock /app/
RUN touch README.md && poetry install --only main --no-root && rm -rf $POETRY_CACHE_DIR

# runtime layer
FROM python:3.13.1-alpine AS runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN apk upgrade --no-cache && apk --no-cache add curl

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY src/sts ./sts

ENTRYPOINT ["python", "-m", "sts"]