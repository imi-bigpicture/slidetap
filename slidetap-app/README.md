# _SlideTap_ back-end

The _SlideTap_ back-end is responsible for interacting with the database and provide services for handling metadata and images. The front-end communicates with the back-end using REST controllers. The application requires that several user-specific implementations are provided, see [Concepts](#concepts).

## Requirements

The back-end requires Python >=3.9. Other main dependencies are:

- Flask for serving controllers
- SqlAlchemy for database store. Using either sqllite or postgresql is supported.
- marshmallow for serializing items for the front-end
- wsidicomizer for reading WSIs

## Concepts

A SlideTap application is built up using varios components, some that are generic, some that are specific to the type of dataset to produce, and some that are specific to the user environment. The components that are specific are:

- A `Schema` defines what kind of `Samples`, `Images`, `Annotations`, and `Observations` that can be created, how they can be related, and what kind of `Attributes` they can have. _SlideTap_ can be configured to use different metadata schemas, but does not come with any defined `Schemas` (except for the example application). A suitable `Schema` must thus be created by the user.

- `MetadataImporter` and `ImageImporter` that can import metadata and images into the specified schema structure.

- `MetadataExporter` and `ImageExporter` that can export metadata and images in the dataset specific formats.

- An `AuthService` that authenticates users and a `LoginService` that logins users, and a `LoginController` that the front-end can use to login users.

These components must be created by the user, see [Example application](#Example application)

### Schema

A `Schema` describes the structure of metadata and images, and is composed of an `ProjectSchema`, one or more `ItemSchema`s, describing the structure and relation of for example samples and images, and `AttributeSchema`s, describing the structure of attributes assigned to a project and items.

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

### Importers

Importers are responsible for taking metadata and images from other sources, such as a LIMS and/or a PACS, and organising it into the used schema.

#### MetadataImporter

A metadata importer should implement the abstract methods defined in the MetadataImporter metaclass:

#### schema (property)

Should return the `Schema` that the imported metadata follows.

#### create_project (method)

Should create a new project.

#### search (method)

Should search for metadata for a project based on the supplied search criteria.

#### ImageImporter

A image importer should implement the abstract methods defined in the ImageImporter metaclass:

##### preprocess (method)

Should find images related to the exisint metadata in the project (e.g. slides samples),  make them avaiable (e.g. download if needed) and preprocess the image files for metadata.

### Exporters

Exporters are responsible for taking curated metadata and images and formatting them into a specified output format.

#### MetadataExporter

A metadata exporter should implement the abstract methods defined in the MetadataExporter metaclass. The metadata exporter is responsible for serializing the metadata into the specified output format, for example json or xml.

##### export (method)

Should serialize the metadata in a project to selected output format, e.g. json or xml.

##### preview_item (method)

Should produce a string that represents a preview of how an item will be serialized.

#### ImageExporter

A image exporter should implement the abstract methods defined in the ImageExporter metaclass:

##### export (method)

Should export all the images in the project to the specified output format (e.g. DICOM).

### AuthService

The `AuthService` is responsible for authentication user credentials.

### LoginService

The `LoginService` is responsible for setting tokens or similar needed to ensure that the user has access to the restricted controllers when logged in.

### LoginController

The `LoginController` is used so that the front-end can send requests to login and logout a user.

### Create application

The back-end application is created using the `Create()`-method of the [`SlideTapAppFactory`](/slidetap/slidetap/slidetap.py)-class. Create a .py-file with a `create_app()`-method calling this method using your implementations as parameters:

```python
from slidetap import SlideTapAppFactory
from slidetap.services import JwtLoginService

def create_app() -> Flask:
  if config is None:
        config = Config()
    login_service = JwtLoginService()
    auth_service = YourAuthServiceImplementation(...)
    login_controller = BasicAuthLoginController(auth_service, login_service)
    image_importer = YourImageImporterImplementation(...)
    image_exporter = YourImageExporterImplementation(...)
    metadata_importer = YourMetadataImporterImplementation(...)
    metadata_exporter = YourMetadataExporterImplementation(...)
    return SlideTapAppFactory.create(
        auth_service,
        login_service,
        login_controller,
        image_importer,
        image_exporter,
        metadata_importer,
        metadata_exporter,
        config,
    )
```

### Example application

A simple example application, located in `slidetap\apps\example` is provided for demonstration and testing. This can be run with the provided `flask_run.bat` script or made into a docker image. The example application reads metadata from the uploaded json file (see `tests\test_data\input.json`).

See [Setup test data](#setup-test-data) for how to download the needed test images.

## Development

This section assumes that the commands are issued in the `slidetap` subfolder.

### Setup

First install poetry according to [instructions](https://python-poetry.org/docs/).

Then run in a shell:

```console
> poetry install
```

### Configuration of application

Create an `.env`-file in the project folder setting the following environmental variables:

- FLASK_APP: Path to the `create_app` to use.
- FLASK_RUN_PORT: Port to run the flask application on.
- FLASK_DEBUG: If flask should be run in debug mode (enables reloading).
- SLIDETAP_SECRET_KEY: The secret key to use.
- SLIDETAP_WEBAPPURL: The url the front end is served at.
- SLIDETAP_STORAGE: Path to location were to store data.
- SLIDETAP_DBURI: URI for database storage.
- SLIDETAP_KEEPALIVE: Keepalive time in seconds.
- SLIDETAP_ENFORCE_HTTPS: If to enforce the use of https.

```env
FLASK_APP=slidetap/apps/example/app
FLASK_RUN_PORT=5001
FLASK_DEBUG=true
SLIDETAP_SECRET_KEY=DEVELOP
SLIDETAP_WEBAPPURL=http://localhost:13000
SLIDETAP_STORAGE=C:\temp\slidetap
SLIDETAP_DBURI=sqlite:///C:/temp/slidetap/db.sqlite
SLIDETAP_KEEPALIVE=1800
SLIDETAP_ENFORCE_HTTPS=false
```

### To run webserver

```console
> poetry run flask run --host=0.0.0.0
```

### Setup test data

To run the integration test, you need to place two wsi images (for example [CMU-1-SMALL-REGION.SVS](https://cytomine.com/collection/cmu-1/cmu-1-small-region-svs)) in the `tests\test_data\Image 1` and `Image 2` folders, named `Image 1.svs` and `Image 2.svs`.

### To run test

```console
> poetry run pytest
```
