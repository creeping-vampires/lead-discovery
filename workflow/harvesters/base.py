"""
Base harvester interface for lead discovery.
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class BaseHarvester(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def harvest(self) -> List[Dict[str, any]]:
        """
        Gathers raw prospect records from the source.
        Returns a list of dictionaries with raw lead data.
        """
        pass

