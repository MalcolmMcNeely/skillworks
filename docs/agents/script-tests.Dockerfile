# The script tests run here because on Windows every git and bash process they start is slow to start.
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /usr/local/bin/
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Fetched once at build, so a run does not download pytest into every fresh container.
RUN uv run --no-project --with pytest --with pytest-xdist --with filelock python -c ""

WORKDIR /repo
