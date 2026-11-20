"""Shared placement core: tentative resource accounting, routing, chain construction, commit/release.

Every policy is expressed as a *per-VNF host ordering + selection rule* on top of ``build_chain``.
Feasibility checks, routing, bandwidth accounting and rollback live only here.
"""
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Tuple

from src.sfc import VNF_REQUIREMENTS

Edge = Tuple[str, str]


def _ekey(u, v):
    return (u, v) if u <= v else (v, u)


class ResourceState:
    """Copy-free overlay of tentative reservations on top of the live graph."""

    def __init__(self, graph):
        self.graph = graph
        self.cpu, self.ram, self.bw = {}, {}, {}

    def free_cpu(self, n):
        return self.graph.nodes[n]['cpu_capacity'] - self.cpu.get(n, 0)

    def free_ram(self, n):
        return self.graph.nodes[n]['ram_capacity'] - self.ram.get(n, 0)

    def free_bw(self, u, v):
        return self.graph[u][v]['bandwidth'] - self.bw.get(_ekey(u, v), 0)

    def reserve_node(self, n, cpu, ram):
        self.cpu[n] = self.cpu.get(n, 0) + cpu
        self.ram[n] = self.ram.get(n, 0) + ram

    def reserve_path(self, edges, bw):
        for u, v in edges:
            k = _ekey(u, v)
            self.bw[k] = self.bw.get(k, 0) + bw


@dataclass
class Hop:
    """One feasible host for the next VNF, together with the route from the previous hop."""
    node: str
    edges: List[Edge]
    delay: float


@dataclass
class PlacementResult:
    success: bool
    placements: list = field(default_factory=list)   # [(node, vnf, cpu, ram)]
    paths: list = field(default_factory=list)        # [[(u, v), ...]] non-empty route segments
    delay: float = 0.0                                # propagation delay; the simulation adds processing delay
    bw: float = 0.0
    reason: Optional[str] = None                      # 'infeasible' when not successful
    info: dict = field(default_factory=dict)          # policy-specific diagnostics

    @property
    def nodes(self):
        return [p[0] for p in self.placements]


def route(state: ResourceState, src, dst, bw):
    """Delay-weighted shortest path from src to dst (precomputed in ``graph.graph['paths']``).

    Returns (edges, delay) or None if any edge lacks ``bw`` free bandwidth.
    """
    if src == dst:
        return [], 0.0
    path = state.graph.graph['paths'][src][dst]
    edges = list(zip(path[:-1], path[1:]))
    if any(state.free_bw(u, v) < bw for u, v in edges):
        return None
    return edges, sum(state.graph[u][v]['delay'] for u, v in edges)


def feasible_hosts(state: ResourceState, vnf, prev_node, bw, node_order: Iterable[str]):
    """Yield every node (in ``node_order``) that can host ``vnf`` and be reached from ``prev_node``."""
    req = VNF_REQUIREMENTS[vnf]
    for node in node_order:
        if state.free_cpu(node) >= req['cpu'] and state.free_ram(node) >= req['ram']:
            r = route(state, prev_node, node, bw)
            if r is not None:
                yield Hop(node, r[0], r[1])


# Selector signature: (hops_iterator, state, vnf_index) -> Hop | None
Selector = Callable[[Iterable[Hop], ResourceState, int], Optional[Hop]]
# Ordering signature: (state, prev_node, vnf_index) -> list of nodes
Ordering = Callable[[ResourceState, Optional[str], int], List[str]]


def graph_order(state, prev_node, i):
    return list(state.graph.nodes())


def first_hop(hops, state, i):
    return next(iter(hops), None)


def build_chain(graph, req, select: Selector = first_hop, order: Ordering = graph_order) -> PlacementResult:
    """Route ``req`` from its ingress through its VNFs (placed one by one) to its egress.

    Works on a tentative overlay and does NOT modify ``graph``. ``delay`` is the total propagation delay.
    """
    state = ResourceState(graph)
    bw = req.bandwidth
    placements, paths, delay, prev = [], [], 0.0, req.src
    for i, vnf in enumerate(req.chain):
        hop = select(feasible_hosts(state, vnf, prev, bw, order(state, prev, i)), state, i)
        if hop is None:
            return PlacementResult(False, bw=bw, reason='infeasible')
        need = VNF_REQUIREMENTS[vnf]
        state.reserve_node(hop.node, need['cpu'], need['ram'])
        state.reserve_path(hop.edges, bw)
        placements.append((hop.node, vnf, need['cpu'], need['ram']))
        if hop.edges:
            paths.append(hop.edges)
        delay += hop.delay
        prev = hop.node
    r = route(state, prev, req.dst, bw)
    if r is None:
        return PlacementResult(False, bw=bw, reason='infeasible')
    if r[0]:
        state.reserve_path(r[0], bw)
        paths.append(r[0])
    delay += r[1]
    return PlacementResult(True, placements, paths, delay, bw)


def commit(graph, res: PlacementResult):
    for node, _, cpu, ram in res.placements:
        graph.nodes[node]['cpu_capacity'] -= cpu
        graph.nodes[node]['ram_capacity'] -= ram
    for edges in res.paths:
        for u, v in edges:
            graph[u][v]['bandwidth'] -= res.bw


def release(graph, res: PlacementResult):
    for node, _, cpu, ram in res.placements:
        graph.nodes[node]['cpu_capacity'] += cpu
        graph.nodes[node]['ram_capacity'] += ram
    for edges in res.paths:
        for u, v in edges:
            graph[u][v]['bandwidth'] += res.bw
