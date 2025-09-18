from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class File:
    filename: str
    content_type: str
    stream: BinaryIO