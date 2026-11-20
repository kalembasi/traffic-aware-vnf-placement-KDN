"""Summary tables and the pre-registered hypothesis tests (protocol sections 5-7)."""
import numpy as np
import pandas as pd
from scipy import stats

METRICS = ['acceptance', 'cpu_acceptance', 'lat_mean', 'lat_p95', 'decision_ms']

# (label, a, b): every cell is the paired difference a - b of the mean latency
HYPOTHESES = [('H1', 'kdn', 'smart-load'), ('H2', 'kdn', 'model-nom'), ('H3', 'kdn', 'model-cal'),
              ('H4', 'kdn', 'cands-prop'), ('H5', 'kdn-greedy', 'smart-load'), ('H6', 'kdn-greedy', 'kdn')]
REPORTED = [('gap', 'kdn', 'oracle'), ('vs-smart', 'kdn', 'smart'),
            ('gap-greedy', 'kdn-greedy', 'oracle-greedy'), ('vs-model-cal-greedy', 'kdn-greedy', 'model-cal-greedy')]
SENSITIVITY = [h for h in HYPOTHESES if h[0] in ('H1', 'H2', 'H3', 'H4')] + REPORTED[:2]


def summarize_runs(runs, metrics=METRICS):
    """Mean, sample std and 95% t-CI half-width over seeds per (lambda, algorithm)."""
    rows = []
    for (lam, algo), g in runs.groupby(['lambda', 'algorithm'], sort=False):
        r = {'lambda': lam, 'algorithm': algo, 'n_seeds': len(g)}
        for m in metrics:
            x = g[m].dropna().to_numpy(dtype=float)
            n = len(x)
            r[f'{m}_mean'] = x.mean() if n else np.nan
            r[f'{m}_std'] = x.std(ddof=1) if n > 1 else np.nan
            r[f'{m}_ci95'] = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def write_markdown(summary, path, title):
    lines = [f"# {title}", "", "Mean ± sample std over seeds (95% CI half-width in brackets).", ""]
    for lam, g in summary.groupby('lambda', sort=False):
        lines += [f"## lambda = {lam}", "",
                  "| Algorithm | Seeds | Acceptance (%) | CPU-weighted acc. (%) | Latency mean (ms) | Latency p95 (ms) | Decision (ms) |",
                  "|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            f = lambda m, d=2: f"{r[m + '_mean']:.{d}f} ± {r[m + '_std']:.{d}f} [{r[m + '_ci95']:.{d}f}]"
            lines.append(f"| {r['algorithm']} | {r['n_seeds']} | {f('acceptance')} | {f('cpu_acceptance')} | "
                         f"{f('lat_mean')} | {f('lat_p95')} | {f('decision_ms', 3)} |")
        lines.append("")
    with open(path, 'w') as fh:
        fh.write('\n'.join(lines))


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


def _ci(d):
    n = len(d)
    h = stats.t.ppf(0.975, n - 1) * d.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return d.mean() - h, d.mean() + h


def _wilcoxon(d):
    if len(d) < 6 or not np.any(d != 0):
        return 1.0
    return float(stats.wilcoxon(d, alternative='two-sided').pvalue)


def hypotheses(runs, comparisons):
    """Paired two-sided Wilcoxon over seeds per (sigma, lambda) cell, Holm across all cells of a hypothesis.

    Comparisons whose label does not start with 'H' are reported without a test.
    """
    rows = []
    for hyp, a, b in comparisons:
        cells = []
        for (sigma, lam), g in runs.groupby(['sigma', 'lambda']):
            p = g.pivot(index='seed', columns='algorithm', values='lat_mean')
            cells.append((sigma, lam, (p[a] - p[b]).dropna()))
        raw = [_wilcoxon(d) for *_, d in cells]
        adj = holm(raw)
        for (sigma, lam, d), pr, pa in zip(cells, raw, adj):
            lo, hi = _ci(d)
            tested = hyp.startswith('H')
            rows.append({'hypothesis': hyp, 'sigma': sigma, 'lambda': lam, 'comparison': f'{a} - {b}',
                         'mean_diff': d.mean(), 'ci95_lo': lo, 'ci95_hi': hi, 'n_lower': int((d < 0).sum()),
                         'n_higher': int((d > 0).sum()), 'p': pr if tested else np.nan,
                         'p_holm': pa if tested else np.nan,
                         'result': ('' if not tested else 'no significant difference' if pa >= 0.05
                                    else f'{a} better' if d.mean() < 0 else f'{b} better')})
    return pd.DataFrame(rows)
