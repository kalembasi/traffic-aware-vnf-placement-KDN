"""v2 placement policies (protocol section 3). All routes are delay-weighted and run ingress -> VNFs -> egress."""
import os

import numpy as np

from src.algorithms.base import BasePlacement
from src.placement import PlacementResult, build_chain, first_hop, graph_order
from src.v2.features import _net, candidate_features, host_reservations, rho, state_features, vnf_matrix, vnf_rows

W = 'delay'
WAKE_UP_PENALTY = 1000.0


def _chain(graph, req, select=first_hop, order=graph_order):
    return build_chain(graph, req.chain, req.bandwidth, select, order, src=req.src, dst=req.dst, weight=W)


class Greedy2(BasePlacement):
    name = 'greedy'

    def place(self, graph, req):
        return _chain(graph, req)


class Random2(BasePlacement):
    """Each VNF on a uniformly random feasible node."""
    name = 'random'

    def __init__(self, rng):
        self.rng = rng

    def place(self, graph, req):
        def sel(hops, state, i):
            hops = list(hops)
            return hops[self.rng.integers(len(hops))] if hops else None
        return _chain(graph, req, sel)


class Smart2(BasePlacement):
    """Per-VNF score: delay from previous hop (+ delay to egress for the last VNF) + wake-up penalty
    + alpha * measured utilisation of the node. alpha = 0 is the load-unaware smart-v2."""
    name = 'smart'

    def __init__(self, alpha=0.0, wake_up_penalty=WAKE_UP_PENALTY):
        self.alpha, self.wake_up_penalty = alpha, wake_up_penalty

    def place(self, graph, req):
        dist, last = graph.graph['dist'], len(req.chain) - 1

        def sel(hops, state, i):
            def score(h):
                idle = state.free_cpu(h.node) >= state.graph.nodes[h.node]['cpu_max']
                s = h.delay + (self.wake_up_penalty if idle else 0.0) + self.alpha * rho(graph, h.node)
                return s + (dist[h.node][req.dst] if i == last else 0.0)
            return min(hops, key=score, default=None)
        return _chain(graph, req, sel)


class LeastUtilised(BasePlacement):
    name = 'least-util'

    def place(self, graph, req):
        order = sorted(graph.nodes, key=lambda n: rho(graph, n))
        return _chain(graph, req, order=lambda s, p, i: order)


class ColocateFromIngress(BasePlacement):
    name = 'colocate'

    def place(self, graph, req):
        dist = graph.graph['dist']
        return _chain(graph, req, order=lambda s, prev, i: sorted(graph.nodes, key=lambda n: dist[prev][n]))


class ShuffledFirstFit(BasePlacement):
    name = 'shuffled'

    def __init__(self, rng):
        self.rng = rng

    def place(self, graph, req):
        def order(s, prev, i):
            nodes = list(graph.nodes)
            self.rng.shuffle(nodes)
            return nodes
        return _chain(graph, req, order=order)


class CandidatePolicy(BasePlacement):
    """Generates the shared candidate set (protocol section 3) and selects one with ``choose``.

    ``wake_up_penalty`` applies to the smart-based generators: 1000 in v2, 0 in v3."""
    name = 'candidates'
    CANDIDATE_ALPHAS = (2.0, 10.0, 50.0)

    def __init__(self, rng, wake_up_penalty=WAKE_UP_PENALTY):
        p = wake_up_penalty
        self.generators = ([Smart2(0.0, p)] + [Smart2(a, p) for a in self.CANDIDATE_ALPHAS] +
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
                    r.info['generator'] = g.name if not isinstance(g, Smart2) else f'smart-a{g.alpha:g}'
                    out.append(r)
        return out

    def choose(self, graph, req, cands):
        raise NotImplementedError

    def gate(self, graph, req):
        return True

    def place(self, graph, req):
        if not self.gate(graph, req):
            return PlacementResult(False, bw=req.bandwidth, reason='gate')
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


class Oracle(CandidatePolicy):
    """Knows the hidden ground truth: picks the candidate with the lowest true latency."""
    name = 'oracle'

    def __init__(self, rng, world, wake_up_penalty=WAKE_UP_PENALTY):
        super().__init__(rng, wake_up_penalty)
        self.world = world

    def choose(self, graph, req, cands):
        return min(cands, key=lambda c: self.world.true_latency(graph, c, req))


class PropOnly(CandidatePolicy):
    """EXPLORATORY (not pre-registered): lowest *known* propagation delay among the same candidates."""
    name = 'cands-prop'

    def choose(self, graph, req, cands):
        return min(cands, key=lambda c: c.delay)


class KDN2(CandidatePolicy):
    """Lowest (known propagation + predicted processing) delay among the candidates."""
    name = 'kdn2'

    def __init__(self, rng, models_dir, use_gate=False, wake_up_penalty=WAKE_UP_PENALTY):
        super().__init__(rng, wake_up_penalty)
        import xgboost as xgb
        self.regressor = xgb.XGBRegressor()
        self.regressor.load_model(os.path.join(models_dir, 'kdn2_regressor.json'))
        self.regressor.set_params(n_jobs=1)
        self.classifier = None
        if use_gate:
            self.classifier = xgb.XGBClassifier()
            self.classifier.load_model(os.path.join(models_dir, 'kdn2_classifier.json'))
            self.classifier.set_params(n_jobs=1)

    def gate(self, graph, req):
        if self.classifier is None:
            return True
        return bool(self.classifier.predict(np.array([state_features(graph, req)], dtype=float))[0])

    def choose(self, graph, req, cands):
        net = _net(graph)
        X = np.array([candidate_features(graph, req, c, net) for c in cands], dtype=float)
        pred = self.regressor.predict(X)
        total = np.array([c.delay for c in cands]) + pred
        i = int(np.argmin(total))
        cands[i].info['pred_proc'] = float(pred[i])
        return cands[i]


class ModelSelector(CandidatePolicy):
    """v3: analytical selector that knows the M/M/1-style delay formula and the nominal s_v.

    Predicted latency = propagation + sum_v kappa_hat[host] * s_v / (1 - min(rho_hat[host], rho_max)),
    rho_hat = (measured load + u0_hat * CPU reserved by this SFC on the host) / cpu_max.
    ``calibrated=False`` (model-nom) uses kappa_hat = 1; ``True`` (model-cal) uses the per-node fit.
    """
    name = 'model'

    def __init__(self, rng, world, models_dir, calibrated, wake_up_penalty=WAKE_UP_PENALTY):
        super().__init__(rng, wake_up_penalty)
        import json
        with open(os.path.join(models_dir, 'calibration.json')) as f:
            cal = json.load(f)
        self.u0_hat = cal['u0_hat']
        self.kappa = cal['kappa_hat'] if calibrated else {}
        self.service, self.rho_max = world.cfg['service_ms'], world.cfg['rho_max']

    def predict(self, graph, req, res):
        hosts = host_reservations(res)
        total = 0.0
        for node, vnf, _, _ in res.placements:
            rho = (graph.nodes[node]['load'] + self.u0_hat * hosts[node][1]) / graph.nodes[node]['cpu_max']
            total += self.kappa.get(node, 1.0) * self.service[vnf] / (1.0 - min(rho, self.rho_max))
        return total

    def choose(self, graph, req, cands):
        return min(cands, key=lambda c: c.delay + self.predict(graph, req, c))


class KDN3(CandidatePolicy):
    """v3: propagation + sum of per-VNF processing delays predicted by an XGBoost regressor (no formula)."""
    name = 'kdn3'

    def __init__(self, rng, models_dir, wake_up_penalty=WAKE_UP_PENALTY):
        super().__init__(rng, wake_up_penalty)
        import xgboost as xgb
        self.regressor = xgb.XGBRegressor()
        self.regressor.load_model(os.path.join(models_dir, 'kdn3_regressor.json'))
        self.regressor.set_params(n_jobs=1)

    def choose(self, graph, req, cands):
        net_rho = _net(graph)[0]
        rows, owner = [], []
        for i, c in enumerate(cands):
            r = vnf_rows(graph, req, c, net_rho)
            rows += r
            owner += [i] * len(r)
        pred = self.regressor.predict(vnf_matrix(rows))
        proc = np.bincount(owner, weights=pred, minlength=len(cands))
        total = np.array([c.delay for c in cands]) + proc
        i = int(np.argmin(total))
        cands[i].info['pred_proc'] = float(proc[i])
        return cands[i]


def build_policy(name, world, rng, models_dir=None, alpha_star=None):
    p = world.cfg.get('wake_up_penalty', WAKE_UP_PENALTY)   # v2: 1000 (not in config), v3: 0
    if name == 'greedy':
        return Greedy2()
    if name == 'random':
        return Random2(rng)
    if name == 'smart':
        return Smart2(0.0, p)
    if name == 'smart-load':
        if alpha_star is None:
            raise ValueError('smart-load needs alpha_star (tuned on the train split)')
        return Smart2(alpha_star, p)
    if name.startswith('smart-a'):          # used for alpha tuning: smart-a<alpha>
        return Smart2(float(name[len('smart-a'):]), p)
    if name == 'cands-prop':                # v2: exploratory; v3: pre-registered
        return PropOnly(rng, p)
    # --- v2 exploratory (not pre-registered) ---
    if name == 'smart-nowake':
        return Smart2(0.0, wake_up_penalty=0.0)
    if name == 'smart-nowake-load':
        if alpha_star is None:
            raise ValueError('needs alpha_star')
        return Smart2(alpha_star, wake_up_penalty=0.0)
    if name == 'behaviour':
        return Behaviour(rng, p)
    if name == 'oracle':
        return Oracle(rng, world, p)
    if name == 'kdn2':
        return KDN2(rng, models_dir, wake_up_penalty=p)
    if name == 'kdn2-gate':
        return KDN2(rng, models_dir, use_gate=True, wake_up_penalty=p)
    # --- v3 ---
    if name == 'model-nom':
        return ModelSelector(rng, world, models_dir, calibrated=False, wake_up_penalty=p)
    if name == 'model-cal':
        return ModelSelector(rng, world, models_dir, calibrated=True, wake_up_penalty=p)
    if name == 'kdn3':
        return KDN3(rng, models_dir, wake_up_penalty=p)
    raise KeyError(name)
