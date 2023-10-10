from enum import Enum


class ProjectStatus(Enum):
    INITIALIZED = 1
    SEARCHING = 2
    SEARCH_COMPLETE = 3
    STARTED = 4
    FAILED = 5
    COMPLETED = 6
    SUBMITTED = 7
    DELETED = 8
