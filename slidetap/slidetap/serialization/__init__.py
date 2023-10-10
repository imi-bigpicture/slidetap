"""Module containing models for serialization of entities for web client."""

from slidetap.serialization.dzi import DziModel
from slidetap.serialization.item import (
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
from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.project import ProjectModel, ProjectSimplifiedModel
from slidetap.serialization.common import AttributeSimplifiedModel
from slidetap.serialization.mapper import (
    MappingModel,
    MapperModel,
    MapperSimplifiedModel,
    MappingItemModel,
)
from slidetap.serialization.schema import AttributeSchemaModel
from slidetap.serialization.basic_auth import BasicAuthModel
