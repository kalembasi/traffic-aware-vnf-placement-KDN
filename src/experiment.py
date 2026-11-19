"""Experiment grid runner: algorithms x seeds x arrival rates, every algorithm sees the same traffic."""
import copy
import json
import os
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy import stats

from src.algorithms import build_algorithm
from src.engine import Simulation, generate_schedule, records_frame, summarize
from src.topology import create_topology

_ALGO_CACHE = {}


def run_single(base_config, algo_name, seed, lam, end_time, warmup=0.0, models_dir='models',
               return_records=False):
    """One run. v1 protocol: seed -> topology delays -> traffic schedule -> simulate."""
    cfg = copy.deepcopy(base_config)
    cfg['simulation']['lambda_rate'] = lam
    cfg['simulation']['end_time'] = end_time
    random.seed(seed)
    graph = create_topology(cfg)
    schedule = generate_schedule(cfg['simulation'], end_time, rng=random)
    key = (algo_name, models_dir)
    if key not in _ALGO_CACHE:
        _ALGO_CACHE[key] = build_algorithm(algo_name, models_dir)
    sim = Simulation(graph, _ALGO_CACHE[key], schedule=schedule).run(until=end_time)
    row = {'algorithm': algo_name, 'seed': seed, 'lambda': lam, **summarize(sim, warmup)}
    if return_records:
        rec = records_frame(sim).assign(algorithm=algo_name, seed=seed, **{'lambda': lam})
        return row, rec
    return row, None


def _job(args):
    return run_single(*args)


def run_grid(exp, jobs=1):
    with open(exp.get('base_config', 'config/config.json')) as f:
        base = json.load(f)
    tasks = [(base, a, s, lam, exp['end_time'], exp.get('warmup', 0.0), exp.get('models_dir', 'models'),
              exp.get('save_requests', False))
             for lam in exp['lambdas'] for s in exp['seeds'] for a in exp['algorithms']]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            out = list(ex.map(_job, tasks, chunksize=max(1, len(tasks) // (jobs * 4))))
    else:
        out = [_job(t) for t in tasks]
    runs = pd.DataFrame([r for r, _ in out])
    recs = pd.concat([r for _, r in out if r is not None], ignore_index=True) if exp.get('save_requests') else None
    return runs, recs


METRICS = ['acceptance', 'cpu_acceptance', 'lat_mean', 'lat_p95', 'active_nodes', 'decision_ms', 'gate_rejects']


def summarize_runs(runs, metrics=METRICS):
    """Mean, sample std (ddof=1), population std (ddof=0, as in v1) and 95% t-CI per algorithm/lambda."""
    rows = []
    for (lam, algo), g in runs.groupby(['lambda', 'algorithm'], sort=False):
        r = {'lambda': lam, 'algorithm': algo, 'n_seeds': len(g)}
        for m in metrics:
            x = g[m].dropna().to_numpy(dtype=float)
            n = len(x)
            r[f'{m}_mean'] = x.mean() if n else np.nan
            r[f'{m}_std'] = x.std(ddof=1) if n > 1 else np.nan
            r[f'{m}_std0'] = x.std(ddof=0) if n else np.nan
            h = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
            r[f'{m}_ci95'] = h
        rows.append(r)
    return pd.DataFrame(rows)


def paired_tests(runs, reference, metric='lat_mean'):
    """Paired (same seed, same lambda) Wilcoxon signed-rank test of every algorithm vs ``reference``."""
    rows = []
    for lam, g in runs.groupby('lambda'):
        p = g.pivot(index='seed', columns='algorithm', values=metric)
        if reference not in p:
            continue
        for algo in p.columns:
            if algo == reference:
                continue
            d = (p[algo] - p[reference]).dropna()
            pval = stats.wilcoxon(d).pvalue if len(d) >= 6 and np.any(d != 0) else np.nan
            rows.append({'lambda': lam, 'metric': metric, 'algorithm': algo, 'reference': reference,
                         'mean_diff': d.mean(), 'n': len(d), 'n_lower': int((d < 0).sum()),
                         'n_higher': int((d > 0).sum()), 'p_wilcoxon': pval})
    return pd.DataFrame(rows)


def write_markdown(summary, path, title):
    lines = [f"# {title}", "", "Mean ± sample std over seeds (95% CI half-width in brackets).", ""]
    for lam, g in summary.groupby('lambda', sort=False):
        lines += [f"## lambda = {lam}", "",
                  "| Algorithm | Seeds | Acceptance (%) | CPU-weighted acc. (%) | Latency mean (ms) | Latency p95 (ms) | Active nodes | Decision (ms) |",
                  "|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            f = lambda m, d=2: f"{r[m + '_mean']:.{d}f} ± {r[m + '_std']:.{d}f} [{r[m + '_ci95']:.{d}f}]"
            lines.append(f"| {r['algorithm']} | {r['n_seeds']} | {f('acceptance')} | {f('cpu_acceptance')} | {f('lat_mean')} | "
                         f"{f('lat_p95')} | {f('active_nodes')} | {f('decision_ms', 3)} |")
        lines.append("")
    with open(path, 'w') as fh:
        fh.write('\n'.join(lines))
