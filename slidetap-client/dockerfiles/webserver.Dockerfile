# build stage
FROM node:lts-alpine AS build-stage

LABEL maintainer="erik.o.gabrielsson@sectra.com"
WORKDIR /app
COPY . .

RUN npm install && npm run build

# production stage
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /app

COPY ./dockerfiles/nginx.conf /etc/nginx/nginx.conf
COPY ./dockerfiles/app.conf.template /etc/nginx/templates/app.conf.template

EXPOSE ${SLIDETAP_PORT}

CMD ["nginx", "-g", "daemon off;"]
