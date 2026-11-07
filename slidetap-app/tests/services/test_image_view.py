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

"""Viewing an image through the image view interface of the application."""

import datetime
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything, HasAttributes
from slidetap_example import ExampleSchema
from wsidicom.errors import WsiDicomNotFoundError

from slidetap.config import ImageCacheConfig
from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseImageFile,
    DatabaseProject,
)
from slidetap.external_interfaces import ImageViewInterface
from slidetap.external_interfaces.implementations import FileImageViewInterface
from slidetap.model import BatchStatus, Dzi, ImageFormat, ImageStatus, ImageToView
from slidetap.model.image_status import PROCESSED_STATUSES
from slidetap.services import (
    DatabaseService,
    ImageCache,
    ImageService,
)


def _add_image(
    database_service: DatabaseService,
    schema: ExampleSchema,
    folder_path: Path | None,
) -> UUID:
    with database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", schema.dataset.uid)
        session.add(dataset)
        project = DatabaseProject(
            "project",
            schema.uid,
            schema.project.uid,
            dataset.uid,
            datetime.datetime(2026, 11, 5),
        )
        session.add(project)
        batch = DatabaseBatch("batch", project.uid, datetime.datetime(2026, 11, 5))
        batch.status = BatchStatus.METADATA_SEARCH_COMPLETE
        session.add(batch)
        session.flush()
        image = DatabaseImage(
            dataset_uid=dataset.uid,
            batch_uid=batch.uid,
            schema_uid=schema.image.uid,
            identifier="PL1234-20-1",
            format=ImageFormat.OTHER_WSI,
        )
        image.status = (
            ImageStatus.NOT_STARTED
            if folder_path is None
            else ImageStatus.PRE_PROCESSED
        )
        image.folder_path = str(folder_path) if folder_path is not None else None
        session.add(image)
        session.commit()
        return image.uid


@pytest.fixture()
def image_view_interface(decoy: Decoy) -> ImageViewInterface:
    return decoy.mock(cls=ImageViewInterface)


@pytest.fixture()
def image_service(
    stored_database_service: DatabaseService,
    image_view_interface: ImageViewInterface,
) -> ImageService:
    return ImageService(
        stored_database_service, image_view_interface, ImageCacheConfig()
    )


def _move(database_service: DatabaseService, image_uid: UUID, folder: Path):
    with database_service.get_session() as session:
        database_service.get_image(session, image_uid).folder_path = str(folder)


@pytest.mark.integration
class TestImageService:
    @pytest.mark.parametrize("downloaded", [False, True])
    def test_the_image_is_described_by_the_interface(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
        downloaded: bool,
    ):
        """Downloaded or not, as the interface knows where to read it from."""
        # Arrange
        image_uid = _add_image(
            stored_database_service, schema, tmp_path if downloaded else None
        )
        dzi = Dzi(
            url="/dzi/",
            width=1024,
            height=512,
            tile_size=256,
            tile_format="jpeg",
            planes=[0.0],
            channels=[],
        )
        decoy.when(
            image_view_interface.get_dzi(HasAttributes({"uid": image_uid}), "/dzi/")
        ).then_return(dzi)

        # Act
        described = image_service.get_dzi(image_uid, "/dzi/")

        # Assert
        assert described == dzi

    def test_a_tile_is_read_by_the_interface(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
    ):
        # Arrange
        image_uid = _add_image(stored_database_service, schema, None)
        decoy.when(
            image_view_interface.get_tile(Anything(), 10, 2, 1, "jpeg", None)
        ).then_return(b"tile")

        # Act
        tile = image_service.get_tile(image_uid, 10, 2, 1, "jpeg")

        # Assert
        assert tile == b"tile"

    def test_a_thumbnail_is_read_by_the_interface(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
    ):
        # Arrange
        image_uid = _add_image(stored_database_service, schema, None)
        decoy.when(
            image_view_interface.get_thumbnail(Anything(), 64, 64, "png")
        ).then_return(b"thumbnail")

        # Act
        thumbnail = image_service.get_thumbnail(image_uid, 64, 64, "png")

        # Assert
        assert thumbnail == b"thumbnail"

    def test_an_image_not_there_is_not_found(self, image_service: ImageService):
        # Act & Assert
        with pytest.raises(ValueError):
            image_service.get_dzi(uuid4(), "/dzi/")
        assert image_service.get_thumbnail(uuid4(), 64, 64, "png") is None


@pytest.mark.integration
class TestImageLookup:
    def test_the_image_is_read_with_its_files(
        self,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        # Arrange
        image_uid = _add_image(stored_database_service, schema, tmp_path)
        with stored_database_service.get_session() as session:
            database_image = stored_database_service.get_image(session, image_uid)
            database_image.external_identifier = "slide-1"
            database_image.files.add(DatabaseImageFile(database_image, "slide.svs"))

        # Act
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_image_to_view(session, image_uid)

        # Assert
        assert image == ImageToView(
            uid=image_uid,
            status=ImageStatus.PRE_PROCESSED,
            format=ImageFormat.OTHER_WSI,
            folder_path=str(tmp_path),
            external_identifier="slide-1",
            filenames=("slide.svs",),
        )

    def test_an_image_without_files_is_read_without_them(
        self,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
    ):
        # Arrange
        image_uid = _add_image(stored_database_service, schema, None)

        # Act
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_image_to_view(session, image_uid)

        # Assert
        assert image is not None
        assert image.filenames == ()

    def test_an_image_not_there_is_none(self, stored_database_service: DatabaseService):
        # Act
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_image_to_view(session, uuid4())

        # Assert
        assert image is None


@pytest.mark.integration
class TestImageKeptForSeconds:
    def test_an_image_is_read_once_within_the_seconds(
        self,
        decoy: Decoy,
        monkeypatch: pytest.MonkeyPatch,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        # Arrange
        monkeypatch.setattr("slidetap.services.image_service.monotonic", lambda: 0.0)
        image_uid = _add_image(stored_database_service, schema, tmp_path / "a")
        image_service.get_tile(image_uid, 10, 2, 1, "jpeg")
        _move(stored_database_service, image_uid, tmp_path / "b")
        monkeypatch.setattr("slidetap.services.image_service.monotonic", lambda: 4.9)

        # Act
        image_service.get_tile(image_uid, 10, 2, 1, "jpeg")

        # Assert
        decoy.verify(
            image_view_interface.get_tile(
                HasAttributes({"folder_path": str(tmp_path / "a")}),
                10,
                2,
                1,
                "jpeg",
                None,
            ),
            times=2,
        )

    def test_an_image_is_read_again_once_the_seconds_have_passed(
        self,
        decoy: Decoy,
        monkeypatch: pytest.MonkeyPatch,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        """So that a converted image is viewed where it now is."""
        # Arrange
        monkeypatch.setattr("slidetap.services.image_service.monotonic", lambda: 0.0)
        image_uid = _add_image(stored_database_service, schema, tmp_path / "a")
        image_service.get_tile(image_uid, 10, 2, 1, "jpeg")
        _move(stored_database_service, image_uid, tmp_path / "b")
        monkeypatch.setattr("slidetap.services.image_service.monotonic", lambda: 5.0)

        # Act
        image_service.get_tile(image_uid, 10, 2, 1, "jpeg")

        # Assert
        decoy.verify(
            image_view_interface.get_tile(
                HasAttributes({"folder_path": str(tmp_path / "b")}),
                10,
                2,
                1,
                "jpeg",
                None,
            ),
            times=1,
        )

    def test_an_image_not_there_is_not_kept(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        """So that one added is viewed at once."""
        # Arrange
        image_uid = _add_image(stored_database_service, schema, tmp_path)
        with stored_database_service.get_session() as session:
            session.delete(stored_database_service.get_image(session, image_uid))
        assert image_service.get_thumbnail(image_uid, 64, 64, "png") is None
        added = _add_image(stored_database_service, schema, tmp_path)
        decoy.when(
            image_view_interface.get_thumbnail(
                HasAttributes({"uid": added}), 64, 64, "png"
            )
        ).then_return(b"thumbnail")

        # Act
        thumbnail = image_service.get_thumbnail(added, 64, 64, "png")

        # Assert
        assert thumbnail == b"thumbnail"

    def test_no_seconds_reads_the_image_for_every_request(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        # Arrange
        image_service = ImageService(
            stored_database_service,
            image_view_interface,
            ImageCacheConfig(image_seconds=0),
        )
        image_uid = _add_image(stored_database_service, schema, tmp_path / "a")
        image_service.get_tile(image_uid, 10, 2, 1, "jpeg")
        _move(stored_database_service, image_uid, tmp_path / "b")

        # Act
        image_service.get_tile(image_uid, 10, 2, 1, "jpeg")

        # Assert
        decoy.verify(
            image_view_interface.get_tile(
                HasAttributes({"folder_path": str(tmp_path / "b")}),
                10,
                2,
                1,
                "jpeg",
                None,
            ),
            times=1,
        )


@pytest.mark.integration
class TestImageWhoseFilesAreNotThere:
    @pytest.mark.parametrize(
        "missing",
        [
            FileNotFoundError("the download is removed"),
            WsiDicomNotFoundError("level files", "the converted folder"),
        ],
    )
    def test_an_image_moved_within_the_seconds_is_viewed_where_it_now_is(
        self,
        decoy: Decoy,
        monkeypatch: pytest.MonkeyPatch,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
        missing: Exception,
    ):
        """As a converted image is, from its download, and a stored one, into
        the outbox."""
        # Arrange
        monkeypatch.setattr("slidetap.services.image_service.monotonic", lambda: 0.0)
        image_uid = _add_image(stored_database_service, schema, tmp_path / "a")
        decoy.when(
            image_view_interface.get_tile(
                HasAttributes({"folder_path": str(tmp_path / "a")}),
                10,
                2,
                1,
                "jpeg",
                None,
            )
        ).then_raise(missing)
        decoy.when(
            image_view_interface.get_tile(
                HasAttributes({"folder_path": str(tmp_path / "b")}),
                10,
                2,
                1,
                "jpeg",
                None,
            )
        ).then_return(b"moved")
        image_service.get_dzi(image_uid, "/dzi/")
        _move(stored_database_service, image_uid, tmp_path / "b")

        # Act
        tile = image_service.get_tile(image_uid, 10, 2, 1, "jpeg")

        # Assert
        assert tile == b"moved"

    def test_an_image_whose_files_are_gone_is_not_found(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        # Arrange
        image_uid = _add_image(stored_database_service, schema, tmp_path)
        decoy.when(image_view_interface.get_dzi(Anything(), "/dzi/")).then_raise(
            FileNotFoundError("gone")
        )

        # Act & Assert
        with pytest.raises(ValueError, match="not there"):
            image_service.get_dzi(image_uid, "/dzi/")

    def test_an_image_whose_files_are_gone_has_no_thumbnail(
        self,
        decoy: Decoy,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        # Arrange
        image_uid = _add_image(stored_database_service, schema, tmp_path)
        decoy.when(
            image_view_interface.get_thumbnail(Anything(), 64, 64, "png")
        ).then_raise(FileNotFoundError("gone"))

        # Act
        thumbnail = image_service.get_thumbnail(image_uid, 64, 64, "png")

        # Assert
        assert thumbnail is None

    def test_an_image_whose_files_stay_gone_where_it_moved_is_not_found(
        self,
        decoy: Decoy,
        monkeypatch: pytest.MonkeyPatch,
        stored_database_service: DatabaseService,
        image_service: ImageService,
        image_view_interface: ImageViewInterface,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        """Read again once, rather than for as long as it is asked for."""
        # Arrange
        monkeypatch.setattr("slidetap.services.image_service.monotonic", lambda: 0.0)
        image_uid = _add_image(stored_database_service, schema, tmp_path / "a")
        reads: list[object] = []

        def gone(*args: object) -> bytes:
            reads.append(args[0])
            raise FileNotFoundError("gone")

        decoy.when(
            image_view_interface.get_tile(Anything(), 10, 2, 1, "jpeg", None)
        ).then_do(gone)
        image_service.get_dzi(image_uid, "/dzi/")
        _move(stored_database_service, image_uid, tmp_path / "b")

        # Act & Assert
        with pytest.raises(ValueError, match="not there"):
            image_service.get_tile(image_uid, 10, 2, 1, "jpeg")
        assert len(reads) == 2


@pytest.mark.integration
class TestProcessed:
    @pytest.mark.parametrize("status", list(ImageStatus))
    def test_the_image_and_what_is_viewed_of_it_say_the_same(
        self,
        stored_database_service: DatabaseService,
        schema: ExampleSchema,
        status: ImageStatus,
    ):
        # Arrange
        image_uid = _add_image(stored_database_service, schema, None)
        with stored_database_service.get_session() as session:
            stored_database_service.get_image(session, image_uid).status = status

        # Act
        with stored_database_service.get_session() as session:
            processed = stored_database_service.get_image(session, image_uid).processed
            to_view = stored_database_service.get_image_to_view(session, image_uid)

        # Assert
        assert processed is (status in PROCESSED_STATUSES)
        assert to_view is not None
        assert to_view.processed is processed

    def test_an_image_that_failed_to_store_holds_processed_data(self):
        # Act & Assert
        assert ImageStatus.STORING_FAILED in PROCESSED_STATUSES


@pytest.fixture()
def image_cache(decoy: Decoy) -> ImageCache:
    return decoy.mock(cls=ImageCache)


@pytest.fixture()
def file_image_view_interface(image_cache: ImageCache) -> FileImageViewInterface:
    return FileImageViewInterface(image_cache)


def _image(folder_path: Path | None) -> ImageToView:
    return ImageToView(
        uid=uuid4(),
        status=ImageStatus.PRE_PROCESSED,
        format=ImageFormat.OTHER_WSI,
        folder_path=str(folder_path) if folder_path is not None else None,
    )


@pytest.mark.unittest
class TestFileImageViewInterface:
    def test_a_thumbnail_is_made_from_the_files(
        self,
        monkeypatch: pytest.MonkeyPatch,
        file_image_view_interface: FileImageViewInterface,
        tmp_path: Path,
    ):
        # Arrange
        monkeypatch.setattr(
            file_image_view_interface,
            "_create_thumbnail",
            lambda image, width, height, format: b"from files",
        )

        # Act
        thumbnail = file_image_view_interface.get_thumbnail(
            _image(tmp_path), 64, 64, "png"
        )

        # Assert
        assert thumbnail == b"from files"

    def test_an_image_not_downloaded_has_no_thumbnail(
        self, file_image_view_interface: FileImageViewInterface
    ):
        # Act
        thumbnail = file_image_view_interface.get_thumbnail(_image(None), 64, 64, "png")

        # Assert
        assert thumbnail is None

    def test_an_image_not_downloaded_is_not_described(
        self,
        decoy: Decoy,
        image_cache: ImageCache,
        file_image_view_interface: FileImageViewInterface,
    ):
        # Arrange
        image = _image(None)
        not_opened = MagicMock()
        not_opened.__enter__.return_value = None
        decoy.when(image_cache.get(image)).then_return(not_opened)

        # Act & Assert
        with pytest.raises(ValueError):
            file_image_view_interface.get_dzi(image, "/dzi/")
