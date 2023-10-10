from enum import Enum


class ImageStatus(Enum):
    NOT_STARTED = 1
    DOWNLOADING = 2
    PROCESSING = 3
    FAILED = 4
    COMPLETED = 5
