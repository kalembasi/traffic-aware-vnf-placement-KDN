"""Two-stage KDN placement: XGBoost gatekeeper (admission) + candidate generation + selection.

The selection rule is configurable so that ablations share exactly the same candidate generator:
  'regressor' : lowest latency predicted by the XGBoost regressor (the v1 method)
  'oracle'    : lowest *true* latency of the candidate (known at decision time in the v1 model)
  'first'     : first feasible candidate (i.e. the co-location candidate when it is feasible)
  'random'    : uniformly random feasible candidate
"""
import os
import random

import numpy as np

from src.algorithms.base import BasePlacement
from src.features import action_features, state_vector
from src.placement import PlacementResult, build_chain, first_hop

SELECTORS = ('regressor', 'oracle', 'first', 'random')


class KDNPlacement(BasePlacement):
    name = 'kdn'

    def __init__(self, models_dir='models', gatekeeper=True, selector='regressor', n_candidates=5, rng=None,
                 n_jobs=1):
        if selector not in SELECTORS:
            raise ValueError(f"selector must be one of {SELECTORS}")
        self.gatekeeper, self.selector, self.n_candidates = gatekeeper, selector, n_candidates
        self.rng = rng or random
        self.classifier = self.regressor = None
        if gatekeeper or selector == 'regressor':
            import xgboost as xgb
            if gatekeeper:
                self.classifier = xgb.XGBClassifier()
                self.classifier.load_model(os.path.join(models_dir, 'kdn_classifier.json'))
            if selector == 'regressor':
                self.regressor = xgb.XGBRegressor()
                self.regressor.load_model(os.path.join(models_dir, 'kdn_regressor.json'))
            for m in (self.classifier, self.regressor):
                if m is not None:
                    m.set_params(n_jobs=n_jobs)  # tiny batches: threading only adds overhead

    # --- candidate generation (identical to v1) ---------------------------------------------
    def _colocate_first(self, state, prev, i):
        nodes = list(state.graph.nodes())
        if prev is not None:
            nodes.remove(prev)
            nodes.insert(0, prev)
        return nodes

    def _shuffled(self, state, prev, i):
        nodes = list(state.graph.nodes())
        self.rng.shuffle(nodes)
        return nodes

    def candidates(self, graph, request):
        out = []
        for k in range(self.n_candidates):
            order = self._colocate_first if k == 0 else self._shuffled
            res = build_chain(graph, request.chain, request.bandwidth, first_hop, order)
            if res.success:
                res.info['candidate_idx'] = k
                out.append(res)
        return out

    # --- decision ---------------------------------------------------------------------------
    def place(self, graph, request):
        state = state_vector(graph, request.sfc_type)
        if self.gatekeeper and self.classifier.predict(np.array([state]))[0] == 0:
            return PlacementResult(False, bw=request.bandwidth, reason='gate')

        cands = self.candidates(graph, request)
        if not cands:
            return PlacementResult(False, bw=request.bandwidth, reason='infeasible')

        if self.selector == 'regressor':
            X = np.array([state + action_features(c) for c in cands], dtype=float)
            preds = self.regressor.predict(X)
            best = cands[int(np.argmin(preds))]
            best.info['predicted_latency'] = float(preds.min())
            best.info['cand_preds'] = preds.tolist()
        elif self.selector == 'oracle':
            best = min(cands, key=lambda c: c.delay)
        elif self.selector == 'first':
            best = cands[0]
        else:
            best = self.rng.choice(cands)
        best.info['n_candidates'] = len(cands)
        best.info['cand_delays'] = [c.delay for c in cands]   # diagnostics: true latency of every candidate
        return best
