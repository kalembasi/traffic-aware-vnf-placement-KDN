import random

from src.algorithms.base import BasePlacement
from src.placement import build_chain, graph_order


class RandomPlacement(BasePlacement):
    """Each VNF goes to a uniformly random feasible node."""
    name = 'random'

    def __init__(self, rng=None):
        self.rng = rng or random

    def _select(self, hops, state, i):
        hops = list(hops)
        return self.rng.choice(hops) if hops else None

    def place(self, graph, request):
        return build_chain(graph, request.chain, request.bandwidth, self._select, graph_order)
