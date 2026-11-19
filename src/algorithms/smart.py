from src.algorithms.base import BasePlacement
from src.placement import build_chain, graph_order


class SmartPlacement(BasePlacement):
    """Per-VNF greedy scoring: score = path delay from previous VNF + penalty for waking an idle node.

    Ties are broken by the fixed node order (same as a stable sort in v1).
    """
    name = 'smart'

    def __init__(self, wake_up_penalty=1000):
        self.wake_up_penalty = wake_up_penalty

    def _select(self, hops, state, i):
        def score(h):
            idle = state.free_cpu(h.node) >= state.graph.nodes[h.node]['cpu_max']
            return h.delay + (self.wake_up_penalty if idle else 0)
        return min(hops, key=score, default=None)

    def place(self, graph, request):
        return build_chain(graph, request.chain, request.bandwidth, self._select, graph_order)
