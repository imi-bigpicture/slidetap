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

"""Metaclass for exporter."""

from abc import ABCMeta
from typing import Optional

from flask import Flask
from slidetap.flask_extension import FlaskExtension
from slidetap.storage.storage import Storage
from slidetap.task.scheduler import Scheduler


class Exporter(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for an exporter. Has a Storage for storing exported images
    and metadata."""

    def __init__(
        self, scheduler: Scheduler, storage: Storage, app: Optional[Flask] = None
    ):
        self._scheduler = scheduler
        self._storage = storage
        super().__init__(app)

    @property
    def storage(self) -> Storage:
        """The storage used for exporting images and metadata."""
        return self._storage
