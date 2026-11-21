"""What does each arrival rate lambda mean for the network? Reserved node CPU and full nodes under smart.

Runs smart (test split, 30 seeds, all lambdas). At every arrival after the warm-up it records, before the decision,
the mean share of node CPU that is reserved and the number of nodes whose free CPU is below 30 units (they cannot
host one more VideoTranscoder, the largest VNF). smart ignores kappa, so the numbers are the same for every sigma.

Usage: python -m scripts.load_levels   -> results/load_levels.csv, results/load_levels.md
"""
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from scripts.run import EVAL_SEEDS, HORIZON, LAMBDAS, WARMUP
from src import experiment
from src.sfc import VNF_REQUIREMENTS

ENV = 'experiments/envs/s1.json'
POLICY = 'smart'
BIG_VNF_CPU = max(v['cpu'] for v in VNF_REQUIREMENTS.values())
OUT = 'results'


def _job(args):
    seed, lam = args
    reserved, full = [], []

    def observe(now, req, graph, res):
        if now < WARMUP:
            return
        free = np.array([graph.nodes[n]['cpu_capacity'] for n in graph.nodes])
        cap = np.array([graph.nodes[n]['cpu_max'] for n in graph.nodes])
        reserved.append(float(np.mean(1 - free / cap)))
        full.append(int(np.sum(free < BIG_VNF_CPU)))

    r = experiment.run_single(ENV, POLICY, seed, lam, 'test', HORIZON, WARMUP, observer=observe)
    return {'seed': seed, 'lambda': lam, 'cpu_reserved': 100 * np.mean(reserved),
            'full_nodes': np.mean(full), 'acceptance': r['acceptance']}


def main():
    tasks = [(s, lam) for s in EVAL_SEEDS for lam in LAMBDAS]
    with ProcessPoolExecutor(os.cpu_count()) as ex:
        df = pd.DataFrame(list(ex.map(_job, tasks, chunksize=2)))
    df.to_csv(os.path.join(OUT, 'load_levels.csv'), index=False)

    t = df.groupby('lambda')[['cpu_reserved', 'full_nodes', 'acceptance']].mean()
    lines = [f'# Load levels ({POLICY}, test split, {len(EVAL_SEEDS)} seeds, mean over arrivals after warm-up)', '',
             f'| λ | node CPU reserved (%) | nodes with free CPU < {BIG_VNF_CPU} (of 12) | acceptance (%) |',
             '|---|---|---|---|']
    lines += [f'| {lam:g} | {r.cpu_reserved:.1f} | {r.full_nodes:.1f} | {r.acceptance:.1f} |' for lam, r in t.iterrows()]
    with open(os.path.join(OUT, 'load_levels.md'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
