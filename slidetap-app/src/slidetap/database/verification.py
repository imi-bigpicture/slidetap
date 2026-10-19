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

"""Rounds of units drawn from a batch for verification, and what was decided."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from slidetap.database.db import Base
from slidetap.database.item import DatabaseItem
from slidetap.database.project import DatabaseBatch
from slidetap.database.types import LoadingJson
from slidetap.model.verification import VerificationPopulation, VerificationVerdict


class VerificationPopulationJson(LoadingJson[VerificationPopulation]):
    model = VerificationPopulation
    cache_ok = True


class DatabaseVerificationRound(Base):
    """One draw of units of a batch to verify.

    What was asked for is kept beside what was drawn, with the seed, so that a
    round can be read back as it was made: from how many units, filtered how,
    and why.
    """

    __tablename__ = "verification_round"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    batch_uid: Mapped[UUID] = mapped_column(ForeignKey("batch.uid"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    seed: Mapped[int] = mapped_column(BigInteger)
    requested_size: Mapped[int | None] = mapped_column(Integer)
    requested_fraction: Mapped[float | None] = mapped_column(Float)
    population: Mapped[VerificationPopulation | None] = mapped_column(
        VerificationPopulationJson
    )
    population_size: Mapped[int] = mapped_column(Integer)
    origin_entry_uid: Mapped[UUID | None] = mapped_column(Uuid)
    """The entry whose failure the round follows up on. Not a foreign key:
    it points into the same batch's rounds, which go together."""

    batch: Mapped[DatabaseBatch] = relationship(DatabaseBatch)
    entries: Mapped[list["DatabaseVerificationEntry"]] = relationship(
        "DatabaseVerificationEntry",
        back_populates="round",
        cascade="all, delete-orphan",
    )


class DatabaseVerificationEntry(Base):
    """A unit drawn by a round, and what the verifier decided about it."""

    __tablename__ = "verification_entry"
    # A unit is drawn once: a later round draws from what earlier ones left.
    __table_args__ = (UniqueConstraint("unit_uid", name="uq_verification_entry_unit"),)

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    round_uid: Mapped[UUID] = mapped_column(
        ForeignKey("verification_round.uid"), index=True
    )
    unit_uid: Mapped[UUID] = mapped_column(ForeignKey("item.uid"))
    """The review unit drawn."""
    verdict: Mapped[VerificationVerdict] = mapped_column(Enum(VerificationVerdict))
    """What was last decided. Where the unit stands is read from this and from
    what has happened to the unit since, rather than stored."""
    reason: Mapped[str | None] = mapped_column(String(512))
    """Why it last failed, kept when it passes again."""
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)
    """When it was last decided on. Empty while pending."""
    failed_at: Mapped[datetime | None] = mapped_column(DateTime)
    """When it first failed, kept when it passes again: a round's failure rate
    counts what was found, not what was fixed since."""

    round: Mapped[DatabaseVerificationRound] = relationship(
        DatabaseVerificationRound, back_populates="entries"
    )
    unit: Mapped[DatabaseItem[Any]] = relationship(
        DatabaseItem,
        # Deleted with the unit: once it is gone there is nothing to verify,
        # and the unit could not be deleted while this pointed at it.
        backref=backref("verification_entries", cascade="all, delete-orphan"),
    )
