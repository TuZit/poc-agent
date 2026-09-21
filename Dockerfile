# syntax=docker/dockerfile:1

# Agent Kit POC image.
#
#   docker build -t agent-kit-poc .
#   docker run --rm agent-kit-poc agent-kit --help
#   docker run --rm -v "$PWD:/work" -e OPENAI_API_KEY agent-kit-poc agent-kit doctor
#
# No secrets are baked into the image: OPENAI_API_KEY is injected at run time.

FROM python:3.12-slim

# uv resolves the locked dependency set inside the image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Project sources — including the assets force-included into the wheel
# (skills, templates, samples, integrations).
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY skills ./skills
COPY templates ./templates
COPY samples ./samples
COPY integrations ./integrations

# Install the runtime with the optional OpenAI extra from the lock file.
RUN uv sync --frozen --no-dev --all-extras

# Run as a non-root user against a mountable working directory.
RUN useradd --create-home --uid 10001 agent \
    && mkdir -p /work \
    && chown -R agent:agent /work /app
USER agent

WORKDIR /work
CMD ["agent-kit", "--help"]
