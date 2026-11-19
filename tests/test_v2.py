import os

import pytest

pytestmark = pytest.mark.skipif(not os.path.exists('data/external/sndlib/abilene.txt'),
                                reason='run scripts/fetch_data.sh first')
ENV = 'experiments/v2/env_main.json'


def _sim(policy, seed=3, lam=0.3, horizon=2000):
    from src.v2.environment import V2Simulation
    from src.v2.experiment import policy_rng, world_for
    from src.v2.policies import build_policy
    w = world_for(ENV)
    g = w.build_graph()
    sched, _ = w.schedule('train', seed, lam, horizon)
    algo = build_policy(policy, w, policy_rng(seed, lam, 'train'), alpha_star=10)
    return w, g, sched, V2Simulation(w, g, algo, sched)


def test_topology_is_sndlib_abilene():
    from src.v2.experiment import world_for
    g = world_for(ENV).build_graph()
    assert g.number_of_nodes() == 12 and g.number_of_edges() == 15
    assert g.has_edge('HSTNng', 'KSCYng') and not g.has_node('DALL')
    assert all(0.5 < g[u][v]['delay'] < 12 for u, v in g.edges)


def test_schedule_independent_of_policy_and_seeded():
    from src.v2.experiment import world_for
    w = world_for(ENV)
    a, _ = w.schedule('test', 7, 0.2, 3000)
    b, _ = w.schedule('test', 7, 0.2, 3000)
    assert [(x.request.src, x.request.dst, x.request.sfc_type, x.request.hidden['r']) for x in a] == \
           [(x.request.src, x.request.dst, x.request.sfc_type, x.request.hidden['r']) for x in b]
    assert all(x.request.src != x.request.dst for x in a)


@pytest.mark.parametrize('policy', ['greedy', 'smart', 'smart-load', 'random', 'behaviour', 'oracle'])
def test_resources_and_load_conserved(policy):
    w, g, sched, sim = _sim(policy)
    lat_ok = []
    sim.observer = lambda now, req, graph, res: lat_ok.append(
        (not res.success) or res.info['proc_delay'] > 0 and res.delay >= res.info['prop_delay'])
    sim.run(until=2000)
    assert sum(r.accepted for r in sim.records) > 0 and all(lat_ok)
    sim.env.run(until=2000 + 601)
    for n in g.nodes:
        assert g.nodes[n]['cpu_capacity'] == g.nodes[n]['cpu_max']
        assert abs(g.nodes[n]['load']) < 1e-9
    for u, v in g.edges:
        assert abs(g[u][v]['bandwidth'] - g[u][v]['bw_max']) < 1e-9


def test_oracle_never_worse_than_its_own_candidates():
    from src.v2.policies import Oracle
    from src.v2.experiment import policy_rng, world_for
    w = world_for(ENV)
    g = w.build_graph()
    sched, _ = w.schedule('train', 1, 0.2, 500)
    o = Oracle(policy_rng(1, 0.2, 'train'), w)
    for item in sched[:30]:
        cands = o.candidates(g, item.request)
        if cands:
            best = o.choose(g, item.request, cands)
            assert w.true_latency(g, best, item.request) == min(w.true_latency(g, c, item.request) for c in cands)
