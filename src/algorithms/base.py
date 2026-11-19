from abc import ABC, abstractmethod

from src.placement import PlacementResult


class BasePlacement(ABC):
    """A placement policy decides where to host an SFC request. It must NOT modify the graph:
    the simulation engine commits successful results and releases them on expiry."""
    name = 'base'

    @abstractmethod
    def place(self, graph, request) -> PlacementResult:
        ...
