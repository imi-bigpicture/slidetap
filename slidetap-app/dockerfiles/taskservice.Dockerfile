# Base images are pinned to exact tags; Dependabot's docker ecosystem bumps
# them. Build and production use the same Python image, so the interpreter the
# venv links to exists in production.
FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

# build stage
FROM python:3.14.7-slim-trixie AS build

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_PYTHON_DOWNLOADS=0

WORKDIR /app/slidetap

# Dependencies first, from the workspace manifests and lockfile only, so source
# edits don't invalidate this layer. Installs from uv.lock rather than resolving
# against PyPI, so the image gets the versions the lockfile pins and the 14-day
# `exclude-newer` window applies.
COPY pyproject.toml uv.lock ./
COPY apps/example/pyproject.toml apps/example/
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --package slidetap-example --no-install-workspace

# Then the source, and the workspace packages themselves.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --package slidetap-example

# production stage
FROM python:3.14.7-slim-trixie AS production

LABEL maintainer="erik.o.gabrielsson@sectra.com"

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  # build-essential \
  # gcc \
  # libopenslide0 \
  libturbojpeg0 \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash slidetap

# Owned by root, so the app user can't modify the installed code.
COPY --from=build /app /app
ENV PATH="/app/slidetap/.venv/bin:$PATH"

WORKDIR /app
USER slidetap

CMD ["slidetap-task-worker"]
