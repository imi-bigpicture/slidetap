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

"""A path down inside an attribute, to read or replace what is held at its
end."""

from collections.abc import Sequence

from slidetap.model.attribute import AnyAttribute, ListAttribute, ObjectAttribute
from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.attribute_schema import (
    AttributeSchema,
    ListAttributeSchema,
    ObjectAttributeSchema,
)


class AttributePath(FrozenBaseModel):
    """A path down inside an attribute: the tags of objects and the positions
    in lists down to an attribute held there.

    For example ``("diagnoses", 2)`` in a statement object is the third entry
    of its list `diagnoses`. No steps is the attribute itself. A position may be
    the one past the last of a list, where nothing is held yet, to append to.

    Steps go through the effective value of what they pass: an object or a
    list as it now reads, whether edited, mapped or imported.
    """

    steps: tuple[str | int, ...] = ()

    @classmethod
    def from_item_path(cls, path: Sequence[str | int]) -> tuple[str, "AttributePath"]:
        """The tag of an attribute of an item, and the path inside it, from a
        path on the item naming both, such as ``["statement", "diagnoses", 2]``.

        Raises
        ------
        ValueError
            If the path is empty or does not start with a tag.
        """
        if len(path) == 0:
            raise ValueError("A path needs at least the tag of an attribute.")
        tag, *steps = path
        if not isinstance(tag, str):
            raise ValueError("A path starts with the tag of an attribute.")
        return tag, cls(steps=tuple(steps))

    @property
    def parent(self) -> "AttributePath":
        """The path to what holds the end of this one: no steps, the attribute
        itself, for a path one step down.

        Raises
        ------
        ValueError
            If this is the attribute itself, which nothing inside holds.
        """
        if not self.steps:
            raise ValueError("A path with no steps has nothing holding its end.")
        return AttributePath(steps=self.steps[:-1])

    def overlaps(self, other: "AttributePath") -> bool:
        """Whether one of two paths goes on down from the end of the other, so
        that replacing what is held at the end of one changes what is held at
        the end of the other. Not for the same path, nor for paths that part."""
        shorter, longer = sorted((self.steps, other.steps), key=len)
        return len(longer) > len(shorter) and longer[: len(shorter)] == shorter

    def after_removal_of(self, removed: "AttributePath") -> "AttributePath":
        """This path as it reads once the list entry at the end of another is
        taken out: one position earlier where this goes through a later entry
        of the same list. Unchanged where the other does not end at a list
        entry, or this does not go through its list."""
        if not removed.steps or not isinstance(removed.steps[-1], int):
            return self
        position = removed.steps[-1]
        list_steps = removed.steps[:-1]
        depth = len(list_steps)
        if len(self.steps) <= depth or self.steps[:depth] != list_steps:
            return self
        through = self.steps[depth]
        if not isinstance(through, int) or through <= position:
            return self
        steps = list(self.steps)
        steps[depth] = through - 1
        return AttributePath(steps=tuple(steps))

    def schema_in(self, schema: AttributeSchema) -> AttributeSchema:
        """The schema of what is held at the end of this path in attributes of a
        schema.

        Raises
        ------
        ValueError
            If a step does not go down from what it is taken from: a tag that
            is not of an object, or a position that is not in a list.
        """
        for step in self.steps:
            if isinstance(schema, ObjectAttributeSchema) and isinstance(step, str):
                child = schema.attributes.get(step)
                if child is None:
                    raise ValueError(f"{schema.display_name} has no '{step}'.")
                schema = child
            elif isinstance(schema, ListAttributeSchema) and isinstance(step, int):
                schema = schema.attribute
            else:
                raise ValueError(
                    f"Cannot go down from {schema.display_name} by {step!r}."
                )
        return schema

    def value_in(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """The attribute held at the end of this path in an attribute. None
        where nothing is held, such as an attribute of an object not given, the
        position past the last of a list, or a path going on below a value that
        holds nothing.

        Raises
        ------
        ValueError
            If a position is outside a list, but for the one past its last.
        """
        held: AnyAttribute | None = attribute
        for step in self.steps:
            if isinstance(held, ObjectAttribute) and isinstance(step, str):
                held = (held.value or {}).get(step)
            elif isinstance(held, ListAttribute) and isinstance(step, int):
                entries = held.value or []
                if step == len(entries):
                    return None
                if not 0 <= step < len(entries):
                    raise ValueError(f"No position {step} in the list.")
                held = entries[step]
            else:
                return None
        return held

    def replaced_in(
        self,
        attribute: AnyAttribute,
        schema: AttributeSchema,
        value: AnyAttribute | None,
    ) -> AnyAttribute:
        """A copy of an attribute of a schema with what is held at the end of
        this path replaced by a value, or taken out for None: from an object,
        or from a list, closing the gap. At the position past the last of a
        list, the value is appended.

        Each attribute passed on the way is edited: its effective value is
        copied, changed where the path goes, and made its updated value, so
        what was imported and mapped of it stays as it was. Its display value
        is made again from its schema.

        Raises
        ------
        ValueError
            If this path has no steps, a step does not go down from what
            it is taken from, or a position is outside a list, but for
            appending past its last.
        """
        if not self.steps:
            raise ValueError("A path with no steps ends at the attribute itself.")
        step, rest = self.steps[0], AttributePath(steps=self.steps[1:])
        held_schema = AttributePath(steps=(step,)).schema_in(schema)
        if isinstance(attribute, ObjectAttribute) and isinstance(step, str):
            held_object = dict(attribute.value or {})
            if rest.steps:
                nested = held_object.get(step)
                if nested is None:
                    raise ValueError(f"No '{step}' to go down through.")
                held_object[step] = rest.replaced_in(nested, held_schema, value)
            elif value is None:
                held_object.pop(step, None)
            else:
                held_object[step] = value
            changed = attribute.model_copy(update={"updated_value": held_object})
        elif isinstance(attribute, ListAttribute) and isinstance(step, int):
            entries = list(attribute.value or [])
            appending = step == len(entries)
            if not 0 <= step <= len(entries) or (
                appending and (rest.steps or value is None)
            ):
                raise ValueError(f"No position {step} in the list.")
            if rest.steps:
                entries[step] = rest.replaced_in(entries[step], held_schema, value)
            elif value is None:
                del entries[step]
            elif appending:
                entries.append(value)
            else:
                entries[step] = value
            changed = attribute.model_copy(update={"updated_value": entries})
        else:
            raise ValueError(f"Cannot go down from an attribute by {step!r}.")
        changed.display_value = (
            None
            if changed.value is None
            else schema.create_display_value(changed.value)
        )
        return changed
