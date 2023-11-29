from enum import Enum


class ValueStatus(Enum):
    ORIGINAL_VALUE = 1
    UPDATED_VALUE = 2
    NO_MAPPABLE_VALUE = 3
    NO_MAPPER = 4
    NOT_MAPPED = 5
    MAPPED = 6
