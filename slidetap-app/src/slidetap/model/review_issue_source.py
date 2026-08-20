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

"""What raised a review issue."""

from enum import Enum


class ReviewIssueSource(Enum):
    """What raised an issue: what kind of thing, not which one.

    Which kind changes what a reviewer does with it — something an import
    could not settle is answered differently from something a colleague
    noticed — while who exactly raised it is not recorded, here or anywhere
    else in the application.
    """

    USER = "user"
    """Raised by somebody working on the items."""

    METADATA_IMPORTER = "metadata_importer"
    """Raised by the metadata import, reporting what it could not settle."""

    IMAGE_IMPORTER = "image_importer"
    """Raised by the image import, for the same reason."""

    VALIDATION = "validation"
    """Raised because an item under the unit is not as valid as it is expected
    to be, and settled when it becomes valid again.

    The only source raised and resolved without anybody deciding to: what it
    says is derived from the items, so it is answered by curating them rather
    than by a reviewer taking a view on it.
    """

    @property
    def queue_priority(self) -> int:
        """Where what this raised comes in a list of what is open, lowest
        first.

        A person waiting comes before an import reporting, which comes before
        what validation found. Not because one matters more than another, but
        because validation raises one for every item it finds — a case can be
        waiting on every image in a batch — and ordering by when they were
        raised would leave the one thing a colleague asked about below a list
        of images, where nobody reading the queue would see it.
        """
        return _QUEUE_PRIORITY[self]


_QUEUE_PRIORITY = {
    ReviewIssueSource.USER: 0,
    ReviewIssueSource.METADATA_IMPORTER: 1,
    ReviewIssueSource.IMAGE_IMPORTER: 1,
    ReviewIssueSource.VALIDATION: 2,
}
