# SlideTap example app

Reference implementation of the interfaces SlideTap expects, built on a static
JSON file rather than a real LIS or PACS. Read it as a template: it is the
smallest complete application, and it implements every piece you have to supply.

It is a separate distribution, `slidetap-example`, installed alongside the
library, and it is what the integration tests and the `example/` Docker Compose
stack run.

## What it implements

| Piece | Where | What it does |
|---|---|---|
| `ExampleSchema`, `ExampleSchemaInterface` | `schema.py` | Patient → case → specimen → block → slide → WSI, plus an observation on the case |
| `ExampleMetadataImportInterface` | `interfaces/metadata_import.py` | Parses the uploaded JSON and builds the items for it |
| `ExampleImageImportInterface` | `interfaces/image_import.py` | Resolves an image to a file on disk under a configured root |
| `ExampleMetadataExportInterface` | `interfaces/metadata_export.py` | Writes the selected items of the dataset as a single `metadata.json` |
| `ExampleImageExportInterface` | `interfaces/image_export.py` | Runs the DICOM conversion pipeline for each exported image |
| `ExampleMapperInjector` | `mapper_injector.py` | Seeds mappers for collection, fixation, sampling, embedding, and stain |
| Authentication | `web_app_factory.py` | `JsonFileAuthInterface`, the ready-made file-backed auth that ships with SlideTap |

Pseudonym generation and item naming are not implemented here, so the SlideTap
defaults apply.

## Input format

`parse_file` expects a JSON file of content type `application/json`, validated
against `ContainerModel` in `model.py`. It holds seven flat lists, `patients`,
`cases`, `specimens`, `blocks`, `slides`, `images`, and `observations`, whose
members refer to each other by identifier rather than by nesting. A block names
several specimen identifiers, so the sampling relations are many-to-many where
the schema allows it.

`tests/test_data/input.json` is a working file to start from.

## Images

`ExampleImageImportInterface` resolves each image to
`<example_test_data>/<image identifier>/<image identifier><extension>`, and
fails the image if no such file exists. Both parts are read from the app's own
YAML config, not from the environment:

```yaml
example_test_data: /storage/images
example_test_data_image_extension: .svs
```

They default to `tests/test_data` and `.svs`. See [Setup test
data](../../README.md#setup-test-data) for how to download images the
integration tests can use.

## Export

Metadata export writes one `metadata.json` per project, containing every
selected item grouped by item schema name. Image export runs `ImageProcessor`
with `DicomProcessingStep`, `CreateThumbnails`, `StoreProcessingStep`, and
`FinishingStep`, so exported images are converted to DICOM with thumbnails.

## Running

Migrations are an explicit step, and both processes refuse to start against a
database that has not had them applied:

```console
> uv run slidetap-db upgrade
> uv run slidetap-task-init-schema
```

Then, in separate terminals:

```console
> uv run uvicorn slidetap_example.web_app:app --reload --port 5001
> SLIDETAP_TASK_APP=slidetap_example uv run slidetap-task-worker
```

Port 5001 is what the front-end dev server proxies `/api` to.

See the [back-end README](../../README.md#configuration-of-application) for the
environment variables and YAML settings both processes need, and [the example
documentation](https://imi-bigpicture.github.io/slidetap/example) for running
the whole stack in Docker instead.
