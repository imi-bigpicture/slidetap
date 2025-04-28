from abc import ABCMeta, abstractmethod
from typing import Any, Dict
from uuid import UUID


class ImageDownloader(metaclass=ABCMeta):
    @abstractmethod
    def run(self, image_uid: UUID, **kwargs: Dict[str, Any]):
        """Should download image for input in kwargs."""
        raise NotImplementedError()
