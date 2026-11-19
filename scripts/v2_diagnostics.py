"""Latency decomposition (propagation vs processing) and kdn2's chosen candidate generators (test split)."""
import argparse
import json
import os
from collections import Counter

import numpy as np
import pandas as pd

from src.v2.experiment import run_single

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--env', default='experiments/v2/env_main.json')
ap.add_argument('--models-dir', default='models/v2/main')
ap.add_argument('--ref', default='results/v2/main')
ap.add_argument('--seeds', type=int, default=10)
a = ap.parse_args()
alpha = json.load(open(os.path.join(a.ref, 'alpha_star.json')))['alpha_star']

rows, gens = [], []
for lam in (0.02, 0.05, 0.1, 0.2, 0.4):
    for pol in ('smart', 'smart-load', 'smart-nowake', 'cands-prop', 'kdn2', 'oracle'):
        acc = []

        def obs(now, req, graph, res):
            if res.success and now >= 1200:
                acc.append((res.info['prop_delay'], res.info['proc_delay'], res.info.get('generator', '')))
        for s in range(1, a.seeds + 1):
            run_single(a.env, pol, s, lam, 'test', 10000, 1200, models_dir=a.models_dir, alpha_star=alpha, observer=obs)
        p = np.array([x[0] for x in acc]); q = np.array([x[1] for x in acc])
        rows.append({'lambda': lam, 'algorithm': pol, 'prop_mean': p.mean(), 'proc_mean': q.mean(),
                     'proc_p95': np.percentile(q, 95), 'proc_share': q.sum() / (p.sum() + q.sum())})
        if pol == 'kdn2':
            c = Counter(x[2] for x in acc)
            gens += [{'lambda': lam, 'generator': g, 'share': n / len(acc)} for g, n in c.items()]
d = pd.DataFrame(rows); g = pd.DataFrame(gens).pivot(index='generator', columns='lambda', values='share').fillna(0)
d.to_csv(os.path.join(a.ref, 'latency_decomposition.csv'), index=False)
g.to_csv(os.path.join(a.ref, 'kdn2_generator_choice.csv'))
with open(os.path.join(a.ref, 'diagnostics.md'), 'w') as f:
    f.write(f"# v2 diagnostics (test split, {a.seeds} seeds)\n\n## Latency decomposition (ms)\n\n")
    f.write(d.to_markdown(index=False, floatfmt='.2f'))
    f.write("\n\n## Which candidate generator kdn2 picked (share of accepted SFCs)\n\n")
    f.write(g.to_markdown(floatfmt='.3f'))
print(open(os.path.join(a.ref, 'diagnostics.md')).read())
