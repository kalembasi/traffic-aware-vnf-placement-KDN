"""Pre-registered analysis (protocol section 5): summary table, hypotheses H1-H3, oracle gap."""
import os

import numpy as np
import pandas as pd
from scipy import stats

from src.experiment import summarize_runs, write_markdown


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (same order as input)."""
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = running
    return adj


def _paired(runs, a, b, metric):
    out = []
    for lam, g in runs.groupby('lambda'):
        p = g.pivot(index='seed', columns='algorithm', values=metric)
        d = (p[a] - p[b]).dropna()
        out.append((lam, d))
    return out


def _ci(d):
    n = len(d)
    h = stats.t.ppf(0.975, n - 1) * d.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return d.mean() - h, d.mean() + h


def _wilcoxon(d, alternative):
    if len(d) < 6 or not np.any(d != 0):
        return 1.0
    return float(stats.wilcoxon(d, alternative=alternative).pvalue)


def hypotheses(runs):
    rows = []
    for hyp, a, b, metric, alt in [('H1', 'kdn2', 'smart', 'lat_mean', 'less'),
                                   ('H2', 'kdn2', 'smart-load', 'lat_mean', 'two-sided')]:
        res = _paired(runs, a, b, metric)
        raw = [_wilcoxon(d, alt) for _, d in res]
        for (lam, d), p, padj in zip(res, raw, holm(raw)):
            lo, hi = _ci(d)
            rows.append({'hypothesis': hyp, 'lambda': lam, 'comparison': f'{a} - {b}', 'metric': metric,
                         'mean_diff': d.mean(), 'ci95_lo': lo, 'ci95_hi': hi, 'n_lower': int((d < 0).sum()),
                         'n_higher': int((d > 0).sum()), 'alternative': alt, 'p': p, 'p_holm': padj,
                         'supported': bool(padj < 0.05 and (alt != 'less' or d.mean() < 0))})
    for lam, d in _paired(runs, 'kdn2', 'smart', 'cpu_acceptance'):
        lo, hi = _ci(d)
        rows.append({'hypothesis': 'H3', 'lambda': lam, 'comparison': 'kdn2 - smart', 'metric': 'cpu_acceptance',
                     'mean_diff': d.mean(), 'ci95_lo': lo, 'ci95_hi': hi, 'n_lower': int((d < 0).sum()),
                     'n_higher': int((d > 0).sum()), 'alternative': 'non-inferiority margin -1 pp',
                     'p': np.nan, 'p_holm': np.nan, 'supported': bool(lo > -1.0) if not np.isnan(lo) else True})
    for metric in ('lat_mean', 'lat_p95'):
        for lam, d in _paired(runs, 'kdn2', 'oracle', metric):
            lo, hi = _ci(d)
            rows.append({'hypothesis': 'gap', 'lambda': lam, 'comparison': 'kdn2 - oracle', 'metric': metric,
                         'mean_diff': d.mean(), 'ci95_lo': lo, 'ci95_hi': hi, 'n_lower': int((d < 0).sum()),
                         'n_higher': int((d > 0).sum()), 'alternative': '', 'p': np.nan, 'p_holm': np.nan,
                         'supported': np.nan})
    return pd.DataFrame(rows)


def write_report(runs, out, title):
    os.makedirs(out, exist_ok=True)
    summary = summarize_runs(runs)
    summary.to_csv(os.path.join(out, 'summary.csv'), index=False)
    write_markdown(summary, os.path.join(out, 'summary.md'), title)
    h = hypotheses(runs)
    h.to_csv(os.path.join(out, 'hypotheses.csv'), index=False)
    with open(os.path.join(out, 'summary.md'), 'a') as f:
        f.write('\n## Pre-registered hypotheses\n\n')
        f.write(h.to_markdown(index=False, floatfmt='.4g'))
        f.write('\n')
    return summary, h
