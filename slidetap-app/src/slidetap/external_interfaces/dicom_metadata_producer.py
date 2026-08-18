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

from wsidicomizer.metadata import WsiDicomizerMetadata

from slidetap.model import Image, RootSchema


class DicomMetadataProducer(metaclass=ABCMeta):
    """What an application puts in the DICOM files it produces.

    Given to the step that writes the files, and to whatever writes them again
    when they are stored — the metadata is asked for from one place so that
    both write the same thing, and so that what would be written now can be
    compared with what was written then.
    """

    @abstractmethod
    def create(
        self, schema: RootSchema, image: Image, base: WsiDicomizerMetadata
    ) -> WsiDicomizerMetadata:
        """The metadata for an image, as the items stand now.

        Written over what the image file said about itself, so that what the
        application does not model is kept rather than thrown away — a scanner
        describes its optics and its acquisition, and nothing here knows better.

        Set every field the application models, on every call, including the
        ones that are empty. What is read out of a file and then curated belongs
        to the item afterwards: a value a curator cleared has to be cleared here
        too, and leaving it alone would keep saying what the file said. Which
        fields those are is not something this can be asked separately — it is
        what the assignments in here say it is, and reads against the step that
        put them in the items in the first place.
        """
        raise NotImplementedError()


class EmptyDicomMetadataProducer(DicomMetadataProducer):
    """Nothing of the application's own, for a conversion that needs none."""

    def create(
        self, schema: RootSchema, image: Image, base: WsiDicomizerMetadata
    ) -> WsiDicomizerMetadata:
        return base
