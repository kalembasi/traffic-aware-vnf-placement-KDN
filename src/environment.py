"""Simulated network (experiments/protocol.md, section 2) and the event-driven simulation (SimPy).

Ground truth that policies cannot see: per-request relative VNF loads (from KDN measurements), node
speed factors kappa_n and the processing-delay function. Telemetry exposes the *measured* node
utilisation (graph.nodes[n]['load'] / cpu_max) and per-request traffic features (packets, flows).

Policies only *propose* a PlacementResult; the simulation commits it, adds the hidden load, measures
the true latency and releases everything when the SFC expires.
"""
import json
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

import networkx as nx
import numpy as np
import simpy

from src.data import haversine_km, load_sndlib_network, load_traffic_matrices, load_vnf_family
from src.placement import PlacementResult, commit, release
from src.sfc import SFC_CATALOG, SFC_CPU, SFCRequest

VNF_FAMILY = {'NAT': 'Firewall', 'Firewall': 'Firewall', 'IDS': 'Snort', 'DPI': 'Snort',
              'TrafficMonitor': 'OVS', 'SBC': 'OVS', 'VideoTranscoder': 'OVS'}
SPLIT_CODES = {'train': 1, 'test': 2}


def node_speed_factors(nodes, sigma, perm_seed):
    """Hidden node speed factor kappa_n = exp(sigma * z_pi(n)), z_i = Phi^-1((i + 0.5) / N) (protocol 2.4)."""
    from scipy.stats import norm
    z = norm.ppf((np.arange(len(nodes)) + 0.5) / len(nodes))
    perm = np.random.default_rng(perm_seed).permutation(len(nodes))
    return {n: float(np.exp(sigma * z[perm[i]])) for i, n in enumerate(nodes)}


def load_env_config(path):
    with open(path) as f:
        return json.load(f)


@dataclass
class ScheduledRequest:
    inter_arrival: float
    request: SFCRequest


class World:
    """Static data shared by all runs of one environment configuration."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.nodes_xy, self.links = load_sndlib_network(cfg['topology'])
        tm = load_traffic_matrices(cfg['tm_dir'], cfg['tm_cache'])
        self.tm_nodes, self.tm, self.tm_times = tm['nodes'], tm['tm'], tm['times']
        days = np.array([t[:8] for t in self.tm_times])
        self.split_idx = {name: np.where((days >= lo) & (days <= hi))[0] for name, (lo, hi) in cfg['splits'].items()}
        self.volume = self.tm.sum(axis=(1, 2))
        self.families = {f: load_vnf_family(cfg['vnf_data'], f) for f in set(VNF_FAMILY.values())}
        for f in self.families.values():
            f['median_cpu'] = float(np.median(f['cpu']))
            order = np.argsort(f['packets'])
            f['sorted_packets'], f['sorted_cpu'] = f['packets'][order], f['cpu'][order]
        # traffic-profile pool = Snort feature batches, split into packet-count terciles per SFC type
        pool = self.families['Snort']
        q1, q2 = np.quantile(pool['packets'], [1 / 3, 2 / 3])
        tercile = np.digitize(pool['packets'], [q1, q2])
        self.pool = pool
        self.pool_idx = {'Web': np.where(tercile == 0)[0], 'VoIP': np.where(tercile == 1)[0],
                         'Video': np.where(tercile == 2)[0]}
        self.speed = node_speed_factors(sorted(self.nodes_xy), cfg['speed_sigma'], cfg['speed_perm_seed'])

    # --- topology -------------------------------------------------------------------------
    def build_graph(self):
        c = self.cfg
        G = nx.Graph()
        for n in self.nodes_xy:
            G.add_node(n, cpu_capacity=c['node_cpu'], ram_capacity=c['node_ram'], cpu_max=c['node_cpu'],
                       ram_max=c['node_ram'], load=0.0)
        for u, v, cap in self.links:
            bw = cap / c['bw_scale']
            G.add_edge(u, v, bandwidth=bw, bw_max=bw,
                       delay=haversine_km(self.nodes_xy[u], self.nodes_xy[v]) * c['us_per_km'] / 1000.0)
        G.graph['paths'] = dict(nx.all_pairs_dijkstra_path(G, weight='delay'))
        G.graph['dist'] = dict(nx.all_pairs_dijkstra_path_length(G, weight='delay'))
        return G

    # --- hidden VNF load --------------------------------------------------------------------
    def relative_load(self, family, packets, rng):
        f = self.families[family]
        k = self.cfg['knn']
        pos = np.searchsorted(f['sorted_packets'], packets)
        lo, hi = max(0, pos - k), min(len(f['sorted_packets']), pos + k)
        cand = np.arange(lo, hi)
        nearest = cand[np.argsort(np.abs(f['sorted_packets'][cand] - packets))[:k]]
        return float(f['sorted_cpu'][rng.choice(nearest)] / f['median_cpu'])

    # --- traffic ----------------------------------------------------------------------------
    def schedule(self, split, seed, lam, horizon):
        """Pre-generate the request stream for one run (identical for every policy)."""
        c = self.cfg
        rng = np.random.default_rng([seed, int(round(lam * 10000)), SPLIT_CODES[split]])
        idx = self.split_idx[split]
        n_int = int(np.ceil(horizon / c['t_per_interval'])) + 1
        start = rng.integers(0, len(idx) - n_int)
        window = idx[start:start + n_int]
        vbar = float(self.volume[idx].mean())
        rates = lam * self.volume[window] / vbar
        lam_max = float(rates.max())
        node_names = self.tm_nodes
        keys = list(SFC_CATALOG.keys())
        out, t, last = [], 0.0, 0.0
        while True:
            t += rng.exponential(1.0 / lam_max)
            if t >= horizon:
                return out, int(window[0])
            k = int(t // c['t_per_interval'])
            if rng.random() > rates[k] / lam_max:  # thinning
                continue
            M = self.tm[window[k]].ravel()
            od = rng.choice(len(M), p=M / M.sum())
            src, dst = node_names[od // len(node_names)], node_names[od % len(node_names)]
            sfc_type = keys[rng.integers(len(keys))]
            duration = int(rng.integers(c['min_duration'], c['max_duration'] + 1))
            b = rng.choice(self.pool_idx[sfc_type])
            packets, flows = float(self.pool['packets'][b]), float(self.pool['flows'][b])
            r = [self.relative_load(VNF_FAMILY[v], packets, rng) for v in SFC_CATALOG[sfc_type]]
            req = SFCRequest(len(out), sfc_type, t, duration, src, dst,
                             features={'packets': packets, 'flows': flows}, hidden={'r': r})
            out.append(ScheduledRequest(t - last, req))
            last = t

    # --- ground-truth latency -----------------------------------------------------------------
    def added_loads(self, res, req):
        """Instantaneous load each placed VNF adds to its host (hidden)."""
        u0 = self.cfg['u0']
        add = {}
        for (node, vnf, cpu, _), r in zip(res.placements, req.hidden['r']):
            add[node] = add.get(node, 0.0) + u0 * cpu * r
        return add

    def vnf_delays(self, graph, res, req):
        """True processing delay of every placed VNF (same order as ``res.placements``)."""
        c = self.cfg
        add = self.added_loads(res, req)
        out = []
        for node, vnf, _, _ in res.placements:
            rho = (graph.nodes[node]['load'] + add[node]) / graph.nodes[node]['cpu_max']
            s = c['service_ms'][vnf] * self.speed[node]
            if c['delay_fn'] == 'mm1':
                out.append(s / (1.0 - min(rho, c['rho_max'])))
            elif c['delay_fn'] == 'linear':
                out.append(s * (1.0 + 4.0 * rho))
            else:
                raise ValueError(c['delay_fn'])
        return out

    def processing_delay(self, graph, res, req):
        return sum(self.vnf_delays(graph, res, req))

    def true_latency(self, graph, res, req):
        return res.delay + self.processing_delay(graph, res, req)


@dataclass
class RequestRecord:
    req_id: int
    arrival: float
    sfc_type: str
    duration: float
    accepted: bool
    latency: float
    n_hosts: int
    decision_ms: float


class Simulation:
    """One run of ``policy`` on ``graph`` over a pre-generated ``schedule``.

    ``observer(now, request, graph, result)`` is called after the decision and BEFORE the result is
    committed, so ``graph`` still holds the pre-decision state.
    """

    def __init__(self, world: World, graph, policy, schedule: List[ScheduledRequest],
                 observer: Optional[Callable] = None):
        self.world, self.graph, self.policy, self.schedule = world, graph, policy, schedule
        self.observer = observer
        self.env = simpy.Environment()
        self.records: List[RequestRecord] = []

    def _arrivals(self):
        for item in self.schedule:
            yield self.env.timeout(item.inter_arrival)
            self._handle(item.request)

    def _release(self, res: PlacementResult, duration):
        yield self.env.timeout(duration)
        release(self.graph, res)
        for n, l in res.info['added_load'].items():
            self.graph.nodes[n]['load'] -= l

    def _handle(self, req: SFCRequest):
        t0 = time.perf_counter()
        res = self.policy.place(self.graph, req)
        dt = (time.perf_counter() - t0) * 1e3
        if res.success:
            res.info['prop_delay'] = res.delay
            res.info['vnf_delays'] = self.world.vnf_delays(self.graph, res, req)
            res.info['proc_delay'] = sum(res.info['vnf_delays'])
            res.delay = res.info['prop_delay'] + res.info['proc_delay']
        if self.observer is not None:
            self.observer(self.env.now, req, self.graph, res)
        if res.success:
            commit(self.graph, res)
            res.info['added_load'] = self.world.added_loads(res, req)
            for n, l in res.info['added_load'].items():
                self.graph.nodes[n]['load'] += l
            self.env.process(self._release(res, req.duration))
        self.records.append(RequestRecord(req.req_id, self.env.now, req.sfc_type, req.duration, res.success,
                                          res.delay if res.success else np.nan, len(set(res.nodes)), dt))

    def run(self, until):
        self.env.process(self._arrivals())
        self.env.run(until=until)
        return self


def summarize(sim: Simulation, warmup=0.0):
    """Per-run metrics over requests arriving at or after ``warmup``."""
    recs = [r for r in sim.records if r.arrival >= warmup]
    acc = [r for r in recs if r.accepted]
    lat = np.array([r.latency for r in acc], dtype=float)
    out = {
        'requests': len(recs),
        'accepted': len(acc),
        'acceptance': 100.0 * len(acc) / len(recs) if recs else np.nan,
        # resource-weighted acceptance: share of requested CPU demand that was admitted
        'cpu_acceptance': 100.0 * sum(SFC_CPU[r.sfc_type] for r in acc) / sum(SFC_CPU[r.sfc_type] for r in recs)
        if recs else np.nan,
        'lat_mean': float(lat.mean()) if len(lat) else np.nan,
        'lat_p50': float(np.percentile(lat, 50)) if len(lat) else np.nan,
        'lat_p95': float(np.percentile(lat, 95)) if len(lat) else np.nan,
        'decision_ms': float(np.mean([r.decision_ms for r in recs])) if recs else np.nan,
    }
    for t in SFC_CATALOG:
        rt = [r for r in recs if r.sfc_type == t]
        at = [r.latency for r in rt if r.accepted]
        out[f'acceptance_{t}'] = 100.0 * len(at) / len(rt) if rt else np.nan
        out[f'lat_mean_{t}'] = float(np.mean(at)) if at else np.nan
    return out
