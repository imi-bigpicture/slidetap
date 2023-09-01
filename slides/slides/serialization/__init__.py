"""Module containing models for serialization of entities for web client."""

from slides.serialization.dzi import DziModel
from slides.serialization.item import (
    AnnotationModel,
    AnnotationSimplifiedModel,
    ImageModel,
    ImageSimplifiedModel,
    ObservationModel,
    ObservationSimplifiedModel,
    SampleModel,
    SampleSimplifiedModel,
    ItemModelFactory,
)
from slides.serialization.attribute import AttributeModel
from slides.serialization.project import ProjectModel, ProjectSimplifiedModel
from slides.serialization.common import AttributeSimplifiedModel
from slides.serialization.mapper import (
    MappingModel,
    MapperModel,
    MapperSimplifiedModel,
    MappingItemModel,
)
from slides.serialization.schema import AttributeSchemaModel
from slides.serialization.basic_auth import BasicAuthModel
