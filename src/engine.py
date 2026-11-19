"""Event-driven SFC simulation (SimPy).

Traffic either comes from a pre-generated schedule (evaluation: every algorithm sees exactly the
same requests) or is sampled live (data generation, v1 sampling order). The engine owns all
graph mutations: algorithms only *propose* a PlacementResult; the engine commits it and releases
it when the SFC expires.
"""
import random
import time
from dataclasses import asdict, dataclass
from typing import Callable, List, Optional

import numpy as np
import simpy

from src.placement import commit, release
from src.sfc import SFC_CATALOG, SFCRequest


@dataclass
class ScheduledRequest:
    inter_arrival: float
    request: SFCRequest


@dataclass
class RequestRecord:
    req_id: int
    arrival: float
    sfc_type: str
    duration: float
    accepted: bool
    reason: Optional[str]
    latency: float
    n_hosts: int
    decision_ms: float


def generate_schedule(sim_cfg, end_time, rng=random) -> List[ScheduledRequest]:
    """Pre-sample the whole request stream (v1 evaluation order: inter-arrival, type, duration)."""
    lam, keys = sim_cfg['lambda_rate'], list(SFC_CATALOG.keys())
    out, t = [], 0.0
    while True:
        inter = rng.expovariate(lam)
        sfc_type = rng.choice(keys)
        duration = rng.randint(sim_cfg['min_duration'], sim_cfg['max_duration'])
        t += inter
        if t >= end_time:
            return out
        out.append(ScheduledRequest(inter, SFCRequest(len(out), sfc_type, t, duration)))


class Simulation:
    """One simulation run of ``algorithm`` on ``graph``.

    Args:
        schedule: list of ScheduledRequest; if None, requests are sampled live from ``sim_cfg``.
        observer: optional callable(now, request, graph, result) invoked after the decision and
                  BEFORE the result is committed (so ``graph`` still holds the pre-decision state).
        monitor_interval: period for sampling the number of active nodes (None disables).
    """

    def __init__(self, graph, algorithm, schedule=None, sim_cfg=None, rng=random,
                 observer: Optional[Callable] = None, monitor_interval: Optional[float] = 10):
        self.graph, self.algorithm = graph, algorithm
        self.schedule, self.sim_cfg, self.rng = schedule, sim_cfg, rng
        self.observer, self.monitor_interval = observer, monitor_interval
        self.env = simpy.Environment()
        self.records: List[RequestRecord] = []
        self.active_samples = []   # (time, active_node_count)

    # --- processes ------------------------------------------------------------------------
    def _arrivals(self):
        if self.schedule is not None:
            for item in self.schedule:
                yield self.env.timeout(item.inter_arrival)
                self._handle(item.request)
        else:  # live sampling, v1 data-generation order: inter-arrival, (wait), type, duration
            cfg, keys, i = self.sim_cfg, list(SFC_CATALOG.keys()), 0
            while True:
                inter = self.rng.expovariate(cfg['lambda_rate'])
                yield self.env.timeout(inter)
                sfc_type = self.rng.choice(keys)
                duration = self.rng.randint(cfg['min_duration'], cfg['max_duration'])
                self._handle(SFCRequest(i, sfc_type, self.env.now, duration))
                i += 1

    def _release(self, result, duration):
        yield self.env.timeout(duration)
        release(self.graph, result)

    def _monitor(self):
        nodes = self.graph.nodes
        while True:
            yield self.env.timeout(self.monitor_interval)
            active = sum(1 for n in nodes if nodes[n]['cpu_capacity'] < nodes[n]['cpu_max'])
            self.active_samples.append((self.env.now, active))

    def _handle(self, req: SFCRequest):
        t0 = time.perf_counter()
        res = self.algorithm.place(self.graph, req)
        dt = (time.perf_counter() - t0) * 1e3
        if self.observer is not None:
            self.observer(self.env.now, req, self.graph, res)
        if res.success:
            commit(self.graph, res)
            self.env.process(self._release(res, req.duration))
        self.records.append(RequestRecord(req.req_id, self.env.now, req.sfc_type, req.duration,
                                          res.success, res.reason, res.delay if res.success else np.nan,
                                          len(set(res.nodes)), dt))

    # --- run --------------------------------------------------------------------------------
    def run(self, until=None):
        self.env.process(self._arrivals())
        if self.monitor_interval:
            self.env.process(self._monitor())
        self.env.run(until=until)
        return self


def summarize(sim: Simulation, warmup=0.0):
    """Aggregate metrics over requests arriving at or after ``warmup``."""
    recs = [r for r in sim.records if r.arrival >= warmup]
    acc = [r for r in recs if r.accepted]
    lat = np.array([r.latency for r in acc], dtype=float)
    samples = [a for t, a in sim.active_samples if t >= warmup]
    out = {
        'requests': len(recs),
        'accepted': len(acc),
        'acceptance': 100.0 * len(acc) / len(recs) if recs else np.nan,
        'gate_rejects': sum(1 for r in recs if r.reason == 'gate'),
        'lat_mean': float(lat.mean()) if len(lat) else np.nan,
        'lat_p50': float(np.percentile(lat, 50)) if len(lat) else np.nan,
        'lat_p95': float(np.percentile(lat, 95)) if len(lat) else np.nan,
        'active_nodes': float(np.mean(samples)) if samples else np.nan,
        'decision_ms': float(np.mean([r.decision_ms for r in recs])) if recs else np.nan,
    }
    for t in SFC_CATALOG:
        rt = [r for r in recs if r.sfc_type == t]
        at = [r.latency for r in rt if r.accepted]
        out[f'acceptance_{t}'] = 100.0 * len(at) / len(rt) if rt else np.nan
        out[f'lat_mean_{t}'] = float(np.mean(at)) if at else np.nan
    return out


def records_frame(sim: Simulation):
    import pandas as pd
    return pd.DataFrame([asdict(r) for r in sim.records])
