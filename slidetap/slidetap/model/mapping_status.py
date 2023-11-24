from enum import Enum


class MappingStatus(Enum):
    ORIGINAL_VALUE = 1
    NO_MAPPABLE_VALUE = 2
    NO_MAPPER = 3
    NOT_MAPPED = 4
    MAPPED = 5
