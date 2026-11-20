import pytest

from src.placement import ResourceState, build_chain, commit, release, route
from src.policies import Greedy
from tests.conftest import S0, needs_data

pytestmark = needs_data


def _world_and_requests(n=30):
    from src.experiment import world_for
    w = world_for(S0)
    sched, _ = w.schedule('train', 1, 0.2, 2000)
    return w, [x.request for x in sched[:n]]


def snapshot(g):
    return ({n: (g.nodes[n]['cpu_capacity'], g.nodes[n]['ram_capacity']) for n in g.nodes},
            {(u, v): g[u][v]['bandwidth'] for u, v in g.edges})


def test_build_chain_does_not_mutate_graph():
    w, reqs = _world_and_requests(1)
    g = w.build_graph()
    before = snapshot(g)
    res = build_chain(g, reqs[0])
    assert res.success and snapshot(g) == before
    assert res.delay >= g.graph['dist'][reqs[0].src][reqs[0].dst] - 1e-12   # detour through the VNFs


def test_commit_release_roundtrip():
    w, reqs = _world_and_requests()
    g = w.build_graph()
    before = snapshot(g)
    results = []
    for req in reqs:
        r = Greedy().place(g, req)
        if r.success:
            commit(g, r)
            results.append(r)
    assert results and snapshot(g) != before
    for r in results:
        release(g, r)
    assert all(abs(a - b) < 1e-9 for a, b in zip(snapshot(g)[1].values(), before[1].values()))
    assert snapshot(g)[0] == before[0]


def test_route_respects_bandwidth():
    w, _ = _world_and_requests(0)
    g = w.build_graph()
    st = ResourceState(g)
    src, dst = 'STTLng', 'NYCMng'
    edges, delay = route(st, src, dst, 50)
    assert delay == pytest.approx(g.graph['dist'][src][dst])
    st.reserve_path(edges, min(g[u][v]['bandwidth'] for u, v in edges) - 10)   # leave 10 on the bottleneck
    assert route(st, src, dst, 50) is None
    assert route(st, src, dst, 10) is not None
