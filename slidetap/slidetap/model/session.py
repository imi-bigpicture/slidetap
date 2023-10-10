from dataclasses import dataclass
from typing import Optional


@dataclass
class Session:
    """Session received for authenticated user."""

    username: str
    token: str
    keep_alive_interval: Optional[str] = None
