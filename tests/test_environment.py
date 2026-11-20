import numpy as np
import pytest

from tests.conftest import S0, S05, S1, needs_data

pytestmark = needs_data


def _sim(policy, env=S0, seed=3, lam=0.3, horizon=2000):
    from src.environment import Simulation
    from src.experiment import policy_rng, world_for
    from src.policies import build_policy
    w = world_for(env)
    g = w.build_graph()
    sched, _ = w.schedule('train', seed, lam, horizon)
    return w, g, Simulation(w, g, build_policy(policy, w, policy_rng(seed, lam, 'train'), alpha_star=10), sched)


def test_topology_is_sndlib_abilene():
    from src.experiment import world_for
    g = world_for(S0).build_graph()
    assert g.number_of_nodes() == 12 and g.number_of_edges() == 15
    assert g.has_edge('HSTNng', 'KSCYng')
    assert all(0.5 < g[u][v]['delay'] < 12 for u, v in g.edges)


def test_schedule_independent_of_policy_and_seeded():
    from src.experiment import world_for
    w = world_for(S0)
    a, _ = w.schedule('test', 7, 0.2, 3000)
    b, _ = w.schedule('test', 7, 0.2, 3000)
    key = lambda s: [(x.request.src, x.request.dst, x.request.sfc_type, x.request.hidden['r']) for x in s]
    assert key(a) == key(b)
    assert all(x.request.src != x.request.dst for x in a)


def test_speed_factors_follow_protocol():
    from src.experiment import world_for
    k0, k05, k1 = world_for(S0).speed, world_for(S05).speed, world_for(S1).speed
    assert all(v == 1.0 for v in k0.values())
    for k in (k05, k1):
        assert abs(np.mean(np.log(list(k.values())))) < 1e-12           # geometric mean 1
    nodes = sorted(k05)
    assert np.argsort([k05[n] for n in nodes]).tolist() == np.argsort([k1[n] for n in nodes]).tolist()
    assert max(k1.values()) == pytest.approx(5.65, abs=0.01) and min(k05.values()) == pytest.approx(0.42, abs=0.01)
    perm2 = world_for('experiments/envs/s05_perm2.json').speed
    assert sorted(perm2.values()) == pytest.approx(sorted(k05.values())) and perm2 != k05


@pytest.mark.parametrize('policy', ['greedy', 'random', 'smart', 'smart-load', 'cands-prop', 'behaviour', 'oracle',
                                    'oracle-greedy'])
def test_resources_and_load_conserved(policy):
    w, g, sim = _sim(policy)
    lat_ok = []
    sim.observer = lambda now, req, graph, res: lat_ok.append(
        (not res.success) or res.info['proc_delay'] > 0 and res.delay >= res.info['prop_delay'])
    sim.run(until=2000)
    assert sum(r.accepted for r in sim.records) > 0 and all(lat_ok)
    sim.env.run(until=2000 + w.cfg['max_duration'] + 1)               # let every SFC expire
    for n in g.nodes:
        assert g.nodes[n]['cpu_capacity'] == g.nodes[n]['cpu_max']
        assert abs(g.nodes[n]['load']) < 1e-9
    for u, v in g.edges:
        assert abs(g[u][v]['bandwidth'] - g[u][v]['bw_max']) < 1e-9


def test_oracle_never_worse_than_its_own_candidates():
    from src.experiment import policy_rng, world_for
    from src.policies import Oracle
    w = world_for(S05)
    g = w.build_graph()
    sched, _ = w.schedule('train', 1, 0.2, 500)
    o = Oracle(policy_rng(1, 0.2, 'train'), w)
    for item in sched[:30]:
        cands = o.candidates(g, item.request)
        if cands:
            best = o.choose(g, item.request, cands)
            assert w.true_latency(g, best, item.request) == min(w.true_latency(g, c, item.request) for c in cands)
