from abc import ABCMeta, abstractmethod
from typing import Optional

from slidetap.model import Item


class PseudonymFactoryInterface(metaclass=ABCMeta):
    """Metaclass for creating pseudonyms for entities."""

    @abstractmethod
    def create_pseudonym(self, item: Item) -> Optional[str]:
        """
        Create a pseudonym for the given item.

        Parameters
        ----------
        item: Item
            The item to create a pseudonym for.

        Returns
        -------
        Optional[str]
            The created pseudonym, or None if no pseudonym could be created.
        """
        raise NotImplementedError()
