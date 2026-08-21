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

"""Tests for the mapper resolver fast path (Nexus #46).

Covers `MapperService._resolve_expression`: combining the DB's exact-literal
lookup (`DatabaseService.get_literal_mapping_candidate`) with the small set of
genuinely regex-shaped expressions (`get_regex_mapping_items`) to pick the
same winner a full hits-ordered linear scan would, plus the newline fallback
that keeps that guarantee exact. The exact/regex split itself now lives in
`DatabaseMappingItem.literal` (see `tests/database/test_mapper.py`) rather
than a per-process cache, so there is nothing here to invalidate on mutation
— every resolve reads current DB state directly.
"""

from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from slidetap_example import ExampleSchema
from sqlalchemy import select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseMapper,
    DatabaseMappingItem,
    DatabaseUnmappedValue,
)
from slidetap.model import Code, CodeAttribute, MappingItem, StringAttribute
from slidetap.model.mapper import MappingItemCreate
from slidetap.model.schema.attribute_schema import CodeAttributeSchema
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ReviewService,
    SchemaService,
    ValidationService,
)
from slidetap.services.mapper_service import MapperService


def _mapping_item(
    mapper_uid: UUID, expression: str, hits: int = 0
) -> DatabaseMappingItem:
    item = DatabaseMappingItem(
        mapper_uid, expression, StringAttribute(uid=uuid4(), schema_uid=uuid4())
    )
    item.hits = hits
    return item


@pytest.fixture()
def attribute_service(decoy: Decoy) -> AttributeService:
    return decoy.mock(cls=AttributeService)


@pytest.fixture()
def validation_service(decoy: Decoy) -> ValidationService:
    return decoy.mock(cls=ValidationService)


@pytest.fixture()
def schema_service(decoy: Decoy) -> SchemaService:
    return decoy.mock(cls=SchemaService)


@pytest.fixture()
def database_service(decoy: Decoy) -> DatabaseService:
    return decoy.mock(cls=DatabaseService)


@pytest.fixture()
def review_service(decoy: Decoy) -> ReviewService:
    return decoy.mock(cls=ReviewService)


@pytest.fixture()
def mapper_service(
    attribute_service: AttributeService,
    validation_service: ValidationService,
    schema_service: SchemaService,
    database_service: DatabaseService,
    review_service: ReviewService,
) -> MapperService:
    return MapperService(
        attribute_service=attribute_service,
        validation_service=validation_service,
        schema_service=schema_service,
        database_service=database_service,
        review_service=review_service,
    )


@pytest.mark.unittest
class TestResolveExpression:
    def test_exact_candidate_wins_with_no_regex_overlap(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_literal_mapping_candidate(session, mapper_uid, "A")
        ).then_return(_mapping_item(mapper_uid, "^A$"))
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([])

        assert mapper_service._resolve_expression(session, mapper_uid, "A") == "^A$"

    def test_no_candidates_returns_none(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_literal_mapping_candidate(
                session, mapper_uid, "does-not-exist"
            )
        ).then_return(None)
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([_mapping_item(mapper_uid, ".*resectie.*")])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "does-not-exist")
            is None
        )

    def test_regex_only_match(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_literal_mapping_candidate(session, mapper_uid, "male")
        ).then_return(None)
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return(
            [
                _mapping_item(mapper_uid, ".*male.*"),
                _mapping_item(mapper_uid, ".*bovine.*"),
            ]
        )

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "male")
            == ".*male.*"
        )

    def test_non_matching_regex_candidates_are_ignored(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        # `get_regex_mapping_items` returns every regex-shaped expression for
        # the mapper; the resolver still has to re.match each one itself.
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_literal_mapping_candidate(session, mapper_uid, "7185")
        ).then_return(_mapping_item(mapper_uid, "^7185$"))
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([_mapping_item(mapper_uid, ".*zzz.*")])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "7185") == "^7185$"
        )

    def test_higher_hits_regex_beats_lower_hits_exact(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        """Winner is picked by (hits desc, uid) across exact and regex
        candidates together — the same ordering a full linear scan would use —
        so a heavily-hit regex key can still beat a fresh exact key."""
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_literal_mapping_candidate(
                session, mapper_uid, "71854001"
            )
        ).then_return(_mapping_item(mapper_uid, "^71854001$", hits=1))
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([_mapping_item(mapper_uid, ".*854.*", hits=100)])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "71854001")
            == ".*854.*"
        )

    def test_tie_break_by_uid(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        exact = _mapping_item(mapper_uid, "^71854001$", hits=5)
        regex = _mapping_item(mapper_uid, ".*854.*", hits=5)
        # Force a deterministic uid ordering regardless of generation order.
        exact.uid, regex.uid = sorted([exact.uid, regex.uid])
        decoy.when(
            database_service.get_literal_mapping_candidate(
                session, mapper_uid, "71854001"
            )
        ).then_return(exact)
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([regex])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "71854001")
            == exact.expression
        )

    def test_trailing_newline_value_uses_linear_scan(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        """`^X$` matches `"X\\n"` under re.match (`$` matches before a trailing
        newline), which the exact string-equality lookup on `literal` would
        miss. A newline-bearing value is routed through the authoritative
        linear scan instead, independent of the exact/regex queries."""
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_mapper_expressions(session, mapper_uid)
        ).then_return(["^71854001$"])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "71854001\n")
            == "^71854001$"
        )


@pytest.mark.unittest
class TestGetMatchingExpressionSingle:
    def test_single_expression_branch_matches(
        self, decoy: Decoy, mapper_service: MapperService
    ):
        session = decoy.mock(cls=Session)
        mapper = decoy.mock(cls=DatabaseMapper)
        attribute = decoy.mock(cls=DatabaseAttribute)
        decoy.when(attribute.mappable_value).then_return("HE")

        assert (
            mapper_service._get_matching_expression(session, mapper, attribute, "^HE$")
            == "^HE$"
        )
        assert (
            mapper_service._get_matching_expression(session, mapper, attribute, "^XX$")
            is None
        )

    def test_none_value_returns_none(self, decoy: Decoy, mapper_service: MapperService):
        session = decoy.mock(cls=Session)
        mapper = decoy.mock(cls=DatabaseMapper)
        attribute = decoy.mock(cls=DatabaseAttribute)
        decoy.when(attribute.mappable_value).then_return(None)

        assert (
            mapper_service._get_matching_expression(session, mapper, attribute, None)
            is None
        )


@pytest.fixture()
def writer(sqlite_database_service: DatabaseService) -> MapperService:
    return MapperService(
        None,
        None,
        None,
        sqlite_database_service,  # type: ignore[arg-type]
        None,
    )


@pytest.fixture()
def reader(sqlite_database_service: DatabaseService) -> MapperService:
    return MapperService(
        None,
        None,
        None,
        sqlite_database_service,  # type: ignore[arg-type]
        None,
    )


@pytest.mark.integration
class TestResolverMatchesLinearScan:
    """`_resolve_expression` must always pick the same winner the
    authoritative `_linear_scan_expression` would, for every value — not just
    the hand-picked cases in `TestResolveExpression` above, which mock the DB
    queries and never touch real literal classification. Runs against a real
    SQLite database, per erikogabrielsson's review on PR #56.
    """

    def test_resolver_matches_linear_scan_for_adversarial_values(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
        writer: MapperService,
    ):
        expressions = [
            ("^A$", 1),
            ("A$", 5),  # collides with "^A$" on the literal "A"
            ("^71854001$", 3),
            (".*854.*", 100),  # outranks "^71854001$"; also matches "7185400"
            ("^$", 2),  # matches only the empty string
            ("^HE[0-9]*", 0),
            ("^Female$", 4),  # isolated: no regex-shaped expression matches it
        ]
        values = [
            "A",  # colliding literals; the higher-hit row must win
            "71854001",  # a high-hit regex outranks a low-hit exact key
            "",  # only "^$" matches
            "7185400",  # near-miss on the exact key, still hits the regex
            "Female\n",  # newline guard: only a linear scan sees this match
        ]

        with sqlite_database_service.get_session() as session:
            for expression, hits in expressions:
                item = sqlite_database_service.add_mapping(
                    session, mapper_uid, expression, code_attribute
                )
                item.hits = hits

            for value in values:
                assert writer._resolve_expression(
                    session, mapper_uid, value
                ) == writer._linear_scan_expression(session, mapper_uid, value), value


@pytest.mark.integration
class TestResolutionReflectsMutations:
    """Resolution must reflect mutations made by a different `MapperService`
    instance immediately, with nothing to invalidate: the exact/regex split
    lives in the `mapping_item.literal` column, not a per-process cache. Each
    test uses two independent `MapperService` instances sharing one database,
    simulating the web process and a Procrastinate worker, per
    erikogabrielsson's review on PR #56.
    """

    def test_create_mapping_is_visible_to_another_instance(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
        writer: MapperService,
        reader: MapperService,
    ):
        writer.create_mapping(
            MappingItemCreate(
                mapper_uid=mapper_uid,
                expression="^71854001$",
                attribute=code_attribute,
            )
        )

        with sqlite_database_service.get_session() as session:
            assert (
                reader._resolve_expression(session, mapper_uid, "71854001")
                == "^71854001$"
            )

    def test_update_mapping_changes_what_resolves(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
        writer: MapperService,
        reader: MapperService,
    ):
        created = writer.create_mapping(
            MappingItemCreate(
                mapper_uid=mapper_uid,
                expression="^71854001$",
                attribute=code_attribute,
            )
        )

        writer.update_mapping(
            MappingItem(
                uid=created.uid,
                mapper_uid=mapper_uid,
                expression="^Male$",
                attribute=code_attribute,
                hits=created.hits,
            )
        )

        with sqlite_database_service.get_session() as session:
            assert reader._resolve_expression(session, mapper_uid, "Male") == "^Male$"
            assert reader._resolve_expression(session, mapper_uid, "71854001") is None

    def test_get_or_create_mapper_renames_rather_than_duplicating(
        self,
        sqlite_database_service: DatabaseService,
        writer: MapperService,
    ):
        """The mapper table is unique on the schema pair, not the name. Asking
        for a mapper whose name has changed since it was injected has to find
        the existing row and rename it — inserting a second one for the same
        pair fails the constraint, taking down every request that builds a
        MapperService."""
        # Arrange
        attribute_schema_uid, root_attribute_schema_uid = uuid4(), uuid4()
        with sqlite_database_service.get_session() as session:
            original = sqlite_database_service.add_mapper(
                session, "old-name", attribute_schema_uid, root_attribute_schema_uid
            )
            original_uid = original.uid

        # Act
        mapper = writer.get_or_create_mapper(
            "new-name", attribute_schema_uid, root_attribute_schema_uid
        )

        # Assert
        assert mapper.uid == original_uid
        assert mapper.name == "new-name"

    def test_delete_mapping_removes_what_resolves(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
        writer: MapperService,
        reader: MapperService,
    ):
        created = writer.create_mapping(
            MappingItemCreate(
                mapper_uid=mapper_uid,
                expression="^71854001$",
                attribute=code_attribute,
            )
        )

        writer.delete_mapping(created.uid)

        with sqlite_database_service.get_session() as session:
            assert reader._resolve_expression(session, mapper_uid, "71854001") is None


@pytest.mark.integration
class TestDeletingAMappingPutsItsValuesBackToWaiting:
    """Covers `_clear_mapping_from_attributes`, which frees attributes of a
    mapping by assigning their columns so that a locked one can be freed too.
    That goes around the update which would otherwise record that the value is
    waiting for a mapping again, so it records for itself.
    """

    @pytest.fixture()
    def mappable_value(self) -> str:
        return "Hudstans"

    @pytest.fixture()
    def code_attribute_schema(self) -> CodeAttributeSchema:
        return CodeAttributeSchema(
            uid=uuid4(),
            tag="code",
            name="code",
            display_name="Code",
            optional=False,
            read_only=False,
        )

    def test_the_value_is_recorded_as_waiting_again(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
        code_attribute_schema: CodeAttributeSchema,
        mappable_value: str,
        writer: MapperService,
    ):
        # Arrange
        with sqlite_database_service.get_session() as session:
            mapping_uid = sqlite_database_service.add_mapping(
                session, mapper_uid, f"^{mappable_value}$", code_attribute
            ).uid
            attribute_uid = sqlite_database_service.add_attribute(
                session,
                CodeAttribute(
                    uid=uuid4(),
                    schema_uid=code_attribute_schema.uid,
                    mappable_value=mappable_value,
                    mapped_value=Code(code="code", scheme="scheme", meaning="meaning"),
                    mapping_item_uid=mapping_uid,
                ),
                code_attribute_schema,
            ).uid
        with sqlite_database_service.get_session() as session:
            assert (
                session.scalars(
                    select(DatabaseUnmappedValue).where(
                        DatabaseUnmappedValue.root_attribute_uid == attribute_uid
                    )
                ).all()
                == []
            ), "mapped to begin with, so nothing is waiting"

        # Act
        writer.delete_mapping(mapping_uid)

        # Assert
        with sqlite_database_service.get_session() as session:
            recorded = session.scalars(
                select(DatabaseUnmappedValue).where(
                    DatabaseUnmappedValue.root_attribute_uid == attribute_uid
                )
            ).all()
            assert [row.value for row in recorded] == [mappable_value]


@pytest.mark.unittest
class TestMapperSchemaUids:
    """Asking for a mapper under schema uids that have been regenerated.

    A model's attribute uids are regenerated with the model, so a mapper that
    has been injected before is asked for under uids the stored one has never
    seen after any revision touching the attribute it maps. Selecting a mapper
    goes by those uids and nothing else, so a mapper left on the old ones is
    stranded: it is in the mapper group, it has its mappings, and it resolves
    nothing.
    """

    @pytest.fixture()
    def schema_service(self) -> SchemaService:
        return SchemaService(ExampleSchema())

    @pytest.fixture()
    def injector(
        self,
        schema_service: SchemaService,
        sqlite_database_service: DatabaseService,
    ) -> MapperService:
        return MapperService(
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            schema_service,
            sqlite_database_service,
            None,  # type: ignore[arg-type]
        )

    @staticmethod
    def _attribute_schema_uids(schema_service: SchemaService) -> tuple[UUID, UUID]:
        uids = list(schema_service.attributes)
        assert len(uids) >= 2, "the example model has attributes to map"
        return uids[0], uids[1]

    def test_mapper_is_moved_to_regenerated_schema_uids(
        self,
        schema_service: SchemaService,
        sqlite_database_service: DatabaseService,
        injector: MapperService,
    ):
        # Arrange
        # The uids of a revision of the model that is no longer loaded.
        in_model, _ = self._attribute_schema_uids(schema_service)
        with sqlite_database_service.get_session() as session:
            existing_uid = sqlite_database_service.add_mapper(
                session, "diagnose", uuid4(), uuid4()
            ).uid

        # Act
        mapper = injector.get_or_create_mapper("diagnose", in_model, in_model)

        # Assert
        assert mapper.uid == existing_uid
        assert mapper.attribute_schema_uid == in_model
        assert mapper.root_attribute_schema_uid == in_model

    def test_moved_mapper_keeps_its_mappings(
        self,
        schema_service: SchemaService,
        sqlite_database_service: DatabaseService,
        injector: MapperService,
    ):
        # Arrange
        in_model, _ = self._attribute_schema_uids(schema_service)
        with sqlite_database_service.get_session() as session:
            existing_uid = sqlite_database_service.add_mapper(
                session, "diagnose", uuid4(), uuid4()
            ).uid
            mapping = sqlite_database_service.add_mapping(
                session,
                existing_uid,
                "^C50.9$",
                StringAttribute(uid=uuid4(), schema_uid=uuid4()),
            )
            mapping.hits = 98
            mapping_uid = mapping.uid

        # Act
        injector.get_or_create_mapper("diagnose", in_model, in_model)

        # Assert
        with sqlite_database_service.get_session() as session:
            mappings = session.scalars(
                select(DatabaseMappingItem).where(
                    DatabaseMappingItem.mapper_uid == existing_uid
                )
            ).all()
            assert [item.uid for item in mappings] == [mapping_uid]
            assert mappings[0].hits == 98

    def test_name_taken_by_a_mapper_in_the_model_is_refused(
        self,
        schema_service: SchemaService,
        sqlite_database_service: DatabaseService,
        injector: MapperService,
    ):
        # Arrange
        # Both attributes are in the loaded model, so neither mapper is a
        # regenerated version of the other: the name is claimed twice.
        in_model, also_in_model = self._attribute_schema_uids(schema_service)
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_mapper(session, "diagnose", in_model, in_model)

        # Act & Assert
        with pytest.raises(ValueError, match="diagnose"):
            injector.get_or_create_mapper("diagnose", also_in_model, also_in_model)
