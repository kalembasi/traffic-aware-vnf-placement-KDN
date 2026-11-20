"""Placement policies (protocol section 3). Routes are delay-weighted and run ingress -> VNFs -> egress.

A policy decides where to host an SFC request and must NOT modify the graph: the simulation commits
a successful result and releases it when the SFC expires.
"""
import json
import os

import numpy as np

from src.features import host_reservations, net_rho, rho, vnf_matrix, vnf_rows
from src.placement import PlacementResult, build_chain, graph_order
from src.sfc import VNF_REQUIREMENTS


class Policy:
    name = 'policy'

    def place(self, graph, req) -> PlacementResult:
        raise NotImplementedError


# --- heuristics ---------------------------------------------------------------------------------
class Greedy(Policy):
    """First-fit: each VNF on the first feasible node in a fixed node order."""
    name = 'greedy'

    def place(self, graph, req):
        return build_chain(graph, req)


class Random(Policy):
    """Each VNF on a uniformly random feasible node."""
    name = 'random'

    def __init__(self, rng):
        self.rng = rng

    def place(self, graph, req):
        def sel(hops, state, i):
            hops = list(hops)
            return hops[self.rng.integers(len(hops))] if hops else None
        return build_chain(graph, req, sel)


class Smart(Policy):
    """Per-VNF score: delay from the previous hop (+ delay to the egress for the last VNF)
    + alpha * measured utilisation of the node. alpha = 0 is the load-unaware smart heuristic."""
    name = 'smart'

    def __init__(self, alpha=0.0):
        self.alpha = alpha

    def place(self, graph, req):
        dist, last = graph.graph['dist'], len(req.chain) - 1

        def sel(hops, state, i):
            def score(h):
                s = h.delay + self.alpha * rho(graph, h.node)
                return s + (dist[h.node][req.dst] if i == last else 0.0)
            return min(hops, key=score, default=None)
        return build_chain(graph, req, sel)


class LeastUtilised(Policy):
    name = 'least-util'

    def place(self, graph, req):
        order = sorted(graph.nodes, key=lambda n: rho(graph, n))
        return build_chain(graph, req, order=lambda s, p, i: order)


class ColocateFromIngress(Policy):
    name = 'colocate'

    def place(self, graph, req):
        dist = graph.graph['dist']
        return build_chain(graph, req, order=lambda s, prev, i: sorted(graph.nodes, key=lambda n: dist[prev][n]))


class ShuffledFirstFit(Policy):
    name = 'shuffled'

    def __init__(self, rng):
        self.rng = rng

    def place(self, graph, req):
        def order(s, prev, i):
            nodes = list(graph.nodes)
            self.rng.shuffle(nodes)
            return nodes
        return build_chain(graph, req, order=order)


# --- selectors over a shared candidate set --------------------------------------------------------
class CandidatePolicy(Policy):
    """Generates the shared candidate set (at most 8 distinct placements) and selects one with ``choose``."""
    name = 'candidates'
    CANDIDATE_ALPHAS = (2.0, 10.0, 50.0)

    def __init__(self, rng):
        self.generators = ([Smart(0.0)] + [Smart(a) for a in self.CANDIDATE_ALPHAS] +
                           [LeastUtilised(), ColocateFromIngress(), ShuffledFirstFit(rng), ShuffledFirstFit(rng)])
        self.rng = rng

    def candidates(self, graph, req):
        out, seen = [], set()
        for g in self.generators:
            r = g.place(graph, req)
            if r.success:
                key = tuple(r.nodes)
                if key not in seen:
                    seen.add(key)
                    r.info['generator'] = g.name if not isinstance(g, Smart) else f'smart-a{g.alpha:g}'
                    out.append(r)
        return out

    def choose(self, graph, req, cands):
        raise NotImplementedError

    def place(self, graph, req):
        cands = self.candidates(graph, req)
        if not cands:
            return PlacementResult(False, bw=req.bandwidth, reason='infeasible')
        best = self.choose(graph, req, cands)
        best.info['n_candidates'] = len(cands)
        return best


class Behaviour(CandidatePolicy):
    """Data-collection policy: uniform random choice among the candidates."""
    name = 'behaviour'

    def choose(self, graph, req, cands):
        return cands[self.rng.integers(len(cands))]


class PropOnly(CandidatePolicy):
    """Lowest known propagation delay among the candidates (no load information)."""
    name = 'cands-prop'

    def choose(self, graph, req, cands):
        return min(cands, key=lambda c: c.delay)


class Oracle(CandidatePolicy):
    """Knows the hidden ground truth: picks the candidate with the lowest true latency."""
    name = 'oracle'

    def __init__(self, rng, world):
        super().__init__(rng)
        self.world = world

    def choose(self, graph, req, cands):
        return min(cands, key=lambda c: self.world.true_latency(graph, c, req))


class ModelSelector(CandidatePolicy):
    """Analytical selector that knows the delay formula and the nominal service times s_v.

    Predicted latency = propagation + sum_v kappa_hat[host] * s_v / (1 - min(rho_hat[host], rho_max)),
    rho_hat = (measured load + u0_hat * CPU reserved by this SFC on the host) / cpu_max.
    ``calibrated=False`` (model-nom) uses kappa_hat = 1; ``True`` (model-cal) uses the per-node fit.
    """
    name = 'model'

    def __init__(self, rng, world, models_dir, calibrated):
        super().__init__(rng)
        with open(os.path.join(models_dir, 'calibration.json')) as f:
            cal = json.load(f)
        self.u0_hat = cal['u0_hat']
        self.kappa = cal['kappa_hat'] if calibrated else {}
        self.service, self.rho_max = world.cfg['service_ms'], world.cfg['rho_max']

    def predict(self, graph, req, res):
        hosts = host_reservations(res)
        total = 0.0
        for node, vnf, _, _ in res.placements:
            r = (graph.nodes[node]['load'] + self.u0_hat * hosts[node][1]) / graph.nodes[node]['cpu_max']
            total += self.kappa.get(node, 1.0) * self.service[vnf] / (1.0 - min(r, self.rho_max))
        return total

    def choose(self, graph, req, cands):
        return min(cands, key=lambda c: c.delay + self.predict(graph, req, c))


def load_regressor(models_dir):
    import xgboost as xgb
    reg = xgb.XGBRegressor()
    reg.load_model(os.path.join(models_dir, 'kdn_regressor.json'))
    reg.set_params(n_jobs=1)   # tiny batches: threading only adds overhead
    return reg


def kdn_scorer(models_dir):
    """Predicted processing delay of each (partial) placement: sum of the regressor's per-VNF predictions."""
    reg = load_regressor(models_dir)

    def score(graph, req, placements):
        network_rho = net_rho(graph)
        rows, owner = [], []
        for i, p in enumerate(placements):
            r = vnf_rows(graph, req, p, network_rho)
            rows += r
            owner += [i] * len(r)
        return np.bincount(owner, weights=reg.predict(vnf_matrix(rows)), minlength=len(placements))
    return score


class KDN(CandidatePolicy):
    """Propagation + sum of per-VNF processing delays predicted by an XGBoost regressor (no formula)."""
    name = 'kdn'

    def __init__(self, rng, models_dir):
        super().__init__(rng)
        self.scorer = kdn_scorer(models_dir)

    def choose(self, graph, req, cands):
        proc = self.scorer(graph, req, cands)
        total = np.array([c.delay for c in cands]) + proc
        i = int(np.argmin(total))
        cands[i].info['pred_proc'] = float(proc[i])
        return cands[i]


# --- the model builds the placement (protocol section 7) -----------------------------------------
class GreedyModel(Policy):
    """Each VNF goes to the feasible node with the lowest propagation from the previous hop + predicted
    processing delay of the partial chain (+ delay to the egress for the last VNF).

    ``scorer(graph, req, partials) -> processing delay of each partial placement``.
    """
    name = 'greedy-model'

    def __init__(self, scorer):
        self.scorer = scorer

    def place(self, graph, req):
        dist, last, placed = graph.graph['dist'], len(req.chain) - 1, []

        def sel(hops, state, i):
            hops = list(hops)
            if not hops:
                return None
            vnf = req.chain[i]
            need = VNF_REQUIREMENTS[vnf]
            parts = [PlacementResult(True, placed + [(h.node, vnf, need['cpu'], need['ram'])]) for h in hops]
            proc = self.scorer(graph, req, parts)
            score = [h.delay + p + (dist[h.node][req.dst] if i == last else 0.0) for h, p in zip(hops, proc)]
            best = hops[int(np.argmin(score))]
            placed.append((best.node, vnf, need['cpu'], need['ram']))
            return best
        return build_chain(graph, req, sel, graph_order)


def build_policy(name, world, rng, models_dir=None, alpha_star=None):
    if name == 'greedy':
        return Greedy()
    if name == 'random':
        return Random(rng)
    if name == 'smart':
        return Smart(0.0)
    if name == 'smart-load':
        if alpha_star is None:
            raise ValueError('smart-load needs alpha_star (tuned on the train split)')
        return Smart(alpha_star)
    if name.startswith('smart-a'):          # alpha tuning: smart-a<alpha>
        return Smart(float(name[len('smart-a'):]))
    if name == 'behaviour':
        return Behaviour(rng)
    if name == 'cands-prop':
        return PropOnly(rng)
    if name == 'oracle':
        return Oracle(rng, world)
    if name == 'model-nom':
        return ModelSelector(rng, world, models_dir, calibrated=False)
    if name == 'model-cal':
        return ModelSelector(rng, world, models_dir, calibrated=True)
    if name == 'kdn':
        return KDN(rng, models_dir)
    if name == 'kdn-greedy':
        return GreedyModel(kdn_scorer(models_dir))
    if name == 'model-cal-greedy':
        m = ModelSelector(rng, world, models_dir, calibrated=True)
        return GreedyModel(lambda g, req, parts: [m.predict(g, req, x) for x in parts])
    if name == 'oracle-greedy':
        return GreedyModel(lambda g, req, parts: [world.processing_delay(g, x, req) for x in parts])
    raise KeyError(name)
