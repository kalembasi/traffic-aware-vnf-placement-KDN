from abc import ABC, abstractmethod

class BasePlacement(ABC):
    @abstractmethod
    def place_sfc(self, graph, sfc_name):
        """
        Attempt to place an SFC onto the network graph.
        
        :param graph: NetworkX graph object representing the topology.
        :param sfc_name: Name of the SFC string (e.g., 'Web').
        :return: tuple (bool success, list of placements representing (node, vnf, req_cpu, req_ram))
        """
        pass
