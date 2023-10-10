from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Dzi:
    url: str
    width: int
    height: int
    tile_size: int
    tile_format: str
    planes: List[float]
    channels: List[str]
    tile_overlap: int = 0
    tiles_url: Optional[str] = None
