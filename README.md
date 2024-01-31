# _SlideTap_

Webapp for exporting pathology data using configurable sources for images and metadata.

This application has not been tested for clinical use and is not CE-marked.
It may therefore be used for research purposes only and comes without any guarantees.

## Overview

_SlideTap_ is a webapp for creating research dataset of digital pathology data. It is designed to be able to interact with different sources of data, e.g. PACS for images and LIS for metadata, to enable curation of the data, and to output the data in desired formats.

## Components

_SlideTap_ is divided into a back-end (in subfolder `slidetap`) and a front-end (in subfolder `slidetap-client`). Refere to the `README.md` in those folders for more specific information.

## Deployment

The project is designed to be deployed using Docker or simiar technology.

### Deployment requirements

- An site-specific implementation of the components outlined
- Docker (see [SETUP_DOCKER.md](SETUP_DOCKER.md))
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
- SLIDETAP_KEEPALIVE: Interval in seconds for client to send keepalive.
- SLIDETAP_ENFORCE_HTTPS: If to only allow HTTPS connections.
- SLIDETAP_APP_CREATOR: Path to .py-file with create_app()-method.

```bash
SLIDETAP_SERVERNAME=server_hostname
SLIDETAP_PORT=3000
SLIDETAP_SSL_CERTIFICATE_FOLDER=path_to_certs
SLIDETAP_SSL_CERTIFICATE=cert.pem
SLIDETAP_SSL_CERTIFICATE_KEY=privkey.pem
SLIDETAP_APIPORT=8000
SLIDETAP_STORAGE=path_to_storage
SLIDETAP_KEEPALIVE=1800
SLIDETAP_ENFORCE_HTTPS=true
SLIDETAP_APP_CREATOR=path_to_create_app_file
```

Include other environment variables needed for your implementations.

### Build and run containers

```console
sudo docker-compose up
```
