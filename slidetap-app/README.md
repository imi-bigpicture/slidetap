# SlideTap back-end

The SlideTap back-end is a FastAPI application that serves the REST API, manages database persistence, and runs background image processing via Celery workers. The front-end communicates with it exclusively through the `/api/` prefix.

## Quick start

This section assumes commands are run from the `slidetap-app/` directory.

**1. Install dependencies**

```console
uv sync
```

**2. Configure the application**

Create a `config.yaml` file and a `.env` file (see [Configuration](#configuration) below).

**3. Start the API server**

```console
uv run uvicorn slidetap_example.web_app_factory:app --host 0.0.0.0 --port 5001
```

**4. Start the Celery worker** (separate terminal, same directory)

```console
uv run celery -A slidetap_example.task_app:task_app worker --loglevel=info
```

**5. Start the frontend** (separate terminal, in `slidetap-client/`)

```console
npm install
npm run dev
# Opens at http://localhost:13000
```

> **Tip:** If you are not actively changing the frontend, you can run `npm run build` once in `slidetap-client/` and serve the pre-built files directly from the backend. See the `static_dir` parameter on `SlideTapWebAppFactory.create()` for details.

## Configuration

### Environment variables (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SLIDETAP_CONFIG_FILE` | Yes | — | Path to the `config.yaml` file |
| `SLIDETAP_SECRET_KEY` | Yes | — | Secret key for JWT signing |
| `SLIDETAP_WEBAPP_URL` | Yes | — | URL the frontend is served at (e.g. `http://localhost:13000`) |
| `SLIDETAP_STORAGE` | Yes | — | Path to directory for image and file storage |
| `SLIDETAP_DBURI` | Yes | — | SQLAlchemy database URI (e.g. `sqlite:///path/db.sqlite`) |
| `SLIDETAP_BROKER_URL` | Yes | — | Celery broker URL (e.g. `amqp://localhost`) |
| `SLIDETAP_KEEPALIVE` | No | `1800` | Session keepalive interval in seconds |
| `SLIDETAP_ENFORCE_HTTPS` | No | `true` | Set to `false` for local development |

Example `.env` for local development:

```env
SLIDETAP_CONFIG_FILE=config.yaml
SLIDETAP_SECRET_KEY=DEVELOP
SLIDETAP_WEBAPP_URL=http://localhost:13000
SLIDETAP_STORAGE=C:\temp\slidetap
SLIDETAP_DBURI=sqlite:///C:/temp/slidetap/db.sqlite
SLIDETAP_BROKER_URL=amqp://localhost
SLIDETAP_KEEPALIVE=1800
SLIDETAP_ENFORCE_HTTPS=false
```

### config.yaml

The `config.yaml` file controls Celery worker behaviour and image processing settings:

```yaml
celery:
  concurrency: 1                    # number of concurrent worker processes
  worker_max_tasks_per_child: 10    # restart worker after N tasks (controls memory)
  broker_heartbeat: 120             # AMQP heartbeat in seconds (0 = disabled)

dicomization:
  levels: 3                         # number of pyramid levels
  threads: 1                        # threads per conversion task
  include_labels: false
  include_overviews: false
```

## Architecture

The back-end is part of a three-layer stack:

```
slidetap-app          FastAPI + Celery (this package)
      ↓  plugin interfaces
bigpicture-slidetap   BigPicture-specific adapters and Excel mapper
      ↓  data model
bigpicture-metadata-interface   XML serialization and submission
```

The recommended way to build on top of SlideTap is to create your own project that extends [bigpicture-slidetap](https://github.com/imi-bigpicture/bigpicture-slidetap).

## Implementing a custom application

A SlideTap application requires concrete implementations of the following interfaces:

| Interface | Purpose |
|---|---|
| `Schema` | Defines metadata structure (item types, attribute types) |
| `MetadataImportInterface` | Imports metadata from an external source (LIMS, XLSX, SQL) |
| `ImageImportInterface` | Locates and imports WSI images (PACS, filesystem) |
| `MetadataExportInterface` | Exports curated metadata (e.g. to BigPicture XML) |
| `ImageExportInterface` | Exports images (e.g. DICOM conversion) |
| `AuthInterface` | Authenticates users |

Wire them together in a `web_app_factory.py`:

```python
from dishka import make_async_container
from fastapi import FastAPI
from slidetap import BaseProvider
from slidetap.service_provider import ConfigProvider
from slidetap.web import SlideTapWebAppFactory, WebAppProvider

def create_app() -> FastAPI:
    base_provider = BaseProvider(
        schema_interface=YourSchemaInterface,
        metadata_export_interface=YourMetadataExportInterface,
        metadata_import_interface=YourMetadataImportInterface,
        mapper_injector=YourMapperInjector,
    )
    config_provider = ConfigProvider()
    web_provider = WebAppProvider(auth_interface=YourAuthInterface)
    container = make_async_container(base_provider, config_provider, web_provider)
    return SlideTapWebAppFactory.create(container=container)

app = create_app()
```

The image interfaces (`ImageImportInterface`, `ImageExportInterface`) are wired in the task app factory instead, since image processing runs in the Celery worker. See `apps/example/` for a complete reference implementation of both the web and task app factories.

## Running tests

```console
uv run pytest -m unittest          # fast unit tests only
uv run pytest                      # all tests (integration tests require WSI images)
```

Integration tests require two WSI images placed at:
- `tests/test_data/Image 1/Image 1.svs`
- `tests/test_data/Image 2/Image 2.svs`

A suitable test image is [CMU-1-SMALL-REGION.SVS](https://cytomine.com/collection/cmu-1/cmu-1-small-region-svs).
