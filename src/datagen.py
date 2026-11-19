"""Telemetry generation: run Greedy under several traffic profiles and log (state, action, outcome)."""
import copy
import random

import pandas as pd

from src.algorithms.greedy import GreedyPlacement
from src.engine import Simulation
from src.features import action_features, network_state
from src.topology import create_topology

TELEMETRY_COLUMNS = [
    'timestamp', 'sfc_type', 'network_active_nodes', 'network_free_cpu', 'network_free_bw',
    'net_max_node_utilization', 'net_bottleneck_bw', 'action_max_path_distance',
    'action_num_unique_nodes', 'outcome_accepted', 'outcome_latency', 'profile',
]


class TelemetryObserver:
    """Records the pre-decision network state, the chosen action and its outcome."""

    def __init__(self, profile):
        self.profile, self.rows = profile, []

    def __call__(self, now, req, graph, res):
        max_path, n_unique = action_features(res)  # (0, 0) when rejected
        self.rows.append([f"{now:.2f}", req.sfc_type, *network_state(graph), max_path, n_unique,
                          int(res.success), res.delay if res.success else 0, self.profile])


def generate(config, seed=2025, algorithm_factory=GreedyPlacement):
    """Returns (telemetry DataFrame, per-profile traffic statistics DataFrame)."""
    random.seed(seed)  # v1: one global RNG drives topology delays and all traffic
    dg = config['data_generation']
    rows, stats = [], []
    for p in dg['profiles']:
        cfg = copy.deepcopy(config)
        cfg['simulation'].update(lambda_rate=p['lambda_rate'], min_duration=p['min_duration'],
                                 max_duration=p['max_duration'])
        graph = create_topology(cfg)
        obs = TelemetryObserver(p['name'])
        sim = Simulation(graph, algorithm_factory(), schedule=None, sim_cfg=cfg['simulation'],
                         rng=random, observer=obs, monitor_interval=None).run(until=dg['end_time'])
        rows += obs.rows
        n = len(sim.records)
        stats.append({'Profile': p['name'], 'Requests': n,
                      'Avg_Inter_Arrival': sim.records[-1].arrival / n if n else 0,
                      'Avg_Duration': sum(r.duration for r in sim.records) / n if n else 0,
                      'Acceptance': sum(r.accepted for r in sim.records) / n if n else 0})
    return pd.DataFrame(rows, columns=TELEMETRY_COLUMNS), pd.DataFrame(stats)
