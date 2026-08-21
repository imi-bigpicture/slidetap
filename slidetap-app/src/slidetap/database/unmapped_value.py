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

"""A value someone recorded that no mapping accounts for."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import Base


class DatabaseUnmappedValue(Base):
    """A value an attribute carries that no mapping resolves.

    Read off the attributes as they are written, rather than searched for when
    asked. Only an attribute hanging directly off an item is a row of its own;
    the rest are JSON inside that row, and finding the unmapped ones among them
    means walking every attribute of every item in the project. That is a
    question this table answers instead.

    Derived, in full, from the attributes it is read from: it is never the only
    copy of anything, and rebuilding it loses nothing. What that buys is the
    freedom to repair it rather than having to prove it can never be wrong ---
    see ``slidetap-db unmapped-values``.
    """

    __tablename__ = "unmapped_value"

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    """The attribute's own uid, nested or not.

    Nested attributes carry a uid of their own in the JSON they are stored in,
    so an occurrence has an identity without one being invented for it. Two
    identical values in a list are two attributes, and so two rows.
    """

    root_attribute_uid: Mapped[UUID] = mapped_column(
        ForeignKey("attribute.uid", ondelete="CASCADE"), index=True
    )
    """The attribute row this was read from, which is itself where it is not
    nested.

    Deleted with it, so that an attribute or the item under it going away
    cannot leave a value behind that nothing holds. Replacing what one
    attribute contributes is then a delete by this and an insert, with no
    reconciling.
    """

    schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
    """What the attribute is, which says which mapper would resolve it."""

    value: Mapped[str] = mapped_column(String(512))
    """What was recorded, as it was recorded."""

    root_attribute: Mapped[DatabaseAttribute] = relationship(
        DatabaseAttribute,
        backref=backref("unmapped_values", cascade="all, delete-orphan"),
    )
