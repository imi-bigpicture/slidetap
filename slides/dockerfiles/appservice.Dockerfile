# build stage
FROM python:3.8-slim AS build

LABEL maintainer="erik.o.gabrielsson@sectra.com"

# Uncomment if openslide is needed
# RUN apt-get update && apt-get install -y \
#   libopenslide0 \
#   gcc \
#   && rm -rf /var/lib/apt/lists/*


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

EXPOSE ${SLIDES_APIPORT}

CMD gunicorn \
  --bind 0.0.0.0:${SLIDES_APIPORT} \
  --worker-tmp-dir /dev/shm \
  --log-file - \
  "${SLIDES_APP_CREATOR}"

