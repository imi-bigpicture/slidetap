from enum import Enum


class ImageStatus(Enum):
    NOT_STARTED = 1
    DOWNLOADING = 2
    DOWNLOADED = 3
    PRE_PROCESSING = 4
    PRE_PROCESSED = 5
    POST_PROCESSING = 6
    POST_PROCESSED = 7
    FAILED = 8
    COMPLETED = 9
