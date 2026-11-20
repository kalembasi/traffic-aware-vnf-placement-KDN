"""Data ablation: does the result depend on the KDN VNF measurements or the Abilene traffic matrices?

Re-runs sigma = 1 (test split, 30 seeds, all lambdas) with greedy, smart and oracle-greedy in four worlds:
  base     the normal simulator
  noKDN    every VNF load factor r = 1 (KDN CPU measurements unused; random stream kept identical)
  noTM     constant arrival rate and uniform source/destination pairs (Abilene matrices unused)
  neither  both of the above
oracle-greedy stands in for kdn-greedy so that no model has to be retrained per world; on the base world the
two agree within 0.2 ms at every lambda (results/s1/summary.csv).

Usage: python -m scripts.ablation_data   -> results/ablation_data.csv, results/ablation_data.md
"""
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from scripts.run import EVAL_SEEDS, HORIZON, LAMBDAS, WARMUP
from src import experiment
from src.environment import World, load_env_config

ENV = 'experiments/envs/s1.json'
POLICIES = ['greedy', 'smart', 'oracle-greedy']
OUT = 'results'


class NoKDN(World):
    """Every VNF load factor r = 1. The original draw is still made so the request stream stays identical."""

    def relative_load(self, family, packets, rng):
        super().relative_load(family, packets, rng)
        return 1.0


class NoTM(World):
    """Constant arrival rate and uniform source/destination pairs instead of the Abilene traffic matrices."""

    def __init__(self, cfg):
        super().__init__(cfg)
        n = len(self.tm_nodes)
        uniform = np.ones((n, n)) - np.eye(n)
        self.tm = np.broadcast_to(uniform, self.tm.shape)
        self.volume = np.full(len(self.volume), uniform.sum())


class Neither(NoKDN, NoTM):
    pass


VARIANTS = {'base': World, 'noKDN': NoKDN, 'noTM': NoTM, 'neither': Neither}


def _job(args):
    variant, policy, seed, lam = args
    if variant not in experiment._WORLDS:
        experiment._WORLDS[variant] = VARIANTS[variant](load_env_config(ENV))
    r = experiment.run_single(variant, policy, seed, lam, 'test', HORIZON, WARMUP)
    return {'variant': variant, 'algorithm': policy, 'seed': seed, 'lambda': lam,
            'acceptance': r['acceptance'], 'lat_mean': r['lat_mean']}


def main():
    tasks = [(v, p, s, lam) for v in VARIANTS for p in POLICIES for s in EVAL_SEEDS for lam in LAMBDAS]
    with ProcessPoolExecutor(os.cpu_count()) as ex:
        df = pd.DataFrame(list(ex.map(_job, tasks, chunksize=4)))
    df.to_csv(os.path.join(OUT, 'ablation_data.csv'), index=False)

    t = df.pivot_table(index=['variant', 'lambda'], columns='algorithm', values='lat_mean')
    gain = (t['smart'] - t['oracle-greedy']).unstack('lambda').loc[list(VARIANTS)]
    lines = ['# Data ablation (sigma = 1, 30 test seeds)', '',
             'Mean latency gain of oracle-greedy over smart (ms; positive = oracle-greedy faster).', '',
             '| variant | ' + ' | '.join(f'λ={lam:g}' for lam in gain.columns) + ' |',
             '|---|' + '---|' * len(gain.columns)]
    lines += [f'| {v} | ' + ' | '.join(f'{x:+.2f}' for x in row) + ' |' for v, row in gain.iterrows()]
    lines += ['', f'Largest change vs base: {(gain - gain.loc["base"]).abs().max().max():.2f} ms.']
    with open(os.path.join(OUT, 'ablation_data.md'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
