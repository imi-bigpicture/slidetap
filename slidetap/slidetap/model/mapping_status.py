from enum import Enum


class MappingStatus(Enum):
    NO_MAPPABLE_VALUE = 1
    NO_MAPPER = 2
    NOT_MAPPED = 3
    MAPPED = 4
