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
from collections.abc import Sequence

from slidetap.model import RootSchema


class SchemaInterface(metaclass=ABCMeta):
    @abstractmethod
    def root(self) -> RootSchema:
        """
        The root schema new projects are created with.

        A project is on its root by the root's uid alone, so any change to the
        content of a root needs a new root uid, and new uids for the schemas
        changed, with the old root kept as a previous root. The application
        refuses to start while projects hold items or attributes on schemas
        their root does not have.

        Called once, when the schema service is created.

        Returns
        -------
        RootSchema
            The root of new projects.
        """
        raise NotImplementedError()

    def previous_roots(self) -> Sequence[RootSchema]:
        """
        The root schemas of earlier versions that projects are still on.

        A project stays on the root it was created with, so a root that
        existing projects are on must be returned for as long as there are
        such projects: the application refuses to start while a project is on
        a root returned neither here nor by `root()`. A previous root is
        returned as it was when its projects were created on it; a change to
        it is a new root, see `root()`.

        Called once, when the schema service is created.

        Returns
        -------
        Sequence[RootSchema]
            The previous roots. Defaults to none.
        """
        return ()

    @classmethod
    @abstractmethod
    def get_schema_type(cls) -> type[RootSchema]:
        """
        Get the type of schema handled by this interface.

        Returns
        -------
        type[RootSchema]
            The type of schema.
        """
        raise NotImplementedError()
