# build stage
FROM python:3.12-slim AS build

LABEL maintainer="erik.o.gabrielsson@sectra.com"

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  # build-essential \
  # gcc \
  # libopenslide0 \
  libturbojpeg0 \
  && rm -rf /var/lib/apt/lists/*


RUN python -m pip install --no-cache-dir --upgrade pip

WORKDIR /app

COPY . slidetap

RUN python -m pip install -e /app/slidetap --no-cache-dir
RUN python -m pip install -e /app/slidetap/apps/example[web]  --no-cache-dir

# Uncomment if openslide is needed
# RUN apt-get -y remove gcc && apt -y autoremove


EXPOSE ${SLIDETAP_APIPORT}
RUN useradd -ms /bin/bash fastapi
RUN chown -R fastapi:fastapi /app
USER fastapi

CMD uvicorn \
  --host 0.0.0.0 \
  --port ${SLIDETAP_APIPORT} \
  --log-level debug \
  --proxy-headers \
  "${SLIDETAP_WEB_APP}"

