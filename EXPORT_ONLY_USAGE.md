# Using SlideTap for Export-Only Functionality

This guide explains how to use SlideTap as a minimal export engine when you only
need to export data that you have populated yourself, without the import and
curation workflow.

## Overview

SlideTap's modular architecture lets you use the export half of the application
on its own. This suits you if you:

- Have your own data population process.
- Do not need the web UI for curation.
- Want to reuse the export capabilities (DICOM conversion, metadata
  serialization).

## Architecture: minimal export engine

```
Your scripts → Database (PostgreSQL) ← Web service (FastAPI) → Export tasks (Procrastinate) → Storage
```

The database is also the task queue, so PostgreSQL is the only infrastructure
you need beyond the two SlideTap processes.

## What you need

### Core components

**Backend services:**

- `slidetap-app/src/slidetap/` - core library.
- PostgreSQL database, which also serves as the task queue.
- A Procrastinate worker, for asynchronous export processing.

**Your implementation:**

```
your_implementation/
├── interfaces/
│   ├── metadata_export.py       # metadata export implementation
│   └── image_export.py          # image export implementation
├── schema.py                    # RootSchema for your data model
├── web_app_factory.py           # create_app(), builds the dishka container
├── web_app.py                   # app = create_app()
├── task_app_factory.py          # make_task_app()
├── task_app.py                  # task_app = make_task_app()
└── config.yaml                  # configuration
```

A schema is not optional. Items are stored against item and attribute schemas,
so you need a `RootSchema` even when you never import anything.

### Docker deployment

Migrations are an explicit deploy step: the web app and the worker both check
the database revision at startup and refuse to run against a database that is
behind. Apply them once, before either service starts.

```yaml
services:
  dbservice:
    image: postgres:17
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=slidetap
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d slidetap"]
      interval: 5s
      retries: 10

  dbmigrate:
    build: ./slidetap-app
    environment:
      SLIDETAP_DBURI: postgresql://user:password@dbservice:5432/slidetap
    command: >
      sh -c "slidetap-db upgrade &&
             slidetap-task-init-schema"
    restart: "no"
    depends_on:
      dbservice:
        condition: service_healthy

  api:
    build: ./slidetap-app
    environment:
      SLIDETAP_WEB_APP: your_implementation.web_app:app
      SLIDETAP_DBURI: postgresql://user:password@dbservice:5432/slidetap
    ports:
      - "8000:8000"
    depends_on:
      dbmigrate:
        condition: service_completed_successfully

  worker:
    build: ./slidetap-app
    environment:
      SLIDETAP_TASK_APP: your_implementation
      SLIDETAP_DBURI: postgresql://user:password@dbservice:5432/slidetap
    command: ["slidetap-task-worker"]
    depends_on:
      dbmigrate:
        condition: service_completed_successfully
```

`SLIDETAP_WEB_APP` is the uvicorn target for the FastAPI app.
`SLIDETAP_TASK_APP` is the dotted name of the package whose `task_app.py`
exposes `task_app`, not a module path or an attribute reference.

`SLIDETAP_CONFIG_FILE` must also be set for both services, pointing at your
`config.yaml`. Nothing parses any configuration without it.

## Required export interfaces

### 1. Metadata export interface

Implement `MetadataExportInterface` from
[slidetap-app/src/slidetap/external_interfaces/metadata_export.py](slidetap-app/src/slidetap/external_interfaces/metadata_export.py):

```python
class MetadataExportInterface(metaclass=ABCMeta):
    @abstractmethod
    def preview_item(self, item: Item) -> str | None:
        """Return a serialized representation of the item."""

    @abstractmethod
    def export(self, project: Project, dataset: Dataset) -> None:
        """Export metadata for the project to storage."""
```

**Example:** see
[apps/example/src/slidetap_example/interfaces/metadata_export.py](slidetap-app/apps/example/src/slidetap_example/interfaces/metadata_export.py).

### 2. Image export interface

Implement `ImageExportInterface` from
[slidetap-app/src/slidetap/external_interfaces/image_export.py](slidetap-app/src/slidetap/external_interfaces/image_export.py):

```python
class ImageExportInterface(metaclass=ABCMeta):
    @abstractmethod
    def export(
        self, image: Image, batch: Batch, project: Project, task_id: str
    ) -> Image:
        """Export an image to the export format and save it to the
        task-specific processing directory identified by task_id."""

    def create_export_metadata(
        self, image: Image, base: WsiDicomizerMetadata
    ) -> WsiDicomizerMetadata | None:
        """The metadata that belongs in the exported files of an image."""
```

Output goes to the per-task processing directory obtained from
`StorageService`, keyed by `task_id`, not straight to the outbox. Moving the
files to the outbox happens separately, when the batch is completed.
`create_export_metadata` is not abstract: override it when the export format
carries metadata of its own, and it is asked for again when the files are
written to the outbox, so that edits made after export are picked up.

**Example:** see
[apps/example/src/slidetap_example/interfaces/image_export.py](slidetap-app/apps/example/src/slidetap_example/interfaces/image_export.py),
which converts to DICOM with `ImageProcessor` and `DicomProcessingStep`.

## Workflow

### Step 1: populate the database

Go through the services rather than writing rows directly. They apply mappers,
validate, and maintain the item relations and status fields that the export
preconditions below are checked against. Resolve them from the same dishka
container your app factory builds:

```python
from slidetap.services import BatchService, ItemService, ProjectService

project_service = container.get(ProjectService)
batch_service = container.get(BatchService)
item_service = container.get(ItemService)

project = project_service.create(Project(...))
batch = batch_service.create(BatchCreate(project_uid=project.uid, ...))
for item in my_items:
    item_service.add(item)
```

The entities involved:

- **Projects** - containers for datasets.
- **Batches** - groups of items within a project.
- **Items** - samples, images, annotations, observations.
- **Attributes** - metadata attached to items.
- **Schema** - defines item types and attribute structure.

### Step 2: trigger the export

The routes are grouped under plural prefixes, and the order matters. Images are
exported per batch, metadata per project, and the metadata export runs last.

**Export images in a batch:**

```bash
curl -X POST http://localhost:8000/api/batches/batch/{batch_uid}/process
```

**Complete the batch, once its images have finished:**

```bash
curl -X POST http://localhost:8000/api/batches/batch/{batch_uid}/complete
```

**Complete the project:**

```bash
curl -X POST http://localhost:8000/api/projects/project/{project_uid}/complete
```

**Export metadata:**

```bash
curl -X POST http://localhost:8000/api/projects/project/{project_uid}/export
```

**Preview an individual item:**

```bash
curl -X GET http://localhost:8000/api/items/item/{item_uid}/preview
```

The metadata export refuses to run unless all of the following hold, so a
population script has to leave the data in that state:

- The project is completed, and every batch in it is completed.
- The project is valid.
- Every item has a pseudonym. An item is named in the exported bundle by its
  pseudonym and by nothing else.

### Step 3: retrieve the results

Exported files are written under the configured storage location, in the
project's outbox. The exact layout is decided by your export interfaces, since
they are what writes the files.

## What you can skip

- **Frontend** (`slidetap-client/`), if you drive everything over the API.
- **Nginx webserver**, since you can talk to FastAPI directly.
- **Import interfaces**. `MetadataImportInterface` is a required constructor
  argument of `BaseProvider`, so supply a stub whose methods raise, rather than
  omitting it. `ImageImportInterface` is only needed by the task app.
- **Curation UI logic**. You still need validation to pass, because the export
  checks project validity.

## Minimal code to write

1. **Export interfaces**, to serialize your metadata and convert your images.
2. **Schema**, defining your item and attribute types.
3. **App factories**, wiring the interfaces into a dishka container for the web
   app and the task app.
4. **Data population script**, following the data model above.
5. **Config file**, with storage paths and database credentials.

## Key components to reuse

From the example application:

1. `ExampleMetadataExportInterface`, to adapt for your output structure.
2. `ExampleImageExportInterface`, which already converts to DICOM.
3. `ImageProcessor` with `DicomProcessingStep`, handling WSI to DICOM
   conversion.
4. The app factory pattern in `apps/example/src/slidetap_example/`.

## Alternative: pure script approach

If you want to avoid running services entirely, build the container yourself and
call the interfaces directly.

**Pros:**

- No FastAPI or Procrastinate worker needed.
- Minimal infrastructure.

**Cons:**

- No concurrency, so large datasets take as long as they take.
- No API access.
- No task monitoring or retry logic.
- No status handling: the tasks are what set image and batch status, so a script
  that bypasses them leaves the database in a state the web application will not
  recognise. Use this only if you never intend to open the project in the UI.

```python
from dishka import make_container
from slidetap.external_interfaces import ImageExportInterface, MetadataExportInterface
from slidetap.services import DatabaseService

container = make_container(base_provider, task_provider, config_provider)
database_service = container.get(DatabaseService)
metadata_exporter = container.get(MetadataExportInterface)
image_exporter = container.get(ImageExportInterface)

with database_service.get_session() as session:
    project = database_service.get_project(session, project_uid).model
    dataset = database_service.get_dataset(session, project.dataset_uid).model

metadata_exporter.export(project, dataset)
```

## Getting started

1. Study the example implementation in `slidetap-app/apps/example/`.
2. Define your schema and your export interface implementations.
3. Set up a minimal deployment: PostgreSQL, migrations, API, worker.
4. Write scripts to populate the database with your data.
5. Trigger the exports in the order given above.
6. Retrieve the exported files from storage.

## References

- [Main README](README.md)
- [Backend documentation](slidetap-app/README.md)
- [Tasks documentation](docs/tasks.md)
- [Example implementation](slidetap-app/apps/example/)
- External interfaces:
  - [MetadataExportInterface](slidetap-app/src/slidetap/external_interfaces/metadata_export.py)
  - [ImageExportInterface](slidetap-app/src/slidetap/external_interfaces/image_export.py)
