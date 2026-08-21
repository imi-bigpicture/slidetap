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

"""Tests for what a remap leaves in the database (issue #64).

Re-applying mappers to an item already in the database has to persist what it
mapped. Only a root attribute is a row of its own: an attribute nested inside
an object, list or union attribute is JSON inside that one, so what a mapping
makes of it is the holding attribute's mapped value — and the imported value
stays what the import said, as it does everywhere else.

Runs against a real SQLite database, since the defect these cover is one of
what SQLAlchemy emits, which a mocked database cannot show.
"""

from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from sqlalchemy.orm import Session

from slidetap.model import (
    Code,
    CodeAttribute,
    CodeAttributeSchema,
    ListAttribute,
    ListAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)
from slidetap.services.mapper_service import MapperService

MAPPED_CODE = Code(code="87697008", scheme="SCT", meaning="Punch biopsy")
"""What the mapping puts in place of the wording the laboratory recorded."""

WHOLE_MAPPED_CODE = Code(code="65801008", scheme="SCT", meaning="Excision")
"""What a mapping of the holding attribute as a whole gives it to hold."""


@pytest.fixture()
def child_schema() -> CodeAttributeSchema:
    """The nested attribute the mapper maps."""
    return CodeAttributeSchema(
        uid=uuid4(),
        tag="diagnose",
        name="diagnose",
        display_name="Diagnose",
        optional=False,
        read_only=False,
    )


@pytest.fixture()
def object_schema(child_schema: CodeAttributeSchema) -> ObjectAttributeSchema:
    """The root attribute the nested one is written inside."""
    return ObjectAttributeSchema(
        uid=uuid4(),
        tag="statement",
        name="statement",
        display_name="Statement",
        optional=False,
        read_only=False,
        display_attributes_in_parent=False,
        display_value_tags=["diagnose"],
        attributes={"diagnose": child_schema},
    )


@pytest.fixture()
def list_schema(child_schema: CodeAttributeSchema) -> ListAttributeSchema:
    """The same, for the list-shaped root."""
    return ListAttributeSchema(
        uid=uuid4(),
        tag="diagnoses",
        name="diagnoses",
        display_name="Diagnoses",
        optional=False,
        read_only=False,
        display_attributes_in_parent=False,
        attribute=child_schema,
    )


@pytest.fixture()
def union_schema(child_schema: CodeAttributeSchema) -> UnionAttributeSchema:
    """The same, for the union-shaped root."""
    return UnionAttributeSchema(
        uid=uuid4(),
        tag="finding",
        name="finding",
        display_name="Finding",
        optional=False,
        read_only=False,
        attributes=(child_schema,),
    )


@pytest.fixture()
def schema_service(
    decoy: Decoy,
    child_schema: CodeAttributeSchema,
    object_schema: ObjectAttributeSchema,
    list_schema: ListAttributeSchema,
    union_schema: UnionAttributeSchema,
) -> SchemaService:
    service = decoy.mock(cls=SchemaService)
    for schema in (child_schema, object_schema, list_schema, union_schema):
        decoy.when(service.get_any_attribute(schema.uid)).then_return(schema)
        decoy.when(service.get_attribute(schema.uid)).then_return(schema)
    return service


@pytest.fixture()
def validation_service(
    schema_service: SchemaService, sqlite_database_service: DatabaseService
) -> ValidationService:
    """Real, not a mock: what a remap leaves in `valid` is part of what these
    tests are about."""
    return ValidationService(schema_service, sqlite_database_service)


@pytest.fixture()
def review_service(decoy: Decoy) -> ReviewService:
    return decoy.mock(cls=ReviewService)


@pytest.fixture()
def attribute_service(
    schema_service: SchemaService,
    validation_service: ValidationService,
    sqlite_database_service: DatabaseService,
    review_service: ReviewService,
) -> AttributeService:
    return AttributeService(
        schema_service, validation_service, sqlite_database_service, review_service
    )


@pytest.fixture()
def mapper_service(
    attribute_service: AttributeService,
    validation_service: ValidationService,
    schema_service: SchemaService,
    sqlite_database_service: DatabaseService,
    review_service: ReviewService,
) -> MapperService:
    return MapperService(
        attribute_service=attribute_service,
        validation_service=validation_service,
        schema_service=schema_service,
        database_service=sqlite_database_service,
        review_service=review_service,
    )


def _add_mapper(
    database_service: DatabaseService,
    session: Session,
    child_schema: CodeAttributeSchema,
    root_schema_uid: UUID,
    expression: str = "^Hudstans$",
) -> tuple[UUID, UUID]:
    """A mapper for the nested attribute, rooted at the attribute that holds
    it, with one mapping. Returns the mapper and mapping item uids."""
    mapper = database_service.add_mapper(
        session, "diagnose", child_schema.uid, root_schema_uid
    )
    session.flush()
    mapping = database_service.add_mapping(
        session,
        mapper.uid,
        expression,
        CodeAttribute(
            uid=uuid4(), schema_uid=child_schema.uid, original_value=MAPPED_CODE
        ),
    )
    session.flush()
    return mapper.uid, mapping.uid


def _remap(
    mapper_service: MapperService,
    database_service: DatabaseService,
    attribute_uid: UUID,
    mapper_uid: UUID,
) -> None:
    """Re-apply the mapper to the stored attribute, in a session of its own,
    as a request would."""
    with database_service.get_session() as session:
        mapper_service._remap_one_attribute(
            session,
            database_service.get_attribute(session, attribute_uid),
            [database_service.get_mapper(session, mapper_uid)],
        )
        session.commit()


@pytest.mark.integration
class TestNestedRemapIsPersisted:
    def test_value_mapped_inside_an_object_survives_the_session(
        self,
        sqlite_database_service: DatabaseService,
        mapper_service: MapperService,
        validation_service: ValidationService,
        child_schema: CodeAttributeSchema,
        object_schema: ObjectAttributeSchema,
    ):
        """The defect in #64: the mapped value was written to an in-memory copy
        only, so a later read — an export, say — found nothing there."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            mapper_uid, mapping_uid = _add_mapper(
                sqlite_database_service, session, child_schema, object_schema.uid
            )
            attribute = ObjectAttribute(
                uid=uuid4(),
                schema_uid=object_schema.uid,
                original_value={
                    "diagnose": CodeAttribute(
                        uid=uuid4(),
                        schema_uid=child_schema.uid,
                        mappable_value="Hudstans",
                    )
                },
            )
            attribute_uid = sqlite_database_service.add_attribute(
                session, attribute, object_schema
            ).uid
            session.commit()

        # Act
        _remap(mapper_service, sqlite_database_service, attribute_uid, mapper_uid)

        # Assert
        with sqlite_database_service.get_session() as session:
            reloaded = sqlite_database_service.get_attribute(session, attribute_uid)
            child = reloaded.model.value["diagnose"]
            assert child.mapped_value == MAPPED_CODE
            assert child.mapping_item_uid == mapping_uid
            # The imported value is what the import said, and stays so: the
            # mapping is in the mapped value, as it is for any attribute.
            assert reloaded.model.original_value["diagnose"].mapped_value is None
            # What the remap concluded about the attribute has to hold for what
            # it saved: validating the stored state again says the same thing.
            assert validation_service.validate_attribute(reloaded, session)

    def test_value_mapped_inside_a_list_survives_the_session(
        self,
        sqlite_database_service: DatabaseService,
        mapper_service: MapperService,
        child_schema: CodeAttributeSchema,
        list_schema: ListAttributeSchema,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            mapper_uid, mapping_uid = _add_mapper(
                sqlite_database_service, session, child_schema, list_schema.uid
            )
            attribute = ListAttribute(
                uid=uuid4(),
                schema_uid=list_schema.uid,
                original_value=[
                    CodeAttribute(
                        uid=uuid4(),
                        schema_uid=child_schema.uid,
                        mappable_value="Hudstans",
                    )
                ],
            )
            attribute_uid = sqlite_database_service.add_attribute(
                session, attribute, list_schema
            ).uid
            session.commit()

        # Act
        _remap(mapper_service, sqlite_database_service, attribute_uid, mapper_uid)

        # Assert
        with sqlite_database_service.get_session() as session:
            reloaded = sqlite_database_service.get_attribute(session, attribute_uid)
            child = reloaded.model.value[0]
            assert child.mapped_value == MAPPED_CODE
            assert child.mapping_item_uid == mapping_uid

    def test_value_mapped_inside_a_union_survives_the_session(
        self,
        sqlite_database_service: DatabaseService,
        mapper_service: MapperService,
        child_schema: CodeAttributeSchema,
        union_schema: UnionAttributeSchema,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            mapper_uid, mapping_uid = _add_mapper(
                sqlite_database_service, session, child_schema, union_schema.uid
            )
            attribute = UnionAttribute(
                uid=uuid4(),
                schema_uid=union_schema.uid,
                original_value=CodeAttribute(
                    uid=uuid4(),
                    schema_uid=child_schema.uid,
                    mappable_value="Hudstans",
                ),
            )
            attribute_uid = sqlite_database_service.add_attribute(
                session, attribute, union_schema
            ).uid
            session.commit()

        # Act
        _remap(mapper_service, sqlite_database_service, attribute_uid, mapper_uid)

        # Assert
        with sqlite_database_service.get_session() as session:
            reloaded = sqlite_database_service.get_attribute(session, attribute_uid)
            child = reloaded.model.value
            assert child.mapped_value == MAPPED_CODE
            assert child.mapping_item_uid == mapping_uid

    def test_an_attribute_with_a_mappable_value_is_not_descended_into(
        self,
        sqlite_database_service: DatabaseService,
        mapper_service: MapperService,
        child_schema: CodeAttributeSchema,
        object_schema: ObjectAttributeSchema,
    ):
        """The rule the mapped value rests on: an attribute carrying a mappable
        value of its own is mapped as a whole, so its mapped value is what that
        mapping gave it and the attributes it holds are left out of mapping.
        Only that way can one column mean one thing.
        """
        # Arrange
        with sqlite_database_service.get_session() as session:
            nested_mapper_uid, nested_mapping_uid = _add_mapper(
                sqlite_database_service, session, child_schema, object_schema.uid
            )
            whole_mapper = sqlite_database_service.add_mapper(
                session, "statement", object_schema.uid, object_schema.uid
            )
            session.flush()
            whole_mapping = sqlite_database_service.add_mapping(
                session,
                whole_mapper.uid,
                "^Hudstans$",
                ObjectAttribute(
                    uid=uuid4(),
                    schema_uid=object_schema.uid,
                    original_value={
                        "diagnose": CodeAttribute(
                            uid=uuid4(),
                            schema_uid=child_schema.uid,
                            original_value=WHOLE_MAPPED_CODE,
                        )
                    },
                ),
            )
            session.flush()
            attribute = ObjectAttribute(
                uid=uuid4(),
                schema_uid=object_schema.uid,
                mappable_value="Hudstans",
                original_value={
                    "diagnose": CodeAttribute(
                        uid=uuid4(),
                        schema_uid=child_schema.uid,
                        mappable_value="Hudstans",
                    )
                },
            )
            attribute_uid = sqlite_database_service.add_attribute(
                session, attribute, object_schema
            ).uid
            whole_mapper_uid, whole_mapping_uid = whole_mapper.uid, whole_mapping.uid
            session.commit()

        # Act
        with sqlite_database_service.get_session() as session:
            mapper_service._remap_one_attribute(
                session,
                sqlite_database_service.get_attribute(session, attribute_uid),
                [
                    sqlite_database_service.get_mapper(session, mapper_uid)
                    for mapper_uid in (whole_mapper_uid, nested_mapper_uid)
                ],
            )
            session.commit()

        # Assert
        with sqlite_database_service.get_session() as session:
            reloaded = sqlite_database_service.get_attribute(session, attribute_uid)
            assert reloaded.mapping_item_uid == whole_mapping_uid
            assert reloaded.model.value["diagnose"].value == WHOLE_MAPPED_CODE
            # The attribute it was imported holding is left as it came, still
            # waiting for a mapping that mapping never looked for.
            assert reloaded.model.original_value["diagnose"].mapped_value is None
            assert (
                sqlite_database_service.get_mapping(session, nested_mapping_uid).hits
                == 0
            )

    def test_a_remap_that_maps_nothing_leaves_the_attribute_not_valid(
        self,
        sqlite_database_service: DatabaseService,
        mapper_service: MapperService,
        validation_service: ValidationService,
        child_schema: CodeAttributeSchema,
        object_schema: ObjectAttributeSchema,
    ):
        """The other half of #64: `valid` has to describe what was saved. A
        nested value no mapping matched is still waiting for one, and the
        attribute holding it is not valid."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            mapper_uid, _ = _add_mapper(
                sqlite_database_service,
                session,
                child_schema,
                object_schema.uid,
                expression="^Something else$",
            )
            attribute = ObjectAttribute(
                uid=uuid4(),
                schema_uid=object_schema.uid,
                original_value={
                    "diagnose": CodeAttribute(
                        uid=uuid4(),
                        schema_uid=child_schema.uid,
                        mappable_value="Hudstans",
                    )
                },
            )
            attribute_uid = sqlite_database_service.add_attribute(
                session, attribute, object_schema
            ).uid
            session.commit()

        # Act
        _remap(mapper_service, sqlite_database_service, attribute_uid, mapper_uid)

        # Assert
        with sqlite_database_service.get_session() as session:
            reloaded = sqlite_database_service.get_attribute(session, attribute_uid)
            assert reloaded.model.mapped_value is None
            assert reloaded.model.value["diagnose"].mapped_value is None
            assert not validation_service.validate_attribute(reloaded, session)
