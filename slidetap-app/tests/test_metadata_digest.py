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

"""Tests what is kept of an image file, and what is written back into it.

What a file said about itself is kept when it is read, for the application to
write over when the metadata goes into DICOM. The fingerprint of what is written
decides whether the files have to be written again at all: the same metadata
fingerprints the same, so files that would say what they already say are moved
rather than written.
"""

import dataclasses
from datetime import datetime

from wsidicom.conceptcode import SpecimenStainsCode
from wsidicom.metadata import (
    Equipment,
    FocusMethod,
    Label,
    OpticalPath,
    Patient,
    Pyramid,
    Series,
    Slide,
    SlideSample,
    Staining,
    Study,
    WsiMetadata,
)
from wsidicom.metadata import Image as DicomImage
from wsidicomizer.metadata import WsiDicomizerMetadata

from slidetap.image_processor.dicom_metadata import DicomMetadataWriter


def _metadata(
    study_identifier: str = "CASE-1",
    sample_identifier: str = "SLIDE-1",
    stain: str = "hematoxylin stain",
) -> WsiDicomizerMetadata:
    return WsiDicomizerMetadata(
        study=Study(identifier=study_identifier, date=datetime(2026, 1, 2)),
        series=Series(),
        patient=Patient(name="PATIENT-1"),
        equipment=Equipment(),
        slide=Slide(
            stainings=[Staining([SpecimenStainsCode(stain)])],
            samples=[SlideSample(identifier=sample_identifier)],
        ),
        pyramid=Pyramid(image=DicomImage(), optical_paths=[]),
        label=Label(),
    )


class TestMetadataDigest:
    def test_same_metadata_fingerprints_the_same(self):
        assert DicomMetadataWriter().digest(
            _metadata()
        ) == DicomMetadataWriter().digest(_metadata())

    def test_a_changed_identifier_shows(self):
        assert DicomMetadataWriter().digest(
            _metadata()
        ) != DicomMetadataWriter().digest(_metadata(study_identifier="CASE-2"))

    def test_a_changed_sample_shows(self):
        assert DicomMetadataWriter().digest(
            _metadata()
        ) != DicomMetadataWriter().digest(_metadata(sample_identifier="SLIDE-2"))

    def test_a_changed_staining_shows(self):
        assert DicomMetadataWriter().digest(
            _metadata()
        ) != DicomMetadataWriter().digest(_metadata(stain="giemsa stain"))

    def test_a_cleared_field_shows(self):
        # What a curator cleared is what the application says about it, so the
        # files have to be written again to stop saying otherwise.
        with_versions = dataclasses.replace(
            _metadata(), equipment=Equipment(manufacturer="Co", software_versions=["1"])
        )
        cleared = dataclasses.replace(
            _metadata(), equipment=Equipment(manufacturer="Co")
        )

        assert DicomMetadataWriter().digest(
            with_versions
        ) != DicomMetadataWriter().digest(cleared)

    def test_metadata_that_refers_to_itself_can_be_fingerprinted(self):
        # A slide sample is sampled from a specimen whose sampling lists it
        # back, which is what walking the objects blindly runs aground on.
        metadata = _metadata()
        digest = DicomMetadataWriter().digest(metadata)
        assert digest is not None
        assert digest == DicomMetadataWriter().digest(metadata)


class TestSourceMetadata:
    """What the file said about itself, kept from the reading of it."""

    @staticmethod
    def _source() -> WsiMetadata:
        """As read from the file being converted, PHI and all."""
        return WsiMetadata(
            study=Study(identifier="SCANNER-CASE"),
            series=Series(),
            patient=Patient(name="REAL-PATIENT"),
            equipment=Equipment(
                manufacturer="Scanner Co",
                model_name="S-1000",
                device_serial_number="SN-1234",
            ),
            slide=Slide(),
            pyramid=Pyramid(
                image=DicomImage(
                    focus_method=FocusMethod.AUTO,
                    acquisition_datetime=datetime(2026, 1, 1),
                ),
                optical_paths=[OpticalPath(identifier="0")],
            ),
            label=Label(text="REAL-LABEL"),
        )

    def test_what_the_file_said_is_read_back(self):
        writer = DicomMetadataWriter()

        recorded = writer.recorded(writer.source_metadata(self._source()))

        assert recorded is not None
        assert recorded.equipment.manufacturer == "Scanner Co"
        assert recorded.equipment.model_name == "S-1000"
        assert recorded.pyramid.image.focus_method == FocusMethod.AUTO

    def test_nothing_confidential_is_kept(self):
        kept = DicomMetadataWriter().source_metadata(self._source())

        assert kept is not None
        assert "REAL-PATIENT" not in kept
        assert "REAL-LABEL" not in kept
        assert "SN-1234" not in kept

    def test_what_was_confidential_is_not_read_back(self):
        writer = DicomMetadataWriter()

        recorded = writer.recorded(writer.source_metadata(self._source()))

        assert recorded is not None
        assert recorded.patient.name is None
        assert recorded.equipment.device_serial_number is None
        assert recorded.pyramid.image.acquisition_datetime is None

    def test_nothing_kept_reads_back_as_nothing(self):
        # An image converted before what its file said was kept.
        assert DicomMetadataWriter().recorded(None) is None

    def test_what_cannot_be_read_back_reads_back_as_nothing(self):
        assert DicomMetadataWriter().recorded("{not json") is None


class TestIccProfiles:
    """The one thing json does not carry, taken from the file being written."""

    @staticmethod
    def _found(profile: bytes | None = b"\x00\x01") -> WsiMetadata:
        return WsiMetadata(
            study=Study(),
            series=Series(),
            patient=Patient(),
            equipment=Equipment(),
            slide=Slide(),
            pyramid=Pyramid(
                image=DicomImage(),
                optical_paths=[OpticalPath(identifier="0", icc_profile=profile)],
            ),
            label=Label(),
        )

    @staticmethod
    def _written(profile: bytes | None = None) -> WsiDicomizerMetadata:
        return dataclasses.replace(
            _metadata(),
            pyramid=Pyramid(
                image=DicomImage(),
                optical_paths=[OpticalPath(identifier="0", icc_profile=profile)],
            ),
        )

    def test_a_path_without_a_profile_takes_the_files(self):
        written = DicomMetadataWriter()._with_icc_profiles(
            self._written(), self._found()
        )

        assert written.pyramid.optical_paths[0].icc_profile == b"\x00\x01"

    def test_a_path_with_a_profile_keeps_it(self):
        written = DicomMetadataWriter()._with_icc_profiles(
            self._written(profile=b"\x02\x03"), self._found()
        )

        assert written.pyramid.optical_paths[0].icc_profile == b"\x02\x03"

    def test_a_path_the_file_does_not_have_is_left_alone(self):
        written = DicomMetadataWriter()._with_icc_profiles(
            self._written(), self._found(profile=None)
        )

        assert written.pyramid.optical_paths[0].icc_profile is None
