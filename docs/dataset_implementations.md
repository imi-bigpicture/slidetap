---
title: Dataset implementations
layout: home
nav_order: 3
---

## Dataset implementations

To format a dataset according to your needs, you need to define a schema for the dataset as well as image and metadata exporters that can convert the curated images and metadata to the desired format

### Schema

A `Schema` defines what kind of `Samples`, `Images`, `Annotations`, and `Observations` that can be created, how they can be related, and what kind of `Attributes` they can have. _SlideTap_ can be configured to use different metadata schemas, but does not come with any defined `Schemas` (except for the example application). A suitable `Schema` must thus be created by the user. A `Schema` is composed a `ProjectSchema`, a `DatasetSchema`, one or more `ItemSchema`s, describing the structure and relation of for example samples and images, and `AttributeSchema`s, describing the structure of attributes assigned to a project and items. See `https://imi-bigpciture/slidetap/slidetapa-app/slidetap/apps/example/schema.py` for an example of a `Schema`.

#### ItemSchema

A `ItemSchema` can be of four types:

- `SampleSchema`: Describing a sample, such as a patient, specimen, block, or slide, defining how a sample relates to other samples (e.g. sampled from) and what attributes a sample can have (e.g. `embedding medium`, `staining`).

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

### MetadataExporter

A [`MetadataExporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/exporter/metadata_exporter.py) that can export the curated metadata in a project to a serialized format for storage.

### ImageExporter

An [`ImageExporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/exporter/image_exporter.py) that can export the images in a project to storage in required format.
