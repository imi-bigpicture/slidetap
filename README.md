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
- SLIDETAP_TASK_APP: Dotted name of the package whose `task_app.py` exposes `task_app` and whose `container.py` exposes `create_container()`.

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

After the migrations, and before the applications start, the stored mappers are
set up by `slidetap-mappers set-up`, which the compose stack runs in the same
one-shot service.

## Converting projects to a new schema

An application can create new projects on a new root schema, such as a new
version of a metadata standard, while the projects created before stay on the
root schema they were created with. Those projects can be viewed but not
changed. Where the application also has a migration from their root schema to
that of new projects, a project can be converted to it in the **Convert** tab of
the project.

### Back up the database first

Back up the database before deploying a version of the application with a new
root schema, and again before converting projects. Completing a conversion
rewrites the project on the new root schema, and cannot be undone: the only way
back is restoring the database. With the database of the compose stack:

```console
sudo docker compose exec -T dbservice pg_dump -U user -Fc slidetap > slidetap.dump
```

To restore it, with the applications stopped, which replaces the database with
the one in the dump:

```console
sudo docker compose exec -T dbservice pg_restore -U user -d postgres --clean --create < slidetap.dump
```

The dump holds the database, not the files in the storage folder. A conversion
does not change those files.

### When a project can be converted

The **Convert** tab offers the conversion where the root schema of the project
has a migration to the root schema of new projects, and says why not where it
cannot be converted now. A project cannot be converted when:

- it has been exported, as what was exported stays on the schema it was
  exported with;
- its images are stored, or locked to be stored;
- a batch of it is being searched or processed.

### Converting a project

1. **Convert**: the conversion is planned by the task worker. Every attribute
   and item of the project is converted to the new root schema, and what could
   not be converted by itself is kept to be resolved.
2. **Resolve**: the attributes that could not be converted are listed by item,
   each with what could be converted of it. An attribute the new schema does not
   have is accepted as dropped with **Accept**. An attribute that lost a value
   with no counterpart in the new schema is given a value with **Set value**, or
   left empty with **Leave empty**.
3. **Submit**, once everything is resolved: the conversion is completed by the
   task worker. The project is moved to the new root schema with what was
   resolved, gets back the status it had, and is validated again.

**Revert** gives up the conversion, and leaves the project as it was, at any
point until it is submitted, and also after a failed planning or completion. A
conversion that fails leaves the project as it was before it, with why in the
**Convert** tab.

The task worker must be running for planning and completing. Their tasks are
quick, and show in the task list under the status **succeeded**.

### While a project is converted

From **Convert** until the conversion is completed or reverted, the project has
the status **Converting** and is locked: nothing in it can be edited, its
batches cannot be searched or have their images processed, and it cannot be
exported or deleted. It can still be viewed. Mappers are not locked, as they
are not of a project.

## Acknowledgement

*SlideTap*: Copyright 2024 Sectra AB, licensed under Apache 2.0.

This project is part of a project that has received funding from the Innovative Medicines Initiative 2 Joint Undertaking under grant agreement No 945358. This Joint Undertaking receives support from the European Union’s Horizon 2020 research and innovation programme and EFPIA. IMI website: <www.imi.europa.eu>
