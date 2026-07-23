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

"""Benchmark the mapper resolver (Nexus #46 / #56 follow-up).

Compares the pre-#46 linear regex scan (fetch every expression, `re.match`
each one per value) against the current resolver — an indexed exact-literal
lookup plus a scan of only the genuinely regex-shaped expressions — at
Diagnose-mapper scale (~6k exact keys + a few genuine regex keys).

Runs against a real SQLite database rather than an in-memory data structure:
since #56, the exact/regex split lives in the `mapping_item.literal` column
and the "index" is a database index seek, not a Python dict, so a real
database is the only way to measure it (and to keep the web/worker processes
reading one shared, always-current source instead of a per-process cache).

Run:  uv run python benchmarks/bench_mapper_resolver.py
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from slidetap.config import DatabaseConfig
from slidetap.database import Base
from slidetap.model import Code, CodeAttribute
from slidetap.services import DatabaseService
from slidetap.services.mapper_service import MapperService

N_EXACT = 6173
REGEX_KEYS = [".*resectie.*", "^HE[0-9]*", ".*biopt.*"]
N_LOOKUPS = 2000
WORKBOOK_ROWS = 30_000


def _attribute() -> CodeAttribute:
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=uuid4(),
        original_value=Code(code="code", scheme="scheme", meaning="meaning"),
    )


def build_database(directory: Path) -> tuple[DatabaseService, UUID]:
    uri = f"sqlite:///{directory / 'bench.db'}"
    Base.metadata.create_all(bind=create_engine(uri))
    database_service = DatabaseService(DatabaseConfig(uri, False))
    with database_service.get_session() as session:
        mapper = database_service.add_mapper(session, "bench-mapper", uuid4(), uuid4())
        mapper_uid = mapper.uid
        for i in range(N_EXACT):
            database_service.add_mapping(
                session, mapper_uid, f"^{100000 + i}$", _attribute()
            )
        for expression in REGEX_KEYS:
            database_service.add_mapping(session, mapper_uid, expression, _attribute())
    return database_service, mapper_uid


def old_linear_scan(
    database_service: DatabaseService, session: Session, mapper_uid: UUID, value: str
) -> str | None:
    return next(
        (
            expression
            for expression in database_service.get_mapper_expressions(
                session, mapper_uid
            )
            if MapperService.create_pattern(expression).match(value)
        ),
        None,
    )


def main() -> None:
    with TemporaryDirectory() as tmp:
        database_service, mapper_uid = build_database(Path(tmp))
        # A real MapperService, minus the collaborators `_resolve_expression`
        # never touches (attribute/validation/schema services, injector).
        mapper_service = MapperService(
            attribute_service=None,  # type: ignore[arg-type]
            validation_service=None,  # type: ignore[arg-type]
            schema_service=None,  # type: ignore[arg-type]
            database_service=database_service,
        )
        rng = random.Random(42)  # noqa: S311 - reproducible sampling, not cryptographic
        # Representative lookups: existing exact concept-ids (the common case).
        values = [str(100000 + rng.randrange(N_EXACT)) for _ in range(N_LOOKUPS)]

        MapperService.create_pattern.cache_clear()
        with database_service.get_session() as session:
            start = time.perf_counter()
            for value in values:
                old_linear_scan(database_service, session, mapper_uid, value)
            old_per = (time.perf_counter() - start) / len(values)

        MapperService.create_pattern.cache_clear()
        with database_service.get_session() as session:
            start = time.perf_counter()
            for value in values:
                mapper_service._resolve_expression(session, mapper_uid, value)
            new_per = (time.perf_counter() - start) / len(values)

        print(
            f"expressions: {N_EXACT + len(REGEX_KEYS)} "
            f"({N_EXACT} exact + {len(REGEX_KEYS)} regex), lookups: {len(values)}"
        )
        print(f"{'':<6}{'per value':>14}{'30k workbook':>16}")
        print(f"{'OLD':<6}{old_per * 1e3:>11.3f} ms{old_per * WORKBOOK_ROWS:>13.1f} s")
        print(f"{'NEW':<6}{new_per * 1e3:>11.3f} ms{new_per * WORKBOOK_ROWS:>13.3f} s")
        print(f"\nspeedup: {old_per / new_per:.0f}x")

        # Release the sqlite file handle before the TemporaryDirectory tries to
        # remove it (Windows keeps an open file locked).
        database_service._engine.dispose()


if __name__ == "__main__":
    main()
