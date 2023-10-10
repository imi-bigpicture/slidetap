from dataclasses import dataclass
from typing import Optional


@dataclass
class Code:
    code: str
    scheme: str
    meaning: str
    scheme_version: Optional[str] = None
