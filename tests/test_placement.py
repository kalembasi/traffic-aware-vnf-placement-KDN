import random

from src.algorithms.greedy import GreedyPlacement
from src.placement import ResourceState, build_chain, commit, release, route
from src.sfc import SFC_CODES, SFCRequest
from src.topology import create_topology


def snapshot(g):
    return ({n: (g.nodes[n]['cpu_capacity'], g.nodes[n]['ram_capacity']) for n in g.nodes},
            {(u, v): g[u][v]['bandwidth'] for u, v in g.edges})


def test_build_chain_does_not_mutate_graph(config):
    random.seed(0)
    g = create_topology(config)
    before = snapshot(g)
    res = build_chain(g, ['NAT', 'DPI', 'VideoTranscoder'], 50)
    assert res.success and snapshot(g) == before


def test_commit_release_roundtrip(config):
    random.seed(0)
    g = create_topology(config)
    before = snapshot(g)
    algo = GreedyPlacement()
    results = []
    for i in range(30):
        r = algo.place(g, SFCRequest(i, 'VoIP', 0.0, 10))
        if r.success:
            commit(g, r)
            results.append(r)
    assert snapshot(g) != before
    for r in results:
        release(g, r)
    assert snapshot(g) == before


def test_route_respects_bandwidth(config):
    random.seed(0)
    g = create_topology(config)
    st = ResourceState(g)
    edges, _ = route(st, 'SEAT', 'NYCG', 50)
    st.reserve_path(edges, g[edges[0][0]][edges[0][1]]['bandwidth'] - 10)  # leave 10 on the path
    assert route(st, 'SEAT', 'NYCG', 50) is None
    assert route(st, 'SEAT', 'NYCG', 10) is not None


def test_sfc_codes_match_v1_label_encoder():
    assert SFC_CODES == {'Video': 0, 'VoIP': 1, 'Web': 2}
