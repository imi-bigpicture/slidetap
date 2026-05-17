# _SlideTap_ back-end

The _SlideTap_ back-end is responsible for interacting with the database and provide services for handling metadata and images. The front-end communicates with the back-end using REST controllers. The application requires that several user-specific implementations are provided, see [Required implementations](#required-implementations).

## Requirements

The back-end requires Python >=3.9. Other main dependencies are:

- FastAPI for serving controllers.
- Procrastinate for running background tasks.
- SqlAlchemy for database store. Using either sqllite or postgresql is supported.
- Pydantic for serializing items for the front-end.
- WsiDicom and WsiDicomizer for reading WSIs.
- dishka for dependency injection.

## Components

The back-end application is divided into modules:

- Web: Controllers and services for the front-end.
- Task: For running background tasks.
- Database: for storing and retreiving entities.
- Config: Configuration of the application.
- Services: Services for use with web controllers and background tasks.

The application is run as a web application serving the controllers and one or more workers running the background tasks.

## Required implementations

A SlideTap application is built up using varios components, some that are generic, some that are specific to the type of dataset to produce, and some that are specific to the user environment. The components that are specific are:

### Schema

A `Schema` defines what kind of `Samples`, `Images`, `Annotations`, and `Observations` that can be created, how they can be related, and what kind of `Attributes` they can have. _SlideTap_ can be configured to use different metadata schemas, but does not come with any defined `Schemas` (except for the example application). A suitable `Schema` must thus be created by the user. A `Schema` is composed a `ProjectSchema`, a `DatasetSchema`, one or more `ItemSchema`s, describing the structure and relation of for example samples and images, and `AttributeSchema`s, describing the structure of attributes assigned to a project and items. See `apps\example\schema.py` for an example of a `Schema`.

#### ItemSchema

A `ItemSchema` can be of four types:

- `SampleSchema`: Describing a sample, such as a patient, specimen, block, or slide, defining how a sample relates to other samples (e.g. sampled from) and what attributes a sample can have (e.g. ´embedding medium´, ´staining´).

- `ImageSchema`: Describing an image, typically a WSI, with what sample types it can image and attributes the image can have.

- `AnnotationSchema`: Describing an annotation done on an image.

- `ObservationSchema`: Describing an observation done on either a sample, an image, or an annotation.

#### AttributeSchema

An attribute schema describes an attribute, and can be of different type depending on the required value type:

- `StringAttributeSchema`: Used for attributes that are represented by a string value.

- `NumericAttributeSchema` Used for attributes that are represented by a integer or float value.

- `MeasurementAttributeSchema` Used for attributes that are represented by a float value and a unit.

- `DatetimeAttributeSchema` Used for attributes that are represented by a time, date, or datetime value.

- `BooleanAttributeSchema` Used for attributes that are represented by a boolean value.

- `CodeAttributeSchema` Used for attributes that are represented by a code (code, scheme, meaning) value.

- `ObjectAttributeSchema` Use for attributes that in itself contain other attributes.

- `ListAttributeSchema` Used for attributes that are a list of attributes.

- `UnionAttributeSchema` Used for attributes that can be of two or more value types.

### Importers and exporters

### MetadataImportInterface

A [`MetadataImportInterface`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/external_interfaces/metadata_import.py) is responsible for importing metadata from an outsde source, such as a LIMS, and organize it into the used schema.

### ImageImportInterface

An [`ImageImportInterface`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/external_interfaces/image_import.py) is responsible for importing images from an outsde source, such as a PACS, and making it avaiable for further use.

### MetadataExportInterface

A [`MetadataExportInterface`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/external_interfaces/metadata_export.py) that can export the curated metadata in a project to a serialized format for storage.

### ImageExportInterface

An [`ImageExportInterface`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/external_interfaces/image_export.py) that can export the images in a project to storage in required format.

### Authentication and login

An [`AuthInterface`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/external_interfaces/auth.py) that authenticates users.

These components must be created by the user, see [Example application](#Example application)

### Create application

The back-end application is created using the `create()`-method of the [`SlideTapWebAppFactory`](slidetap/web/app_factory.py)-class and the [`SlideTapTaskAppFactory`](slidetap/task/app_factory.py)-class.

#### Create web application

Create a `web_app_factory.py`-file with a `create_app()`-method that builds a Dishka container from your providers and passes it to `SlideTapWebAppFactory.create()`:

```python
from dishka import make_async_container
from fastapi import FastAPI
from slidetap import BaseProvider
from slidetap.service_provider import ConfigProvider
from slidetap.task import ProcrastinateAppProvider
from slidetap.web import SlideTapWebAppFactory, WebAppProvider

def create_app() -> FastAPI:
    base_provider = BaseProvider(
        schema_interface=YourSchemaInterface,
        metadata_export_interface=YourMetadataExportInterface,
        metadata_import_interface=YourMetadataImportInterface,
        mapper_injector=YourMapperInjector,
    )
    config_provider = ConfigProvider()
    config_provider.provide(YourConfig.parse, provides=YourConfig)
    web_provider = WebAppProvider(auth_interface=YourAuthInterface)
    app_provider = ProcrastinateAppProvider()
    container = make_async_container(
        base_provider, config_provider, web_provider, app_provider
    )
    return SlideTapWebAppFactory.create(container=container)
```

`ProcrastinateAppProvider` is required because `WebAppProvider` provides the
`Scheduler`, which needs the Procrastinate `App` to defer tasks.

Add any additional dependencies to the relevant provider. A lambda can be used
to provide an already-instanced dependency:

```python
    web_provider.provide(SomeDependency)
    web_provider.provide(lambda: some_instance, provides=SomeInstancedDependency)
```

Next create a `web_app.py` file importing your app factory and creating the app:

```python
from your_web_app_factory import create_app

app = create_app()
```

#### Create a task application

Create a `task_app_factory.py`-file with a `make_task_app()`-method that builds a Dishka container from your providers and passes it to `SlideTapTaskAppFactory.create()`:

```python
from dishka import make_container
from procrastinate import App as TaskApp
from slidetap import BaseProvider
from slidetap.service_provider import ConfigProvider
from slidetap.task import (
    ProcrastinateAppProvider,
    SlideTapTaskAppFactory,
    TaskAppProvider,
)

def make_task_app() -> TaskApp:
    base_provider = BaseProvider(
        schema_interface=YourSchemaInterface,
        metadata_export_interface=YourMetadataExportInterface,
        metadata_import_interface=YourMetadataImportInterface,
        mapper_injector=YourMapperInjector,
    )
    task_provider = TaskAppProvider(
        image_export_interface=YourImageExportInterface,
        image_import_interface=YourImageImportInterface,
    )
    app_provider = ProcrastinateAppProvider()
    config_provider = ConfigProvider()
    container = make_container(
        base_provider, task_provider, app_provider, config_provider
    )
    return SlideTapTaskAppFactory.create(container=container)
```

Add any additional dependencies to the relevant provider.

Next create a `task_app.py` file importing your app factory and creating the app:

```python
from your_task_app_factory import make_task_app

task_app = make_task_app()
```

Workers are run via the `slidetap-task-worker` console script, which reads
`concurrency` and `stalled_worker_timeout` from `config.yaml` under the
`task:` section and uses `SLIDETAP_TASK_APP` to locate the App
module:

```console
> SLIDETAP_TASK_APP=your_package uv run slidetap-task-worker
```

For ad-hoc / debugging runs (custom queues, `--verbose`, …) the
Procrastinate CLI is still available:

```console
> uv run procrastinate --app=your_package.task_app.task_app worker
```

### Example application

A simple example application, located in `slidetap\apps\example` is provided for demonstration and testing. This can be run with the provided `flask_run.bat` script or made into a docker image. The example application reads metadata from the uploaded json file (see `tests\test_data\input.json`).

See [Setup test data](#setup-test-data) for how to download the needed test images.

## Development

This section assumes that the commands are issued in the `slidetap-app` subfolder.

### Setup

First install uv according to [instructions](https://docs.astral.sh/uv/getting-started/installation/).

### Configuration of application

Create an `.env`-file in the project folder setting the following environmental variables:

- SLIDETAP_SECRET_KEY: The secret key to use.
- SLIDETAP_WEBAPP_URL: The URL the front end is served at.
- SLIDETAP_STORAGE: Path to location where to store data.
- SLIDETAP_DBURI: URI for database storage.
- SLIDETAP_KEEPALIVE: Keepalive time in seconds.
- SLIDETAP_ENFORCE_HTTPS: If to enforce the use of HTTPS.

```env
SLIDETAP_SECRET_KEY=DEVELOP
SLIDETAP_WEBAPP_URL=http://localhost:13000
SLIDETAP_STORAGE=C:\temp\slidetap
SLIDETAP_DBURI=sqlite:///C:/temp/slidetap/db.sqlite
SLIDETAP_KEEPALIVE=1800
SLIDETAP_ENFORCE_HTTPS=false
```

### To run webserver

```console
> uv run flask run --host=0.0.0.0
```

### Setup test data

To run the integration test, you need to place two wsi images (for example [CMU-1-SMALL-REGION.SVS](https://cytomine.com/collection/cmu-1/cmu-1-small-region-svs)) in the `tests\test_data\Image 1` and `Image 2` folders, named `Image 1.svs` and `Image 2.svs`.

### To run test

```console
> uv run pytest
```
