from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TableRequest:
    start: int
    size: int
    identifier_filter: Optional[str] = None
    attribute_filters: Optional[Dict[str, str]] = None
    included: Optional[bool] = None
    valid: Optional[bool] = None
