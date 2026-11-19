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

"""File system operations."""

import hashlib
import shutil
from collections.abc import Iterator
from io import RawIOBase
from pathlib import Path

CHUNK_SIZE = 16 * 1024 * 1024
"""Bytes read at a time. Large, as image files are large and often on a network
share, where each read is a round trip."""


class FileOperations:
    """The file system operations that storing performs.

    Injected so that tests can subclass it to produce the failures a real file
    system cannot be asked for, such as a mount dropping part-way through a copy,
    a destination on another file system, or a mount that has dropped and thus
    reads as empty.

    Subclasses are expected to perform the real operation where they do not fail
    it. Storing depends on the semantics of the real file system -- that a rename
    is atomic within a file system and impossible across one, that a copy is
    neither, and that an unreachable path reads as missing rather than raising --
    and a reimplementation of it would only approximate them.
    """

    def exists(self, path: Path) -> bool:
        """Return True if the path exists.

        Note that a path on an unreachable filesystem does not exist, rather than
        raising.
        """
        return path.exists()

    def same_filesystem(self, path: Path, other_path: Path) -> bool:
        """Return True if the paths are on the same filesystem.

        Paths on the same filesystem can be renamed between, which is atomic, and
        paths on different filesystems have to be copied, which is not. Paths that
        cannot be reached are not on the same filesystem, and are thus copied, and
        the copy fails with the reason the path could not be reached.
        """
        try:
            return path.stat().st_dev == other_path.stat().st_dev
        except OSError:
            return False

    def rename(self, source: Path, destination: Path) -> None:
        """Rename source to destination. Atomic, and only within a filesystem."""
        source.rename(destination)

    def copy(self, source: Path, destination: Path) -> dict[Path, str]:
        """Copy source file or folder to destination.

        Returns the SHA-256 of each file copied, as a hex string, by its path
        relative to the source folder, or by its name for a file. Taken from what
        is written, so the files are read only once.
        """
        if not source.is_dir():
            return {Path(source.name): self._copy_file(source, destination)}
        checksums: dict[Path, str] = {}

        def copy_file(file: str, copied: str) -> None:
            checksums[Path(file).relative_to(source)] = self._copy_file(
                Path(file), Path(copied)
            )

        shutil.copytree(source, destination, copy_function=copy_file)
        return checksums

    def remove(self, path: Path) -> None:
        """Remove file or folder."""
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def make_folder(self, path: Path) -> None:
        """Create folder, and any missing parents of it."""
        path.mkdir(parents=True, exist_ok=True)

    def checksum(self, path: Path) -> str:
        """SHA-256 of the file, as a hex string."""
        digest = hashlib.sha256()
        with open(path, "rb", buffering=0) as file:
            for chunk in self._chunks(file):
                digest.update(chunk)
        return digest.hexdigest()

    def list_files(self, folder: Path) -> list[Path]:
        """Files in folder and its subfolders, in sorted order."""
        return sorted(path for path in folder.rglob("*") if path.is_file())

    def _copy_file(self, source: Path, destination: Path) -> str:
        """Copy a file with its metadata, as `shutil.copy2` does, and return the
        SHA-256 of what was written."""
        digest = hashlib.sha256()
        with (
            open(source, "rb", buffering=0) as reader,
            open(destination, "wb") as writer,
        ):
            for chunk in self._chunks(reader):
                digest.update(chunk)
                writer.write(chunk)
        shutil.copystat(source, destination)
        return digest.hexdigest()

    @staticmethod
    def _chunks(file: RawIOBase) -> Iterator[memoryview]:
        """The file's content, read `CHUNK_SIZE` at a time into one buffer."""
        buffer = memoryview(bytearray(CHUNK_SIZE))
        while read := file.readinto(buffer):
            yield buffer[:read]
