# _SlideTap_

Webapp for exporting pathology data using configurable sources for images and metadata.

This application has not been tested for clinical use and is not CE-marked.
It may therefore be used for research purposes only and comes without any guarantees.

## Overview

_SlideTap_ is a webapp for creating research dataset of digital pathology data. It is designed to be able to interact with different sources of data, e.g. PACS for images and LIS for metadata, to enable curation of the data, and to output the data in desired formats.

## Components

_SlideTap_ is divided into a backend (in subfolder `slidetap-app`) and a frontend (in subfolder `slidetap-client`). Refere to the `README.md` in those folders for more specific information.

## Deployment

The project is designed to be deployed using Docker or similar technology. The
`example` folder holds a complete `docker-compose.yml` to start from, and
[the example documentation](https://imi-bigpicture.github.io/slidetap/example)
walks through running it end to end.

### Deployment requirements

- A site-specific implementation of the components outlined above.
- Docker and Docker Compose (see <https://docs.docker.com/engine/install/>).
- A PostgreSQL database, which also serves as the background task queue.
- SSL cert for webserver.

### Setup environment

Configure the application environment by creating an .env-file:

- SLIDETAP_SERVERNAME: Domain name to webserver.
- SLIDETAP_PORT: Port for webserver.
- SLIDETAP_SSL_CERTIFICATE_FOLDER: Path to folder with certificate (cert.pem) and private key (privkey.pem) for SSL.
- SLIDETAP_SSL_CERTIFICATE: Name of certificate file.
- SLIDETAP_SSL_CERTIFICATE_KEY: Name of private key file.
- SLIDETAP_APIPORT: The port for the back-end server.
- SLIDETAP_STORAGE: Folder to store data.
- SLIDETAP_DBURI: URI of the database, which also holds the task queue.
- SLIDETAP_SECRET_KEY: Secret key used to sign tokens.
- SLIDETAP_CONFIG_FILE: Path to the config.yaml read by the Python applications.
- SLIDETAP_WEB_APP: Uvicorn target for the web application, as `package.module:attribute`.
- SLIDETAP_TASK_APP: Dotted name of the package whose `task_app.py` exposes `task_app`.

```bash
SLIDETAP_SERVERNAME=server_hostname
SLIDETAP_PORT=3000
SLIDETAP_SSL_CERTIFICATE_FOLDER=path_to_certs
SLIDETAP_SSL_CERTIFICATE=cert.pem
SLIDETAP_SSL_CERTIFICATE_KEY=privkey.pem
SLIDETAP_APIPORT=8000
SLIDETAP_STORAGE=path_to_storage
SLIDETAP_DBURI=postgresql://user:password@dbservice:5432/slidetap
SLIDETAP_SECRET_KEY=change_me
SLIDETAP_CONFIG_FILE=/storage/config.yaml
SLIDETAP_WEB_APP=your_package.web_app:app
SLIDETAP_TASK_APP=your_package
```

Include other environment variables needed for your implementations.

Settings that are not site secrets live in `config.yaml` rather than in the
environment, among them `keep_alive`, `log_level`, `dicomization`, and the
`task` section that tunes the workers. See
[the back-end README](slidetap-app/README.md) for the full set.

### Build and run containers

Migrations are an explicit deploy step, and both the web application and the
workers refuse to start against a database that has not had them applied. The
compose stack in `example` wires this up as a one-shot service that the other
services wait for.

```console
cd example
sudo docker compose build
sudo docker compose up
```

## Acknowledgement

*SlideTap*: Copyright 2024 Sectra AB, licensed under Apache 2.0.

This project is part of a project that has received funding from the Innovative Medicines Initiative 2 Joint Undertaking under grant agreement No 945358. This Joint Undertaking receives support from the European Union’s Horizon 2020 research and innovation programme and EFPIA. IMI website: <www.imi.europa.eu>
