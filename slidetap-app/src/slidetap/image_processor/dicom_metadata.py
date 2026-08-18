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

"""Keeping what an image file said, and writing metadata into DICOM again."""

import dataclasses
import hashlib
import json
import logging
from dataclasses import replace
from pathlib import Path

from wsidicom import WsiDicom
from wsidicom.metadata import WsiMetadata
from wsidicom.metadata.schema.json import WsiMetadataJsonSchema
from wsidicomizer.metadata import WsiDicomizerMetadata


class DicomMetadataWriter:
    """Keeps what an image file said, and writes metadata into DICOM again.

    What is written is the application's to decide — it is handed what the file
    said and returns what should be in it. Nothing here has an opinion about
    which of the two wins.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._schema = WsiMetadataJsonSchema()

    def source_metadata(self, metadata: WsiMetadata) -> str | None:
        """What a file said about itself, as json to keep until it is needed.

        Taken while the file is read, before it is converted, so that writing
        the metadata again later starts from what the file said rather than from
        what the application wrote into it the last time.

        The confidential parts are removed before it is kept, as the conversion
        removes them from the files, so that what is kept to write into a file
        is what could be written into it.
        """
        try:
            deidentified = self.as_dicomizer_metadata(metadata).remove_confidential()
            return json.dumps(self._schema.dump(deidentified))
        except Exception:
            self._logger.warning(
                "Could not record what the file said about itself; the metadata "
                "of the converted file cannot be written again.",
                exc_info=True,
            )
            return None

    def recorded(self, source_metadata: str | None) -> WsiDicomizerMetadata | None:
        """What was kept of a file's own metadata, to be written over.

        None where nothing was kept — an image converted before it was, or one
        whose metadata could not be written down.
        """
        if source_metadata is None:
            return None
        try:
            return self.as_dicomizer_metadata(
                self._schema.load(json.loads(source_metadata))
            )
        except Exception:
            self._logger.warning(
                "Could not read back what the file said about itself.",
                exc_info=True,
            )
            return None

    @staticmethod
    def as_dicomizer_metadata(metadata: WsiMetadata) -> WsiDicomizerMetadata:
        """The same metadata as the class the conversion takes."""
        return WsiDicomizerMetadata(
            **{
                field.name: getattr(metadata, field.name)
                for field in dataclasses.fields(WsiMetadata)
            }
        )

    def resave(
        self,
        source: Path,
        destination: Path,
        metadata: WsiDicomizerMetadata,
        include_levels: list[int] | None = None,
        include_labels: bool = True,
        include_overviews: bool = True,
        workers: int | None = None,
    ) -> list[Path]:
        """Write the files of a DICOM image to destination with new metadata.

        The frames are copied as they are — nothing is encoded again, since only
        the metadata is being replaced.

        The metadata replaces what the files hold rather than being merged into
        it: it was made from what the file being converted said, so what it does
        not say is not an omission.

        The instance uids are new, which is what the standard asks for when what
        a file says about the images has changed.
        """
        with WsiDicom.open(source) as wsi:
            files = wsi.save(
                destination,
                metadata=self._with_icc_profiles(metadata, wsi.metadata),
                replace_metadata=True,
                include_levels=include_levels,
                include_labels=include_labels,
                include_overviews=include_overviews,
                workers=workers,
            )
        self._logger.info(
            f"Re-saved DICOM from {source} to {destination} with new metadata."
        )
        return [Path(file) for file in files]

    def _with_icc_profiles(
        self, metadata: WsiDicomizerMetadata, found: WsiMetadata
    ) -> WsiDicomizerMetadata:
        """The metadata, with the profiles of the file it is written into.

        An icc profile is the one part of the metadata that json does not carry,
        so an optical path read back from what was kept of a file has none. A
        file written without one is given a default profile instead of the one
        the scanner characterised its camera with, which is worse than losing
        the tag, so they are taken from the file being written again.
        """
        profiles = {
            path.identifier: path.icc_profile
            for path in found.pyramid.optical_paths
            if path.icc_profile is not None
        }
        if not profiles:
            return metadata
        optical_paths = [
            (
                replace(path, icc_profile=profiles[path.identifier])
                if path.icc_profile is None and path.identifier in profiles
                else path
            )
            for path in metadata.pyramid.optical_paths
        ]
        return replace(
            metadata, pyramid=replace(metadata.pyramid, optical_paths=optical_paths)
        )

    def digest(self, metadata: WsiMetadata) -> str | None:
        """A fingerprint of what would be written into an image's files.

        Taken so that storing an image whose metadata has not changed since it
        was written can move the files rather than write them again.

        The json the metadata serializes to is what is fingerprinted, rather
        than the objects being printed: it is written field by field, so a field
        declared out of the repr is not invisible, and it names the specimen a
        sample was sampled from by identifier, so the metadata referring back to
        itself does not run the walk out of stack. The one thing it leaves out
        is the icc profile, which is the file's rather than the application's.

        None where the metadata cannot be written down. A fingerprint that
        cannot be taken must not read as "nothing has changed", so the caller
        writes the files again instead.
        """
        try:
            written = json.dumps(self._schema.dump(metadata), sort_keys=True)
        except Exception:
            self._logger.warning(
                "Could not fingerprint the metadata; it will be written again.",
                exc_info=True,
            )
            return None
        return hashlib.sha256(written.encode()).hexdigest()
