"""One concrete placement decision (test split) shown from every policy's point of view -> docs/worked_example.json"""
import json

import numpy as np

from src.v2.environment import V2Simulation
from src.v2.experiment import policy_rng, world_for
from src.v2.features import CANDIDATE_FEATURES, candidate_features, rho
from src.v2.policies import KDN2, Smart2

ENV, SEED, LAM, AT = 'experiments/v2/env_main.json', 3, 0.1, 3000.0
w = world_for(ENV)
g = w.build_graph()
sched, _ = w.schedule('test', SEED, LAM, 10000)
kdn = KDN2(policy_rng(SEED, LAM, 'test'), 'models/v2/main')
snap = {}


def obs(now, req, graph, res):
    # capture the first VNF-heavy request after AT with >= 4 distinct candidates
    if snap or now < AT or req.sfc_type != 'Video':
        return
    cands = kdn.candidates(graph, req)
    if len({round(c.delay, 3) for c in cands}) < 4:
        return
    X = np.array([candidate_features(graph, req, c) for c in cands])
    pred = kdn.regressor.predict(X)
    smart = Smart2(0.0).place(graph, req)
    snap.update({
        'time': now, 'sfc': req.sfc_type, 'chain': req.chain, 'src': req.src, 'dst': req.dst,
        'packets': req.features['packets'], 'flows': req.features['flows'], 'hidden_r': req.hidden['r'],
        'node_rho': {n: round(rho(graph, n), 3) for n in graph.nodes},
        'smart_v2_choice': smart.nodes,
        'candidates': [{'generator': c.info['generator'], 'hosts': c.nodes, 'prop_ms': round(c.delay, 2),
                        'pred_proc_ms': round(float(p), 2),
                        'true_proc_ms': round(w.processing_delay(graph, c, req), 2),
                        'features': dict(zip(CANDIDATE_FEATURES, [round(float(v), 3) for v in x]))}
                       for c, p, x in zip(cands, pred, X)]})


V2Simulation(w, g, kdn, sched, observer=obs).run(until=AT + 500)
for c in snap['candidates']:
    c['kdn_score'] = round(c['prop_ms'] + c['pred_proc_ms'], 2)
    c['true_total'] = round(c['prop_ms'] + c['true_proc_ms'], 2)
json.dump(snap, open('docs/worked_example.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in snap.items() if k not in ('candidates', 'node_rho')}, indent=1))
for c in snap['candidates']:
    print(c['generator'], c['hosts'], c['prop_ms'], c['pred_proc_ms'], c['true_proc_ms'], c['kdn_score'], c['true_total'])
