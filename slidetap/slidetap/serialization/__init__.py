"""Module containing models for serialization of entities for web client."""

from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.basic_auth import BasicAuthModel
from slidetap.serialization.common import AttributeSimplifiedModel
from slidetap.serialization.dzi import DziModel
from slidetap.serialization.item import (
    AnnotationDetailsModel,
    AnnotationModel,
    ImageDetailsModel,
    ImageModel,
    ItemModelFactory,
    ObservationDetailsModel,
    ObservationModel,
    SampleDetailsModel,
    SampleModel,
)
from slidetap.serialization.mapper import (
    MapperModel,
    MapperSimplifiedModel,
    MappingItemModel,
)
from slidetap.serialization.project import ProjectModel, ProjectSimplifiedModel
from slidetap.serialization.schema import AttributeSchemaModel
