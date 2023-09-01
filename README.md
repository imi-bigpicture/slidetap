# *Slides*

Webapp for exporting pathology data using configurable sources for images and metadata.

This application has not been tested for clinical use and is not CE-marked.
It may therefore be used for research purposes only and comes without any guarantees.

## Overview

*Slides* is a webapp for creating research dataset of digital pathology data. It is designed to be able to interact with different sources of data, e.g. PACS for images and LIS for metadata, to enable curation of the data, and to output the data in desired formats.

## Requirements

- Python => 3.8
- Node >= 14

## Concepts

### Project

Data export is performed within a project. What data to include in the project is defined by some input selection, such as a file with case numbers. Different types of items can be added to a project:

- Samples, such as patients, specimens, blocks, and slides. These items can be related to each other, so that slides are created from blocks etc.
- Images, such as WSIs. Images are related to a sample, such as a slide, that they image.
- Annotations. Annotations are related to an image.
- Observations, such as reports. Observations are related to either a sample, and image, or an annotation.

All items (can) have:

- A name
- An unique identifier.
- A list of attributes
- A list of parents it relates to (such as blocks for a slide).
- A list of children it relates to (such as slides for a block).
- A schema that defines how the item can related to other items and what attributes it can have (see [Item schema](#item-schema))

There are serveral types of attribute types, corresponding to different value types. Similarliy to items, attributes are defined by [schemas](#attribute-schema).

## Usage

### Login

Login using your username and password according to used AuthService.

### Run a project

#### Create new project

- Click on `PROJECT` and `NEW PROJECT`.
- Name the project and click `CREATE`.
- Click on `Upload`. Select a input file to parse (dependent on implementation).
- Click on `UPLOAD`.

#### Project editing

- After submission metadata and images matching the project's job will be searched for.
- Click on `Select` to display the found items.
- The items are grouped by type as shown in the tab bar. Click on any type to show that type.
- Click the checkbox for each item to select or de-select to include the item in the export.

#### Project curation

TBD

#### Project export

- Start the export of metadata and images by clicking `Start`. A summary of what will be exported is shown. Click `START` to start the export.
- Click `Progress` to show the export progress.
- Click `Validate` to validate that the exported data is correct.

#### Project submission

- Click `Submit` to submit the project to the outbox. A summary of what will be submitted is shown. Click `SUBMIT` to confirm the submission.

## Implementation concepts

A Slides application is built up using varios components, some that are generic, some that are specific to the type of dataset to produce, and some that are specific to the use environment. The components that are specific are:

- A schema that defines the structure of the metadata to produce.

- Metadata and image importers that can import metadata and images into the specified schema structure.

- Metadata and image exporters that can export metadata and images in the dataset specific formats.

- Authentication service that authenticates users.

### Schema

A schema describes the structure of metadata and images, and is composed of item schemas, describing the structure and relation of for example samples and images, and attribute schemas, describing the structure of attributes assigned to items.

#### Item schema

A item schema can be of four types:

- Sample schema: Describing a sample, such as a patient, specimen, block, or slide, defining how a sample relates to other samples (e.g. sampled from) and what attributes a sample can have (e.g. ´embedding medium´, ´staining´).

- Image schema: Describing an image, typically a WSI, with what sample types it can image and attributes the image can have.

- Annotation schema: Describing an annotation done on an image.

- Observation schema: Describing an observation done on either a sample, an image, or an annotation.

#### Attribute schema

An attribute schema describes an attribute, and can be of different type depending on the required value type:

- String attribute schema: Used for attributes that are represented by a string value.

- Numeric attribute schema: Used for attributes that are represented by a integer or float value.

- Measurement attribute schema: Used for attributes that are represented by a float value and a unit.

- Datetime attribute schema: Used for attributes that are represented by a time, date, or datetime value.

- Boolean attribute schema: Used for attributes that are represented by a boolean value.

- Code attribute schema: Used for attributes that are represented by a code (code, scheme, meaning) value.

- Object attribute schema: Use for attributes that in itself contain other attributes.

- List attribute schema: Used for attributes that are a list of attributes.

- Union attribute schema: Used for attributes that can be of two or more value types.

### Importers

Importers are responsible for taking metadata and images from other sources, such as a LIMS and/or a PACS, and organising it into the used schema.

#### Metadata importer

A metadata importer should implement the abstract methods defined in the MetadataImporter metaclass. The metadata importer is responsible for, given a input file, retreive the relevant metadata for the scope defined in the input.

#### Image importer

A image importer should implement the  abstract methods defined in the ImageImporter metaclass. The image importer is responsible for finding images related to the metadata given from the metadata importer and to make these images avaiable (e.g. download) for processing.

### Exporters

Exporters are responsible for taking curated metadata and images and formatting them into a specified output format.

#### Metadata exporter

A metadata exporter should implement the abstract methods defined in the MetadataExporter metaclass. The metadata exporter is responsible for serializing the metadata into the specified output format, for example json or xml.

#### Image exporter

A image exporter should implement the abstract methods defined in the ImageExporter metaclass. The metadata exporter is responsible processing the image and produce images and metadata in the specified output format.

### Create application

The backend application is created using the `Create()`-method of the [`SlidesAppFactory`](/slides/slides/slides.py)-class. Create a .py-file with a `create_app()`-method calling this method using your implementations as parameters:

```python
from slides import SlidesAppFactory
from slides.services import JwtLoginService

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
    return SlidesAppFactory.create(
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

A simple example application, located in `slides\apps\example` is provided for demonstration and testing. This can be run with the provided `flask_run.bat` script or made into a docker image. The example application reads metadata from the uploaded json file (see `tests\test_data\input.json`).

See [Setup test data](#setup-test-data) for how to download the needed test images.

## Deployment

### Requirements

- An site-specific implementation of the components outlined in [Implementation concepts](#implementation-concepts).
- Docker (see [SETUP_DOCKER.md](SETUP_DOCKER.md))
- SSL cert for webserver.

### Setup environment

Configure the application environment by creating an .env-file:

- SLIDES_SERVERNAME: Domain name to webserver.
- SLIDES_PORT: Port for webserver.
- SLIDES_SSL_CERTIFICATE_FOLDER: Path to folder with certificate (cert.pem) and private key (privkey.pem) for SSL.
- SLIDES_SSL_CERTIFICATE: Name of certificate file.
- SLIDES_SSL_CERTIFICATE_KEY: Name of private key file.
- SLIDES_APIPORT: The port for the backend server.
- SLIDES_STORAGE: Folder to store data.
- SLIDES_KEEPALIVE: Interval in seconds for client to send keepalive.
- SLIDES_ENFORCE_HTTPS: If to only allow HTTPS connections.
- SLIDES_APP_CREATOR: Path to .py-file with create_app()-method.

```bash
SLIDES_SERVERNAME=server_hostname
SLIDES_PORT=3000
SLIDES_SSL_CERTIFICATE_FOLDER=path_to_certs
SLIDES_SSL_CERTIFICATE=cert.pem
SLIDES_SSL_CERTIFICATE_KEY=privkey.pem
SLIDES_APIPORT=8000
SLIDES_STORAGE=path_to_storage
SLIDES_KEEPALIVE=1800
SLIDES_ENFORCE_HTTPS=true
SLIDES_APP_CREATOR=path_to_create_app_file
```

Include other environment variables needed for your implementations.

### Build and run containers

```console
sudo docker-compose up
```

### Using webclient

Navigate to <https://$SLIDES_SERVERNAME:$SLIDES_PORT>.

## Development

### Setup

First install poetry according to [instructions](https://python-poetry.org/docs/).

Then run in a shell:

```console
> cd slides
> poetry install
```

### Configuration of application

Open the flask_run.bat file and configure the application similar to deployment.

### Configuration of frontend

Open the `package.json` set the proxy to the host configured for the flask.

### To run webserver

```console
> cd slides
> poetry run flask_run.bat
```

### Starting webclient

Run in a shell:

```console
> cd slides_client
> npm_run.bat
```

A browser window with the client will open automatically.

### Setup test data

To run the integration test, you need to place two wsi images (for example [CMU-1-SMALL-REGION.SVS](https://cytomine.com/collection/cmu-1/cmu-1-small-region-svs)) in the `tests\test_data\Image 1` and `Image 2` folders, named `Image 1.svs` and `Image 2.svs`.

### To run test

```console
> cd slides
> poetry run pytest
```
