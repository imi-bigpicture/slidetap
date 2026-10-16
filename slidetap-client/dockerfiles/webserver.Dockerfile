# Base images are pinned to exact tags; Dependabot's docker ecosystem bumps
# them.

# build stage
FROM node:24.22.0-alpine3.24 AS build-stage

LABEL maintainer="erik.o.gabrielsson@sectra.com"
WORKDIR /app

# Dependencies first, so source edits don't invalidate the install layer.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build

# production stage
# Runs nginx as the unprivileged `nginx` user (uid 101), so the listen port must
# be above 1024 and the mounted certificate and key readable by that user.
FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24 AS production-stage
COPY --from=build-stage /app/dist /app

COPY ./dockerfiles/nginx.conf /etc/nginx/nginx.conf
COPY ./dockerfiles/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY ./dockerfiles/app.conf.template /etc/nginx/templates/app.conf.template

EXPOSE ${SLIDETAP_PORT}

CMD ["nginx", "-g", "daemon off;"]
