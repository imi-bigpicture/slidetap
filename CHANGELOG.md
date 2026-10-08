# SlideTap changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking changes

- `SchemaInterface.create()` is replaced by `root()`, the root of new projects, and `previous_roots()` gives the roots of earlier versions.
- `SchemaService` takes the plugin's `SchemaInterface`, which it asks for its roots, and the `DatabaseService`.
- `SchemaService` no longer has the members of a single root, such as `root`, `get_root()` without a uid, `items`, and the layout lookups: use `default_root` or the root of the project.
- `ValidationService.pending_expression()` and `ReviewService.review_unit_uids_in()` take the root the item schemas are in.
- `SchemaService.attributes`, `private_attributes`, and `get_attributes()` are removed: use `get_attribute()`, `get_private_attribute()`, `get_any_attribute()`, or the lookups of a root.
- `NotAllowedActionError` and `NotFoundError` are imported from `slidetap.model`, as `slidetap.database` no longer exports them.
- `ImagePipelineService` no longer takes a `RootSchema`.
- `ProjectService.get_all_of_root_schema()` is removed, and `get_all(root_schema_uid)` replaces it.
- `DatabaseService.get_mapper_by_name()` takes the family of the mapper.
- `MetadataExportService` takes a `SchemaService`.
- `MetadataImportService.create_project(name)` creates the project with its dataset and default batch, and `create_dataset()` is removed.
- The projects on a previous root are view only: only those on the root of new projects can be changed.
- `SchemaInterface.get_schema_type()` and the injected root schema of new projects are removed: a plugin reads the root from the `SchemaService`.
- Neither the web app nor a worker starts while projects in the database are on a root schema that is not provided, and the error names those roots.
- Neither the web app nor a worker starts while projects hold items or attributes on schemas their root does not have, and the error names those roots.
- The stored mappers are set up on deploy by `slidetap-mappers set-up`, not at startup of the web app, so the plugin's mapper sheets are injected only when it runs.
- `ItemService.get_hierarchy()`, `ItemService.get_images_for_item()`, and `OverviewService.get_overview_data()` take the uid of the layout, which they look up in the root of the item.

### Added

- `DELETING` batch and project statuses, shown while a background task removes what they hold.
- Deleting a batch asks for confirmation in the client and removes the downloaded and processed files of its images.
- Export is refused, with the reason, for a project with a batch being deleted or a selected image that was never stored.
- `SchemaInterface.previous_roots()` lets a plugin provide the roots of earlier versions that projects are still on, as view only.
- A project on a view-only root can be viewed, validated, and deleted, and every change to it is refused with 409.
- Root schemas have an optional `version` and a `family_uid`, and are shown by name and version.
- Schema endpoints `/schemas/roots` and `/schemas/root/{uid}`, and a `rootSchemaUid` parameter for what is looked up within a root.
- Endpoint `/projects/project/{uid}/actions` saying what a project can be offered.
- `RootSchemaSupport` decides whether a project can be changed from its root and its state, and a deleted project is refused as its actions say.
- Mappers stored without a family are given it by `slidetap-mappers set-up`, and one whose attribute no provided root has is adopted by name.
- `SchemaInterface.migration_from(root)` lets a plugin provide a `SchemaMigration` moving the projects on a previous root to the root of new projects.
- `slidetap-mappers set-up` sets up the stored mappers with the container from `create_container()` in the `container` module of the package named by `SLIDETAP_TASK_APP`.
- `UnchangedAttributeMigrator`, in `slidetap.external_interfaces.implementations.migration` with the other migration helpers, moves an attribute to the attribute schema of another root.
- `DeclarativeSchemaMigration` implements a migration from an `ObjectMigrator` per project, dataset, and item schema, each declaring what changed and refused when it says nothing about a changed attribute.
- `EnumAttributeMigrator` and `FixedValueAttributeMigrator` migrate an attribute whose values changed, and an attribute that loses its value to one is left unresolved for the curator.
- `NestedAttributeMigrator` migrates an object, list, or union attribute through the migrators of the attributes it holds, and `ObjectMigrator.attribute_migrator_of()` finds the migrator of an attribute schema at any depth.
- `AttributeMigrator.migrate()` returns a `MigratedAttribute`, the migrated attribute with why its value in effect lost values.
- A migrating project status, while which nothing can be changed in the project and it cannot be deleted (database migration).
- Projects record when they were last exported, and a project that was exported is never migrated (database migration).
- A project is not migrated while work is under way in a batch, or once its images are stored or locked in a batch to be.
- A mapper of an attribute a migration gives another schema is moved to that schema by `MigrationService.migrate_mappers()`, before the mappers of the plugin are injected.
- A mapper moved by a migration is given the family of the root of new projects, and the set-up fails where that family has another mapper of its name.
- A migrated project returns to the status it had before the migration.
- A migration gives every search item of a project its item schema on the root migrated to.
- `SchemaMigration.migrate_item_schema()` gives the item schema of the target root that an item schema of the source migrates to.
- A project is migrated in steps, with what the migration could not convert resolved by a curator before it is completed (database migration).
- `ObjectMigrationResult`, what a migration returns for an object in `slidetap.model`, holds an `UnresolvedAttribute` at the tag of each attribute the migration could not convert, for the curator to resolve.
- Planning a migration also makes an attribute issue of every top-level attribute the migration leaves invalid that was valid before.
- An attribute with a value that a migration drops is an attribute issue, which the curator accepts before the migration can be submitted.
- A resolved value keeps the row, lock, and read-only flag of the attribute it resolves.
- Endpoints for the steps of migrating a project.
- The actions of a project say whether its root has a migration, and why the project cannot be migrated.
- A Convert view in the client, listed only where a root has a migration, that starts a conversion and goes through what it could not convert, item by item.
- A `NotFoundError` raised by a service is answered with 404 on every endpoint.
- `ProjectService.get_completed()` and `get_exportable()` give a project where it is completed, or can be exported.

### Changed

- Batch and project deletion run as background tasks. `DELETE /api/batches/batch/{uid}` and `DELETE /api/projects/project/{uid}` mark the row as deleting, answer `{"status": "scheduled"}` and refuse with `409` while a worker holds the batch.
- A batch that is locked, storing images or completed can no longer be deleted; a locked batch is reopened first.
- Items in a batch are deleted with set-based statements instead of one at a time.
- `BatchStatus.DELETED` is now `13` and `ProjectStatus.DELETED` is `12` on the wire; client and server are deployed together.
- `BaseProvider` takes any factory of the `SchemaInterface`, not only its class.
- Every operation on a project reads its item schemas from the root schema the project was created with.
- The project list shows the projects of every root, and the root each is on.
- Mappers are unique by name within a family of root schemas (database migration).
- Injecting a mapping again with another attribute updates the mapping and the values it was applied to, so the injected sheet wins.
- A changed or deleted mapping leaves what it mapped in projects that cannot be changed or were exported.
- Requires pydantic 2.10 or later.
- A root schema provided more than once is refused.
- The client shows a project with its own root schema and disables the actions the project cannot be offered.
- The Schemas page of the client shows the root schema chosen among those provided, by default the root of new projects.

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
