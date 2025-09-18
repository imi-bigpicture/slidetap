#    Copyright 2025 SECTRA AB
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

from typing import Iterable, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database.item import DatabaseItem
from slidetap.model.item import Item
from slidetap.model.tag import Tag
from slidetap.services.database_service import DatabaseService


class TagService:
    def __init__(self, database_service: DatabaseService):

        self._database_service = database_service

    def get_all(
        self,
    ) -> List[Tag]:
        with self._database_service.get_session() as session:
            return [tag.model for tag in self._database_service.get_tags(session)]

    def update(self, tag: Tag) -> Tag:
        with self._database_service.get_session() as session:
            database_tag = self._database_service.get_optional_tag(session, tag)
            if not database_tag:
                database_tag = self._database_service.add_tag(session, tag)
            else:
                database_tag.name = tag.name
                database_tag.description = tag.description
                database_tag.color = tag.color
            return database_tag.model

    def update_for_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        tags: Iterable[UUID],
        session: Optional[Session] = None,
    ):
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item)
            database_tags = [
                self._database_service.get_optional_tag(session, tag) for tag in tags
            ]
            item.tags = set(tag for tag in database_tags if tag is not None)
