# build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build

ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_PYTHON_DOWNLOADS=0

WORKDIR /app/slidetap

COPY . .

# Installs from uv.lock rather than resolving against PyPI, so the image gets
# the versions the lockfile pins and the 14-day `exclude-newer` window applies.
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --package slidetap-example --extra web

# production stage
FROM python:3.12-slim AS production

LABEL maintainer="erik.o.gabrielsson@sectra.com"

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  # build-essential \
  # gcc \
  # libopenslide0 \
  libturbojpeg0 \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash fastapi

COPY --from=build --chown=fastapi:fastapi /app /app
ENV PATH="/app/slidetap/.venv/bin:$PATH"

WORKDIR /app
USER fastapi

EXPOSE ${SLIDETAP_APIPORT}

CMD uvicorn \
  --host 0.0.0.0 \
  --port ${SLIDETAP_APIPORT} \
  --log-level debug \
  --proxy-headers \
  "${SLIDETAP_WEB_APP}"
