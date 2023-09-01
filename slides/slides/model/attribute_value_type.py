from enum import Enum


class AttributeValueType(Enum):
    COMPOSITE = -1
    STRING = 1
    DATETIME = 2
    NUMERIC = 3
    MEASUREMENT = 4
    CODE = 5
    ENUM = 6
    BOOLEAN = 7
    OBJECT = 8
    LIST = 10
    UNION = 11
