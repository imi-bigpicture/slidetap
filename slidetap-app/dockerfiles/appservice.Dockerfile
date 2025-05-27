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
RUN python -m pip install gunicorn --no-cache-dir

EXPOSE ${SLIDETAP_APIPORT}
RUN useradd -ms /bin/bash flask
RUN chown -R flask:flask /app
USER flask

CMD gunicorn \
  --bind 0.0.0.0:${SLIDETAP_APIPORT} \
  --worker-tmp-dir /dev/shm \
  --log-file - \
  --log-level 'debug' \
  "${SLIDETAP_WEB_APP_CREATOR}"

