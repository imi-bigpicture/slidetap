# build stage
FROM python:3.8-slim AS build

LABEL maintainer="erik.o.gabrielsson@sectra.com"

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  # build-essential \
  # gcc \
  # libopenslide0 \
  libturbojpeg0 \
  && rm -rf /var/lib/apt/lists/*


RUN python -m pip install --no-cache-dir --upgrade pip \
  && python -m pip install gunicorn --no-cache-dir

WORKDIR /app

COPY . .

RUN python -m pip install --no-cache-dir --upgrade pip \
  && python -m pip install --no-cache-dir . \
  && python -m pip cache purge

# Uncomment if openslide is needed
# RUN apt-get -y remove gcc && apt -y autoremove

# production stage
FROM scratch
COPY --from=build / /

EXPOSE ${SLIDETAP_APIPORT}

CMD gunicorn \
  --bind 0.0.0.0:${SLIDETAP_APIPORT} \
  --worker-tmp-dir /dev/shm \
  --log-file - \
  "${SLIDETAP_APP_CREATOR}"

