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

RUN python -m pip install -e /app/slidetap[postresql]  --no-cache-dir

# Uncomment if openslide is needed
# RUN apt-get -y remove gcc && apt -y autoremove

# production stage
RUN useradd -ms /bin/bash celery
RUN chown -R celery:celery /app
USER celery

CMD celery -A ${SLIDETAP_TASK_APP} worker --loglevel=debug
