from dataclasses import dataclass

from slidetap.database.schema.item_schema import ItemSchema


@dataclass
class ProjectItem:
    schema: ItemSchema
    count: int
