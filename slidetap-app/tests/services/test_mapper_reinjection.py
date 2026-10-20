#    Copyright 2026 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""A mapping sheet injected again with what some expressions map to changed.

Against a real database: the attributes the changed mappings mapped are found
by the mapping items they name, nested in the attributes they are part of.
"""

import datetime
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from slidetap_example import ExampleSchema

from slidetap.external_interfaces import MapperInjectorInterface
from slidetap.model import (
    BatchCreate,
    Code,
    CodeAttribute,
    Dataset,
    ListAttribute,
    Mapper,
    MapperGroup,
    MappingItem,
    Project,
    Sample,
)
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ItemService,
    MapperService,
    ReviewService,
    SchemaService,
    TagService,
    ValidationService,
)


@pytest.fixture()
def schema_service(
    schema: ExampleSchema, schema_service_of: Callable[..., SchemaService]
) -> SchemaService:
    return schema_service_of(schema)


@pytest.fixture()
def validation_service(
    schema_service: SchemaService, stored_database_service: DatabaseService
) -> ValidationService:
    return ValidationService(schema_service, stored_database_service)


@pytest.fixture()
def review_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    stored_database_service: DatabaseService,
) -> ReviewService:
    return ReviewService(schema_service, validation_service, stored_database_service)


@pytest.fixture()
def attribute_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    review_service: ReviewService,
    stored_database_service: DatabaseService,
) -> AttributeService:
    return AttributeService(
        schema_service, validation_service, stored_database_service, review_service
    )


@pytest.fixture()
def mapper_service(
    attribute_service: AttributeService,
    schema_service: SchemaService,
    validation_service: ValidationService,
    review_service: ReviewService,
    stored_database_service: DatabaseService,
) -> MapperService:
    return MapperService(
        attribute_service,
        validation_service,
        schema_service,
        stored_database_service,
        review_service,
    )


@pytest.fixture()
def item_service(
    attribute_service: AttributeService,
    schema_service: SchemaService,
    validation_service: ValidationService,
    review_service: ReviewService,
    mapper_service: MapperService,
    stored_database_service: DatabaseService,
) -> ItemService:
    return ItemService(
        attribute_service,
        TagService(stored_database_service),
        mapper_service,
        schema_service,
        validation_service,
        stored_database_service,
        review_service,
    )


class SheetInjector(MapperInjectorInterface):
    """Injects one mapper with what each expression maps to."""

    def __init__(self, mapper: Mapper, codes: dict[str, str]):
        self._mapper = mapper
        self._codes = codes

    def inject(self):
        yield (
            MapperGroup(uid=uuid4(), name="group", default_enabled=True, mappers=[]),
            [
                (
                    self._mapper,
                    [
                        MappingItem(
                            uid=uuid4(),
                            mapper_uid=self._mapper.uid,
                            expression=expression,
                            attribute=stain(self._mapper.attribute_schema_uid, code),
                        )
                        for expression, code in self._codes.items()
                    ],
                )
            ],
        )


def stain(schema_uid: UUID, code: str) -> CodeAttribute:
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=schema_uid,
        original_value=Code(code=code, scheme="SCT", meaning=code),
    )


@pytest.mark.integration
class TestReinjectingASheet:
    @pytest.fixture()
    def batch(
        self, stored_database_service: DatabaseService, schema: ExampleSchema
    ) -> tuple[UUID, UUID]:
        """The dataset and batch of a project to add slides to."""
        dataset = Dataset(uid=uuid4(), name="dataset", schema_uid=schema.dataset.uid)
        project = Project(
            uid=uuid4(),
            name="project",
            root_schema_uid=schema.uid,
            schema_uid=schema.project.uid,
            dataset_uid=dataset.uid,
            created=datetime.datetime(2026, 1, 1),
        )
        with stored_database_service.get_session() as session:
            stored_database_service.add_dataset(session, dataset)
            stored_database_service.add_project(session, project)
            batch = stored_database_service.add_batch(
                session, BatchCreate(name="batch", project_uid=project.uid)
            )
            return dataset.uid, batch.uid

    @pytest.fixture()
    def mapper(self, mapper_service: MapperService, schema: ExampleSchema) -> Mapper:
        """A mapper of the stains nested in the staining of a slide."""
        staining = schema.slide.attributes["staining"]
        stain_uid = staining.attribute.uid  # type: ignore[attr-defined]
        return mapper_service.get_or_create_mapper("stain", stain_uid, staining.uid)

    @staticmethod
    def add_slide(
        item_service: ItemService,
        schema: ExampleSchema,
        batch: tuple[UUID, UUID],
        mapper: Mapper,
        stain_value: str,
    ) -> UUID:
        dataset_uid, batch_uid = batch
        nested = CodeAttribute(uid=uuid4(), schema_uid=mapper.attribute_schema_uid)
        nested.mappable_value = stain_value
        slide = Sample(
            uid=uuid4(),
            identifier=stain_value,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema.slide_schema_uid,
            attributes={
                "staining": ListAttribute(
                    uid=uuid4(),
                    schema_uid=mapper.root_attribute_schema_uid,
                    original_value=[nested],
                )
            },
        )
        return item_service.add(slide, [mapper.uid]).uid

    @staticmethod
    def stain_code(item_service: ItemService, slide_uid: UUID) -> str:
        staining = item_service.get(slide_uid).attributes["staining"]
        return staining.value[0].value.code  # type: ignore[index, union-attr]

    def test_what_a_changed_mapping_mapped_is_mapped_again(
        self,
        item_service: ItemService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        batch: tuple[UUID, UUID],
        mapper: Mapper,
    ):
        """A stain nested in the staining of a slide takes what the sheet now
        maps it to, and a stain of an unchanged mapping keeps its own."""
        # Arrange
        mapper_service._mapper_injector = SheetInjector(
            mapper, {"^HE$": "old-he", "^PAS$": "pas"}
        )
        mapper_service.inject_mappers()
        he = self.add_slide(item_service, schema, batch, mapper, "HE")
        pas = self.add_slide(item_service, schema, batch, mapper, "PAS")
        mapper_service._mapper_injector = SheetInjector(
            mapper, {"^HE$": "new-he", "^PAS$": "pas"}
        )

        # Act
        mapper_service.inject_mappers()

        # Assert
        assert self.stain_code(item_service, he) == "new-he"
        assert self.stain_code(item_service, pas) == "pas"

    def test_only_what_the_mappings_mapped_is_found(
        self,
        stored_database_service: DatabaseService,
        item_service: ItemService,
        mapper_service: MapperService,
        schema: ExampleSchema,
        batch: tuple[UUID, UUID],
        mapper: Mapper,
    ):
        # Arrange
        he_mapping = mapper_service.get_or_create_mapping(
            mapper.uid, "^HE$", stain(mapper.attribute_schema_uid, "he")
        )
        mapper_service.get_or_create_mapping(
            mapper.uid, "^PAS$", stain(mapper.attribute_schema_uid, "pas")
        )
        he = self.add_slide(item_service, schema, batch, mapper, "HE")
        self.add_slide(item_service, schema, batch, mapper, "PAS")
        self.add_slide(item_service, schema, batch, mapper, "unmapped")
        he_staining = item_service.get(he).attributes["staining"].uid

        # Act
        with stored_database_service.get_session() as session:
            found = stored_database_service.get_attribute_uids_mapped_by(
                session, mapper.root_attribute_schema_uid, [he_mapping.uid]
            )

        # Assert
        assert found == [he_staining]
