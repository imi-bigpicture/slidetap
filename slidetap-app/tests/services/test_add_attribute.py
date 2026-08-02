#    Copyright 2024 SECTRA AB
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

"""Tests that adding an attribute keeps the mapping it was created with.

Mappers run before the attribute is inserted, so the mapping item set by
`MapperService` has to survive the insert. Without it the client cannot show
which mapper and expression produced the mapped value.
"""

from uuid import UUID, uuid4

import pytest

from slidetap.model import Code, CodeAttribute
from slidetap.model.schema.attribute_schema import CodeAttributeSchema
from slidetap.services import DatabaseService


@pytest.fixture()
def code_attribute_schema() -> CodeAttributeSchema:
    return CodeAttributeSchema(
        uid=uuid4(),
        tag="code",
        name="code",
        display_name="Code",
        optional=False,
        read_only=False,
        display_in_table=True,
    )


@pytest.mark.integration
class TestAddAttribute:
    def test_keeps_mapping_item_uid(
        self,
        sqlite_database_service: DatabaseService,
        code_attribute_schema: CodeAttributeSchema,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            mapping_uid = sqlite_database_service.add_mapping(
                session, mapper_uid, "^mappable$", code_attribute
            ).uid
            mapped_attribute = CodeAttribute(
                uid=uuid4(),
                schema_uid=code_attribute_schema.uid,
                mappable_value="mappable",
                mapped_value=Code(code="code", scheme="scheme", meaning="meaning"),
                mapping_item_uid=mapping_uid,
            )

            # Act
            added_attribute = sqlite_database_service.add_attribute(
                session, mapped_attribute, code_attribute_schema
            )
            added_uid = added_attribute.uid

        # Assert
        with sqlite_database_service.get_session() as session:
            stored_attribute = sqlite_database_service.get_attribute(session, added_uid)

            assert stored_attribute.model.mapping_item_uid == mapping_uid
