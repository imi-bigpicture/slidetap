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

"""Tests for the file system semantics that storing depends on.

Storing is designed around these, and mocks the operations to test itself, so
they are pinned here against a real file system.
"""

from pathlib import Path

import pytest

from slidetap.services.file_operations import FileOperations


@pytest.fixture()
def file_operations() -> FileOperations:
    return FileOperations()


@pytest.fixture()
def folder(tmp_path: Path) -> Path:
    folder = tmp_path.joinpath("folder")
    folder.mkdir()
    folder.joinpath("file.dcm").write_bytes(b"bytes")
    return folder


@pytest.mark.unittest
class TestFileOperations:
    def test_rename_moves_folder(
        self, file_operations: FileOperations, folder: Path, tmp_path: Path
    ) -> None:
        """A folder is renamed as a whole, with everything it holds."""
        # Arrange
        destination = tmp_path.joinpath("renamed folder")

        # Act
        file_operations.rename(folder, destination)

        # Assert
        assert not folder.exists()
        assert destination.joinpath("file.dcm").read_bytes() == b"bytes"

    def test_rename_onto_existing_folder_raises(
        self, file_operations: FileOperations, folder: Path, tmp_path: Path
    ) -> None:
        """A rename cannot replace an existing folder.

        Storing thus renames an existing destination aside before renaming into
        its place, rather than renaming over it.
        """
        # Arrange
        destination = tmp_path.joinpath("existing folder")
        destination.mkdir()
        destination.joinpath("existing.dcm").write_bytes(b"existing bytes")

        # Act & Assert
        with pytest.raises(OSError):
            file_operations.rename(folder, destination)
        assert destination.joinpath("existing.dcm").read_bytes() == b"existing bytes"

    def test_copy_copies_folder_and_keeps_source(
        self, file_operations: FileOperations, folder: Path, tmp_path: Path
    ) -> None:
        """A copy leaves the source in place, unlike a rename."""
        # Arrange
        destination = tmp_path.joinpath("copied folder")

        # Act
        file_operations.copy(folder, destination)

        # Assert
        assert folder.joinpath("file.dcm").read_bytes() == b"bytes"
        assert destination.joinpath("file.dcm").read_bytes() == b"bytes"

    def test_copy_copies_file(
        self, file_operations: FileOperations, tmp_path: Path
    ) -> None:
        """A thumbnail is a file, not a folder, and is copied as one."""
        # Arrange
        source = tmp_path.joinpath("thumbnail.jpeg")
        source.write_bytes(b"thumbnail bytes")
        destination = tmp_path.joinpath("copied thumbnail.jpeg")

        # Act
        file_operations.copy(source, destination)

        # Assert
        assert destination.read_bytes() == b"thumbnail bytes"

    def test_remove_removes_folder_and_file(
        self, file_operations: FileOperations, folder: Path, tmp_path: Path
    ) -> None:
        """Both a folder and a file are removed, as an image is one of each."""
        # Arrange
        file = tmp_path.joinpath("thumbnail.jpeg")
        file.write_bytes(b"thumbnail bytes")

        # Act
        file_operations.remove(folder)
        file_operations.remove(file)

        # Assert
        assert not folder.exists()
        assert not file.exists()

    def test_exists_of_missing_path_is_false(
        self, file_operations: FileOperations, tmp_path: Path
    ) -> None:
        """A path that is not there does not exist, and does not raise.

        A path on a dropped mount reads the same way, which is why storing cannot
        read a missing source as one that has been stored.
        """
        # Act & Assert
        assert not file_operations.exists(tmp_path.joinpath("missing"))

    def test_same_filesystem_of_paths_in_same_folder(
        self, file_operations: FileOperations, folder: Path, tmp_path: Path
    ) -> None:
        """Paths on one file system can be renamed between, and are reported so."""
        # Act & Assert
        assert file_operations.same_filesystem(folder, tmp_path)

    def test_same_filesystem_of_unreachable_path_is_false(
        self, file_operations: FileOperations, folder: Path, tmp_path: Path
    ) -> None:
        """A path that cannot be reached is not on the same file system.

        Storing then copies rather than renames, and the copy fails with the
        reason the path could not be reached.
        """
        # Act & Assert
        assert not file_operations.same_filesystem(folder, tmp_path.joinpath("missing"))
