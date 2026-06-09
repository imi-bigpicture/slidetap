# SlideTap Copilot Instructions

## Architecture Overview

SlideTap is a **digital pathology dataset curation webapp** with a pluggable architecture for site-specific integrations.

### Two-App Structure
- **`slidetap-app/`** - Python backend (FastAPI + Procrastinate)
  - Web app serves REST API via FastAPI with `dishka` dependency injection
  - Task app runs background jobs (image download/processing, export) via Procrastinate (Postgres-backed, no separate broker)
  - Both apps share a common `BaseProvider` but use different service providers (`WebAppProvider`, `TaskAppProvider`)
- **`slidetap-client/`** - React/TypeScript frontend (Vite + Material UI)
  - Communicates with backend via REST API
  - Uses OpenSeadragon for WSI viewing

### Key Data Flow
1. User uploads metadata file → `MetadataImportInterface.parse_file()` → creates Project/Batches/Items
2. Items are curated in UI (attributes, mappings)
3. Export triggers Procrastinate tasks → `ImageExportInterface` + `MetadataExportInterface` serialize to storage

## Required Implementations Pattern

SlideTap requires **site-specific implementations** of these interfaces (see `slidetap/external_interfaces/`):

| Interface | Purpose |
|-----------|---------|
| `MetadataImportInterface` | Parse input files, search external LIMS, create items |
| `MetadataExportInterface` | Serialize curated metadata to output format |
| `ImageImportInterface` | Download images from PACS/storage |
| `ImageExportInterface` | Export images (e.g., DICOM conversion via wsidicomizer) |
| `AuthInterface` | User authentication |
| `RootSchema` | Define project/sample/image schema with attribute types |

**Reference implementation**: `slidetap-app/apps/example/` - use this as a template for new integrations.

### Schema Definition Pattern
Schemas define the data model structure. See [apps/example/src/slidetap_example/schema.py](slidetap-app/apps/example/src/slidetap_example/schema.py):
```python
class MySchema(RootSchema):
    def __init__(self):
        super().__init__(
            uid=UUID("..."),
            name="My Schema",
            project=ProjectSchema(...),
            dataset=DatasetSchema(...),
            images={self.image.uid: self.image},
            samples={...},  # SampleSchema instances
        )
```

## Development Commands

### Backend (`slidetap-app/`)
```bash
# Install with uv (recommended)
uv sync --dev

# Run tests (uses pytest markers)
uv run pytest -m unittest           # Fast unit tests
uv run pytest -m integration        # Full integration tests (slower)

# Run web app (development)
uv run uvicorn slidetap_example.web_app:app --reload --port 5001

# Run Procrastinate worker
uv run slidetap-task-worker
```

### Frontend (`slidetap-client/`)
```bash
npm install
npm run dev      # Dev server on :13000, proxies /api to :5001
npm run build    # Production build
npm run lint     # ESLint check
```

### Docker Deployment
See `example/docker-compose.yml` - requires PostgreSQL only (Procrastinate uses the DB as its queue):
```bash
cd example && docker-compose up
```

## Code Conventions

### Backend
- **Dependency injection**: Use `dishka` - register providers in `BaseProvider`/`WebAppProvider`/`TaskAppProvider`
- **Database access**: Services use `DatabaseService.get_session()` context manager with SQLAlchemy
- **Pydantic models**: Used for REST API serialization (see `slidetap/model/external/`)
- **Copyright header**: All Python files must have Apache 2.0 license header

### Frontend
- **API services**: Located in `src/services/api/` - one file per router endpoint
- **Models**: Mirror backend Pydantic models in `src/models/`
- **Components**: Organized by domain in `src/components/` (project/, item/, mapper/, etc.)
- **Copyright header**: All typescript files must have Apache 2.0 license header


### Testing
- Mark tests with `@pytest.mark.unittest` or `@pytest.mark.integration`
- Integration tests use `TestClient` with in-memory SQLite
- Use `ExampleSchema` and example implementations for test fixtures (see `tests/conftest.py`)

## Key Files Reference

| Path | Purpose |
|------|---------|
| `slidetap-app/src/slidetap/service_provider.py` | Core DI registration |
| `slidetap-app/src/slidetap/web/app_factory.py` | FastAPI app creation |
| `slidetap-app/src/slidetap/task/tasks.py` | Procrastinate task definitions |
| `slidetap-app/src/slidetap/model/schema/` | Schema base classes |
| `slidetap-app/apps/example/` | Reference implementation |
| `example/docker-compose.yml` | Docker deployment template |
