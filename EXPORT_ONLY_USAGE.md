# Using SlideTap for Export-Only Functionality

This guide explains how to use SlideTap as a minimal export engine when you only need to export data that you've manually populated in the database.

## Overview

SlideTap's modular architecture allows you to use only the export functionality without the full import/curation workflow. This is ideal when you:
- Have your own data population process
- Don't need the web UI for curation
- Want to leverage the export capabilities (DICOM, JSON, etc.)

## Architecture: Minimal Export Engine

```
Your Scripts → Database (PostgreSQL) ← Web Service (FastAPI) → Export Tasks (Celery) → Storage
```

## What You Need

### Core Components

**Backend Services:**
- `slidetap-app/src/slidetap/` - Core library
- PostgreSQL database
- RabbitMQ (message broker for task queue)
- Celery worker (for async export processing)

**Your Implementation:**
```
your_implementation/
├── export_interfaces/
│   ├── metadata_export.py       # JSON export implementation
│   └── image_export.py          # DICOM export implementation
├── app_factory.py               # FastAPI app setup
├── task_app_factory.py          # Celery worker setup
└── config.yaml                  # Configuration
```

### Docker Deployment

```yaml
services:
  postgres:
    image: postgres:17

  rabbitmq:
    image: rabbitmq:4

  api:
    build: ./slidetap-app
    environment:
      - SLIDETAP_APP_CREATOR=your_implementation.app_factory
    ports:
      - "8000:8000"

  worker:
    build: ./slidetap-app
    environment:
      - SLIDETAP_APP_CREATOR=your_implementation.task_app_factory
```

## Required Export Interfaces

### 1. Metadata Export Interface

Implement `MetadataExportInterface` from [slidetap-app/src/slidetap/external_interfaces/metadata_export.py](slidetap-app/src/slidetap/external_interfaces/metadata_export.py)

```python
class MetadataExportInterface(metaclass=ABCMeta):
    @abstractmethod
    def preview_item(self, item: Item) -> Optional[str]:
        """Return a serialized representation of the item."""

    @abstractmethod
    def export(self, project: Project, dataset: Dataset) -> None:
        """Export metadata for the project to storage."""
```

**Example:** See [apps/example/src/slidetap_example/interfaces/metadata_export.py](slidetap-app/apps/example/src/slidetap_example/interfaces/metadata_export.py) (~40 lines)

### 2. Image Export Interface

Implement `ImageExportInterface` from [slidetap-app/src/slidetap/external_interfaces/image_export.py](slidetap-app/src/slidetap/external_interfaces/image_export.py)

```python
class ImageExportInterface(metaclass=ABCMeta):
    @abstractmethod
    def export(self, image: Image, batch: Batch, project: Project) -> Image:
        """Export image file to the export format and save it to storage."""
```

**Example:** See [apps/example/src/slidetap_example/interfaces/image_export.py](slidetap-app/apps/example/src/slidetap_example/interfaces/image_export.py) (~30 lines)

The example includes DICOM conversion using `ImageProcessor` with `DicomProcessingStep`.

## Workflow

### Step 1: Populate Database

Use your own scripts to directly populate the database:

```python
from slidetap.database import ProjectDb, ItemDb
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

with Session(engine) as session:
    # Create project
    project = ProjectDb(name="My Dataset", ...)
    session.add(project)

    # Add items with metadata
    item = ItemDb(...)
    session.add(item)

    # Add image references
    # Add attributes

    session.commit()
```

**Required database structure:**
- **Projects** - containers for datasets
- **Items** - samples, images, annotations, observations
- **Attributes** - metadata attached to items
- **Schema** - defines item types and attribute structure
- **Batches** - groups of items (for image export)

### Step 2: Trigger Export via API

**Export metadata:**
```bash
curl -X POST http://localhost:8000/api/project/{project_uid}/export
```

**Export images in batch:**
```bash
curl -X POST http://localhost:8000/api/batch/{batch_uid}/export
```

**Preview individual item:**
```bash
curl -X GET http://localhost:8000/api/item/{item_uid}/preview
```

### Step 3: Retrieve Results

Exported files are saved to the configured storage location:

```
/storage/
├── projects/{project_uid}/
│   ├── metadata.json          # JSON metadata export
│   └── images/
│       ├── image1.dcm         # DICOM files
│       ├── image2.dcm
│       └── thumbnails/
```

## What You Can Skip

Since you're using export-only functionality:

- ❌ **Frontend** (`slidetap-client/`) - entirely unnecessary
- ❌ **Nginx webserver** - use FastAPI directly
- ❌ **Import interfaces** - don't implement `MetadataImportInterface` or `ImageImportInterface`
- ❌ **Curation/validation UI logic** - no need for validation services
- ❌ **Authentication** (optional) - only if you need API security

## Minimal Code to Write

To get export-only functionality working:

1. **Export interfaces** (~50-100 lines total)
   - Customize JSON format
   - Configure DICOM metadata

2. **App factory** (~20 lines)
   - Wire up interfaces with dependency injection
   - Configure FastAPI app

3. **Data population script** (variable length)
   - Insert your data into database
   - Follow SlideTap's data model

4. **Config file** (~30 lines)
   - Storage paths
   - Database credentials
   - Schema definitions

## Key Components to Reuse

From the example application:

1. **ExampleMetadataExportInterface** - Modify for your JSON structure
2. **ExampleImageExportInterface** - Already includes DICOM conversion
3. **ImageProcessor with DicomProcessingStep** - Handles WSI → DICOM conversion
4. **App factory patterns** - See `apps/example/src/slidetap_example/`

## Benefits of This Approach

✅ Reuse battle-tested export logic
✅ Async processing handles large datasets efficiently
✅ Simple REST API for triggering exports
✅ Extensible if needs grow later
✅ Example implementations to copy from
✅ Task monitoring and retry logic built-in

## Alternative: Pure Script Approach

If you want to avoid running services entirely:

**Pros:**
- No FastAPI, Celery, or RabbitMQ needed
- Simple Python script that directly calls export methods
- Minimal infrastructure

**Cons:**
- No async processing (slow for large datasets)
- No API access
- No task monitoring/retry logic
- Must handle errors manually

**Implementation:**
```python
from your_implementation.export_interfaces import MyMetadataExporter, MyImageExporter
from slidetap.database import get_session

with get_session() as session:
    project = get_project(session, project_uid)
    dataset = get_dataset(session, dataset_uid)

    # Direct export call
    metadata_exporter = MyMetadataExporter()
    metadata_exporter.export(project, dataset)

    # Export images
    image_exporter = MyImageExporter()
    for image in get_images(session, batch_uid):
        image_exporter.export(image, batch, project)
```

## Getting Started

1. Study the example implementation in `apps/example/`
2. Create your export interface implementations
3. Set up minimal Docker deployment (PostgreSQL + RabbitMQ + API + Worker)
4. Write scripts to populate the database with your data
5. Trigger exports via API calls
6. Retrieve exported files from storage

## References

- [Main README](README.md)
- [Backend Documentation](slidetap-app/README.md)
- [Tasks Documentation](docs/tasks.md)
- [Example Implementation](slidetap-app/apps/example/)
- External Interfaces:
  - [MetadataExportInterface](slidetap-app/src/slidetap/external_interfaces/metadata_export.py)
  - [ImageExportInterface](slidetap-app/src/slidetap/external_interfaces/image_export.py)
