from dataclasses import dataclass
from typing import Dict, Optional, Sequence


@dataclass
class ColumnSort:
    column: str
    is_attribute: bool
    descending: bool


@dataclass
class TableRequest:
    start: int
    size: int
    identifier_filter: Optional[str] = None
    attribute_filters: Optional[Dict[str, str]] = None
    sorting: Optional[Sequence[ColumnSort]] = None
    included: Optional[bool] = None
    valid: Optional[bool] = None
