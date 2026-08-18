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

from enum import IntEnum


class BatchStatus(IntEnum):
    """Where a batch stands, in the order it goes through them.

    The values are not what is stored — the database holds the names — so they
    are free to say what follows what.
    """

    INITIALIZED = 1
    """Created, with nothing searched for yet."""

    METADATA_SEARCHING = 2
    """Looking up the metadata of what the search document asked for."""

    METADATA_SEARCH_COMPLETE = 3
    """The metadata is in; the images have not been fetched."""

    IMAGE_PRE_PROCESSING = 4
    """Fetching the images and preparing them for curation."""

    IMAGE_PRE_PROCESSING_COMPLETE = 5
    """The images are here, and the batch is ready to be curated."""

    IMAGE_POST_PROCESSING = 6
    """Writing the images into the export format, metadata and all."""

    IMAGE_POST_PROCESSING_COMPLETE = 7
    """The images are in the export format, waiting in the processing folder."""

    LOCKED = 8
    """Curated, valid and closed to editing, with the images still ours.

    They go to the outbox when the project is completed, so that a batch
    unlocked until then leaves nothing behind in a bundle already handed over.
    """

    IMAGE_STORING = 9
    """Moving the images from the processing folder to the outbox."""

    COMPLETED = 10
    """Everything in the batch is in the outbox."""

    FAILED = 11
    """Something went wrong that the batch cannot go on from."""

    DELETED = 12
    """Taken out of the project."""
