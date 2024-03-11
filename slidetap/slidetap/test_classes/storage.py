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
