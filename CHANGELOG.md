# SlideTap changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `DELETING` batch and project statuses, shown while a background task removes what they hold.
- Deleting a batch asks for confirmation in the client and removes the downloaded and processed files of its images.
- Export is refused, with the reason, for a project with a batch being deleted or a selected image that was never stored.

### Changed

- Batch and project deletion run as background tasks. `DELETE /api/batches/batch/{uid}` and `DELETE /api/projects/project/{uid}` mark the row as deleting, answer `{"status": "scheduled"}` and refuse with `409` while a worker holds the batch.
- A batch that is locked, storing images or completed can no longer be deleted; a locked batch is reopened first.
- Items in a batch are deleted with set-based statements instead of one at a time.
- `BatchStatus.DELETED` is now `13` and `ProjectStatus.DELETED` is `12` on the wire; client and server are deployed together.

### Fixed

- Deleting a large batch no longer blocks the web server for the duration of the delete.
- A batch delete that is interrupted no longer leaves a deleted batch behind with its items still selected in the dataset.

## [0.3.0] - 2026-09-11

### Added

- Review workflow where items and attributes can be flagged, rejected and re-evaluated, with a review view listing all outstanding issues.
- Hierarchy and overview views for curating items, including moving attributes between items and creating or deleting items.
- Pseudonym support through `PseudonymFactoryInterface`, with display modes and options to change or clear pseudonyms.
- Item naming through `ItemNamingFactoryInterface`.
- Private attributes, and tags and comments on items.
- Alembic migrations with a `slidetap-db` console script for managing the database schema.
- Health endpoint for readiness checks.
- Logging configured from a `logging:` section in the YAML config using `dictConfig`.
- PHI is removed from DICOM input files during image processing.
- Images are stored to an outbox as a tracked image status, so that a lost storage mount can be retried instead of failing the batch.
- Item identifiers are enforced unique per schema and dataset in the database.
- Light and dark theme in the client.
- The WSI viewer can display groups of images.
- Extension points for custom frontend components and additional API routes.

### Changed

- Web backend migrated from Flask to FastAPI, using Pydantic models instead of marshmallow and Dishka for dependency injection.
- Background task queue migrated from Celery to Procrastinate. Workers are run via the `slidetap-task-worker` console script; the task queue uses Postgres directly (`SLIDETAP_DBURI`), no broker required.
- Minimum supported Python raised to 3.12.
- Database driver changed from psycopg2 to psycopg 3.
- Python packaging moved from Poetry to uv, and the client from npm to pnpm.
- Console scripts rewritten with Typer.
- Client tables rebuilt on TanStack Table with custom components, replacing Material React Table.
- Excel metadata export moved to an optional `xlsx` extra.
- Hard-coded basic auth replaced by a JSON file backed `JsonFileAuthInterface`.
- Linting and formatting handled by ruff, pyright and typos, replacing flake8, black and codespell.

### Fixed

- Storage move and copy failures are no longer swallowed, and the outbox is no longer deleted before the move completes.
- Project deletion no longer fails when the dataset contains item schemas that are unknown to the application.
- Re-import of a batch handles items shared with other batches instead of duplicating them.
- The client stops polling projects and batches that are idle.

## [0.2.0] - 2025-05-27

### Changed

- Cleaner definition of external interfaces that needs to be implemented.
- Storing of nested attributes in serialized form.
- Static schemas.
- Database querying using explicit sessions.

## [0.1.0] - 2024-10-24

### Added

- Initial release of SlideTap

[Unreleased]: https://github.com/imi-bigpicture/slidetap/compare/v0.3.0..HEAD
[0.3.0]: https://github.com/imi-bigpicture/slidetap/tree/refs/tags/v0.3.0
[0.2.0]: https://github.com/imi-bigpicture/slidetap/tree/refs/tags/v0.2.0
[0.1.0]: https://github.com/imi-bigpicture/slidetap/tree/refs/tags/v0.1.0
