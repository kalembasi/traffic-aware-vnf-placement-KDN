from src.algorithms.base import BasePlacement
from src.placement import build_chain, first_hop, graph_order


class GreedyPlacement(BasePlacement):
    """First-fit: each VNF goes to the first node (fixed node order) that fits and is reachable."""
    name = 'greedy'

    def place(self, graph, request):
        return build_chain(graph, request.chain, request.bandwidth, first_hop, graph_order)
