"""v2 environment (experiments/v2_protocol.md, section 2).

Ground truth that policies cannot see: per-request relative VNF loads (from KDN measurements)
and the processing-delay function. Telemetry exposes the *measured* node utilisation
(graph.nodes[n]['load'] / cpu_max) and per-request traffic features (packets, flows).
"""
import json
import os
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from src.engine import ScheduledRequest, Simulation, RequestRecord
from src.placement import commit, release
from src.sfc import SFC_CATALOG, SFCRequest
from src.v2.data import (haversine_km, load_sndlib_network, load_traffic_matrices, load_vnf_family)

VNF_FAMILY = {'NAT': 'Firewall', 'Firewall': 'Firewall', 'IDS': 'Snort', 'DPI': 'Snort',
              'TrafficMonitor': 'OVS', 'SBC': 'OVS', 'VideoTranscoder': 'OVS'}
SPLIT_CODES = {'train': 1, 'test': 2}


def load_env_config(path):
    with open(path) as f:
        return json.load(f)


class V2World:
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
        G.graph['sp_cache'] = {'delay': dict(nx.all_pairs_dijkstra_path(G, weight='delay'))}
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
            req = SFCRequest(len(out), sfc_type, t, duration, src=src, dst=dst)
            req.features = {'packets': packets, 'flows': flows}
            req.hidden = {'r': r}
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

    def processing_delay(self, graph, res, req):
        c = self.cfg
        add = self.added_loads(res, req)
        total = 0.0
        for node, vnf, _, _ in res.placements:
            rho = (graph.nodes[node]['load'] + add[node]) / graph.nodes[node]['cpu_max']
            s = c['service_ms'][vnf]
            if c['delay_fn'] == 'mm1':
                total += s / (1.0 - min(rho, c['rho_max']))
            elif c['delay_fn'] == 'linear':
                total += s * (1.0 + 4.0 * rho)
            else:
                raise ValueError(c['delay_fn'])
        return total

    def true_latency(self, graph, res, req):
        return res.delay + self.processing_delay(graph, res, req)


class V2Simulation(Simulation):
    """Simulation whose accepted SFCs add hidden load and are measured with the true latency."""

    def __init__(self, world, graph, algorithm, schedule, observer=None, monitor_interval=10):
        super().__init__(graph, algorithm, schedule=schedule, observer=observer, monitor_interval=monitor_interval)
        self.world = world

    def _release(self, result, duration):
        yield self.env.timeout(duration)
        release(self.graph, result)
        for n, l in result.info['added_load'].items():
            self.graph.nodes[n]['load'] -= l

    def _handle(self, req):
        import time
        t0 = time.perf_counter()
        res = self.algorithm.place(self.graph, req)
        dt = (time.perf_counter() - t0) * 1e3
        if res.success:
            res.info['prop_delay'] = res.delay
            res.info['proc_delay'] = self.world.processing_delay(self.graph, res, req)
            res.delay = res.info['prop_delay'] + res.info['proc_delay']
        if self.observer is not None:
            self.observer(self.env.now, req, self.graph, res)
        if res.success:
            commit(self.graph, res)
            res.info['added_load'] = self.world.added_loads(res, req)
            for n, l in res.info['added_load'].items():
                self.graph.nodes[n]['load'] += l
            self.env.process(self._release(res, req.duration))
        self.records.append(RequestRecord(req.req_id, self.env.now, req.sfc_type, req.duration,
                                          res.success, res.reason, res.delay if res.success else np.nan,
                                          len(set(res.nodes)), dt))
