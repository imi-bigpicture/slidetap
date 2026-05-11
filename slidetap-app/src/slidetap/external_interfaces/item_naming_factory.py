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

from abc import ABCMeta, abstractmethod
from typing import Optional

from slidetap.model import Item


class ItemNamingFactoryInterface(metaclass=ABCMeta):
    """Synthesize identifiers and (optionally) names for newly-created items.

    Sibling to :py:class:`PseudonymFactoryInterface`. Both receive a fully
    constructed in-memory :py:class:`Item` model — with schema, dataset,
    parents, and attributes all in place — and return a label string.

    Implementations can read parent linkage off the model directly:
    ``Sample.parents`` / ``Image.samples`` / ``Annotation.image`` /
    ``Observation.sample``/``image``/``annotation``.
    """

    @abstractmethod
    def create_identifier(self, item: Item) -> str:
        """Return a human-readable identifier for ``item``.

        Implementations should ensure uniqueness within the dataset.
        """
        raise NotImplementedError()

    def create_name(self, item: Item) -> Optional[str]:
        """Return a display name for ``item``, or ``None``."""
        return None
