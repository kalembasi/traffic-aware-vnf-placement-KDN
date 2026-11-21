"""Numbers quoted in the paper for greedy, smart and kdn-greedy (sigma = 0 and 1), from results/<env>/runs.csv.

For every (sigma, lambda): mean latency and acceptance of each method, and the paired per-seed gain of kdn-greedy
over smart (smart - kdn-greedy, ms; positive = kdn-greedy faster) with a 95% t-interval over the 30 seeds and the
number of seeds in which kdn-greedy is faster. Also kdn-greedy - oracle-greedy (the cost of predicting instead of
knowing the true delay).

Usage: python -m scripts.paper_tables   -> results/paper_tables.md
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

ENVS = {'s0': 0.0, 's1': 1.0}
METHODS = ['greedy', 'smart', 'kdn-greedy']
OUT = 'results/paper_tables.md'


def paired(t, a, b):
    """Per-lambda paired difference a - b over seeds: mean, 95% t-interval half-width, #seeds with a > b."""
    rows = []
    for lam, g in t.groupby('lambda'):
        d = (g[a] - g[b]).to_numpy()
        h = stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))
        rows.append((lam, d.mean(), h, int((d > 0).sum()), len(d)))
    return rows


def main():
    lines = ['# Paper tables (test split, 30 seeds)', '']
    for env, sigma in ENVS.items():
        df = pd.read_csv(f'results/{env}/runs.csv')
        lat = df.pivot_table(index=['lambda', 'seed'], columns='algorithm', values='lat_mean').reset_index()
        m = df.groupby(['algorithm', 'lambda'])[['lat_mean', 'acceptance', 'decision_ms']].mean()
        lams = sorted(df['lambda'].unique())
        head = '| | ' + ' | '.join(f'λ={lam:g}' for lam in lams) + ' |'
        sep = '|---|' + '---|' * len(lams)
        lines += [f'## σ = {sigma:g}', '', 'Mean latency of accepted SFCs (ms) / acceptance (%) / decision time (ms)',
                  '', head, sep]
        for a in METHODS:
            lines.append(f'| {a} | ' + ' | '.join(
                f'{m.loc[(a, lam), "lat_mean"]:.2f} / {m.loc[(a, lam), "acceptance"]:.1f} / '
                f'{m.loc[(a, lam), "decision_ms"]:.2f}' for lam in lams) + ' |')
        lines += ['', 'Paired gain (ms, mean ± 95% CI half-width, seeds won of 30)', '', head, sep]
        for name, a, b in [('smart − kdn-greedy', 'smart', 'kdn-greedy'),
                           ('greedy − kdn-greedy', 'greedy', 'kdn-greedy'),
                           ('kdn-greedy − oracle-greedy (won = kdn-greedy slower)', 'kdn-greedy', 'oracle-greedy')]:
            cells = [f'{mu:+.2f} ± {h:.2f} ({w}/{n})' for _, mu, h, w, n in paired(lat, a, b)]
            lines.append(f'| {name} | ' + ' | '.join(cells) + ' |')
        rel = [(m.loc[('smart', lam), 'lat_mean'] - m.loc[('kdn-greedy', lam), 'lat_mean'])
               / m.loc[('smart', lam), 'lat_mean'] * 100 for lam in lams]
        lines += ['| relative gain over smart (%) | ' + ' | '.join(f'{x:.1f}' for x in rel) + ' |', '']
    with open(OUT, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
