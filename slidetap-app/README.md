# _SlideTap_ back-end

The _SlideTap_ back-end is responsible for interacting with the database and provide services for handling metadata and images. The front-end communicates with the back-end using REST controllers. The application requires that several user-specific implementations are provided, see [Required implementations](#required-implementations).

## Requirements

The back-end requires Python >=3.9. Other main dependencies are:

- FastAPI for serving controllers.
- Celery for running background tasks.
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

The application is run as two application runnint the controllers and one Celery application running the background tasks.

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

An [`AuthService`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/web/services/auth/auth_service.py) that authenticates users and a [`LoginService`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/web/services/login/login_service.py) that logins users, and a [`LoginController`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/web/controller/login/login_controller.py) that the front-end can use to login users.

These components must be created by the user, see [Example application](#Example application)

### Create application

The back-end application is created using the `Create()`-methods of the [`SlideTapWebAppFactory`](slidetap/web/app_factory)-class and the [`SlideTapTaskAppFactory](slidetap/web/app_factory.py)-class.

#### Create web application

Create a `web_app_factory.py-file` with a `create_app()`-method calling the `SlideTapWebAppFactory.create()` using your service provider:

```python
from fastapi import FastAPI
from slidetap.config import Config
from slidetap import SlideTapWebAppFactory
from slidetap.service_provider import create_web_service_provider

def create_app(
    config: Optional[Config] = None,
) -> FastAPI:
    if config is None:
        config = Config()
    service_provider = create_web_service_provider(
        config=lambda: config,
        schema=YourSchema,
        metadata_export_interface=YourMetadataImportInterface,
        metadata_import_interface=YourMetadataExportInterface,
        auth_service=YourAuthServiceImplementation,
        mapper_injector=ExampleMapperInjector,
    )

    return SlideTapAppFactory.create(
        config=config,
        service_provider=service_provider,
    )
```

If your implementations required additional dependencies, add them to the service_provider. You can use a lambda to return an already instanced dependency:

```python
    service_provider.provide(SomeDependency)
    service_provider.provide(lambda: some_instanced_dependency, provides=SomeInstancedDependency)
```

Next create a `web_app.py` file importing your app factory and creating the app:

```python
from your_web_app_factory import create_app

app = create_app()
```

#### Create a task application

Create a `task_app_factory.py-file` with a `make_celery()`-method calling the `SlideTapTaskAppFactory.create()` using your service provider:

```python
from celery import Celery
from slidetap.config import Config
from slidetap.service_provider import create_task_service_provider
from slidetap.task import SlideTapTaskAppFactory

def make_celery(config: Optional[Config] = None) -> Celery:
    if config is None:
        config = Config()

    service_provider = create_task_service_provider(
        config=lambda: config,
        schema=YourSchema,
        metadata_export_interface=YourMetadataExportInterface,
        metadata_import_interface=YourMetadataImportInterface,
        image_export_interface=YourImageExportInterface,
        image_import_interface=YourImageImportInterface,
    )

    return SlideTapTaskAppFactory.create_celery_worker_app(
        name=__name__, config=config, service_provider=service_provider
    )
```

Also add any additional dependencies.

Next create a `task_app.py` file importing your app factory and creating the app:

```python
from your_task_app_factory import make_celery

celery_app = create_app()
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
