import copy
import random

import pytest

from src.algorithms import build_algorithm
from src.engine import Simulation, generate_schedule
from src.topology import create_topology
from tests.conftest import V1_MODELS, has_v1_models

MODEL_FREE = ['greedy', 'smart', 'random', 'cands-oracle', 'cands-first', 'cands-random']
ALL = MODEL_FREE + (['kdn', 'kdn-nogate'] if has_v1_models else [])


def make_sim(config, algo_name, seed=1, lam=0.4, end=800):
    cfg = copy.deepcopy(config)
    cfg['simulation']['lambda_rate'] = lam
    random.seed(seed)
    g = create_topology(cfg)
    sched = generate_schedule(cfg['simulation'], end, rng=random)
    checks = []

    def observer(now, req, graph, res):  # graph = state before this decision is committed
        checks.append(all(graph.nodes[n]['cpu_capacity'] >= 0 and graph.nodes[n]['ram_capacity'] >= 0
                          for n in graph.nodes) and all(graph[u][v]['bandwidth'] >= 0 for u, v in graph.edges))
    return Simulation(g, build_algorithm(algo_name, V1_MODELS), schedule=sched, observer=observer), g, checks


@pytest.mark.parametrize('algo', ALL)
def test_resources_conserved_and_never_negative(config, algo):
    end = 800
    sim, g, checks = make_sim(config, algo, end=end)
    sim.run(until=end)
    assert sum(r.accepted for r in sim.records) > 0 and checks and all(checks)
    sim.env.run(until=end + config['simulation']['max_duration'] + 1)  # let every SFC expire
    for n in g.nodes:
        assert g.nodes[n]['cpu_capacity'] == g.nodes[n]['cpu_max']
        assert g.nodes[n]['ram_capacity'] == g.nodes[n]['ram_max']
    for u, v in g.edges:
        assert g[u][v]['bandwidth'] == g[u][v]['bw_max']


@pytest.mark.parametrize('algo', ['greedy', 'random', 'cands-random'])
def test_deterministic_given_seed(config, algo):
    # build-then-run sequentially: algorithms draw from the global RNG seeded per run
    a, _, _ = make_sim(config, algo, seed=5)
    a.run(until=800)
    b, _, _ = make_sim(config, algo, seed=5)
    b.run(until=800)
    strip = lambda s: [(r.req_id, r.accepted, r.latency, r.n_hosts) for r in s.records]
    assert strip(a) == strip(b)
