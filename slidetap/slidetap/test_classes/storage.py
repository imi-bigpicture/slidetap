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

from tempfile import TemporaryDirectory
from types import TracebackType
from typing import Optional, Type

from slidetap.storage import Storage
from slidetap.storage.storage import StorageSettings


class TempStorage(Storage):
    def __init__(self):
        self.tempdir = TemporaryDirectory()
        super().__init__(self.tempdir.name, StorageSettings())

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.tempdir.cleanup()

    def cleanup(self):
        self.tempdir.cleanup()
