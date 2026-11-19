"""v2 pipeline (experiments/v2_protocol.md). Sub-commands follow the protocol order:

  datagen  : behaviour-policy telemetry on the train split            (section 4)
  train    : KDN-v2 regressor (+ ablation gate)                         (section 4)
  tune     : grid-search alpha of smart-load on the train split         (section 3)
  evaluate : all policies on the test split, hypotheses H1-H3           (section 5)

Example:
  python -m scripts.v2 datagen  --env experiments/v2/env_main.json --out data/v2/main/telemetry.csv.gz
  python -m scripts.v2 train    --data data/v2/main/telemetry.csv.gz --models-dir models/v2/main
  python -m scripts.v2 tune     --env experiments/v2/env_main.json --out results/v2/main
  python -m scripts.v2 evaluate --env experiments/v2/env_main.json --models-dir models/v2/main --out results/v2/main
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

LAMBDAS = [0.02, 0.05, 0.1, 0.2, 0.4]
HORIZON, WARMUP = 10000, 1200
DATAGEN = dict(lambdas=[0.05, 0.1, 0.2, 0.4], seeds=list(range(1001, 1021)), val_seeds=[1017, 1018, 1019, 1020])
TUNE = dict(seeds=list(range(101, 111)), alphas=[0, 1, 2, 5, 10, 20, 50, 100, 200])
EVAL = dict(seeds=list(range(1, 31)),
            policies=['random', 'greedy', 'smart', 'smart-load', 'oracle', 'kdn2', 'kdn2-gate'])


def cmd_datagen(a):
    from src.v2.experiment import generate_training_data
    t0 = time.time()
    df = generate_training_data(a.env, DATAGEN['seeds'], DATAGEN['lambdas'], HORIZON, jobs=a.jobs)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} rows ({df.accepted.mean():.1%} accepted) -> {a.out} in {time.time() - t0:.0f}s")


def cmd_train(a):
    from src.v2.experiment import train_models
    df = pd.read_csv(a.data)
    print(json.dumps(train_models(df, a.models_dir, DATAGEN['val_seeds']), indent=2))


def cmd_tune(a):
    from src.v2.experiment import run_grid
    pols = [f'smart-a{x:g}' for x in TUNE['alphas']]
    runs = run_grid(a.env, pols, TUNE['seeds'], LAMBDAS, 'train', HORIZON, WARMUP, jobs=a.jobs)
    os.makedirs(a.out, exist_ok=True)
    runs.to_csv(os.path.join(a.out, 'tune_runs.csv'), index=False)
    # protocol: minimise mean latency summed over lambda
    score = runs.groupby(['algorithm', 'lambda'])['lat_mean'].mean().groupby('algorithm').sum()
    table = score.rename('sum_over_lambda_of_mean_latency').reset_index()
    table['alpha'] = table.algorithm.str[len('smart-a'):].astype(float)
    table = table.sort_values('alpha')
    best = float(table.loc[table.sum_over_lambda_of_mean_latency.idxmin(), 'alpha'])
    table.to_csv(os.path.join(a.out, 'tune_summary.csv'), index=False)
    with open(os.path.join(a.out, 'alpha_star.json'), 'w') as f:
        json.dump({'alpha_star': best}, f)
    print(table.to_string(index=False)); print('alpha* =', best)


def cmd_evaluate(a):
    from src.v2.experiment import run_grid
    from src.v2.analysis import write_report
    with open(os.path.join(a.out, 'alpha_star.json')) as f:
        alpha_star = json.load(f)['alpha_star']
    lambdas = [float(x) for x in a.lambdas.split(',')] if a.lambdas else LAMBDAS
    t0 = time.time()
    runs = run_grid(a.env, EVAL['policies'], EVAL['seeds'], lambdas, 'test', HORIZON, WARMUP,
                    models_dir=a.models_dir, alpha_star=alpha_star, jobs=a.jobs)
    runs.to_csv(os.path.join(a.out, 'runs.csv'), index=False)
    write_report(runs, a.out, title=f"v2 evaluation ({a.env}), alpha*={alpha_star:g}")
    print(f"{len(runs)} runs in {time.time() - t0:.0f}s -> {a.out}")


def cmd_explore(a):
    """EXPLORATORY ablations (not in the pre-registered protocol), test split, same seeds/lambdas."""
    from src.v2.experiment import run_grid
    from src.experiment import paired_tests, summarize_runs, write_markdown
    with open(os.path.join(a.ref, 'alpha_star.json')) as f:
        alpha_star = json.load(f)['alpha_star']
    pols = a.policies.split(',')
    runs = run_grid(a.env, pols, EVAL['seeds'], LAMBDAS, 'test', HORIZON, WARMUP,
                    models_dir=a.models_dir, alpha_star=alpha_star, jobs=a.jobs)
    ref_runs = pd.read_csv(os.path.join(a.ref, 'runs.csv'))
    allr = pd.concat([ref_runs, runs[~runs.algorithm.isin(ref_runs.algorithm.unique())]], ignore_index=True)
    os.makedirs(a.out, exist_ok=True)
    runs.to_csv(os.path.join(a.out, 'runs.csv'), index=False)
    s = summarize_runs(allr)
    write_markdown(s, os.path.join(a.out, 'summary.md'), 'EXPLORATORY ablations (not pre-registered) + main policies')
    s.to_csv(os.path.join(a.out, 'summary.csv'), index=False)
    pd.concat([paired_tests(allr, 'kdn2', m) for m in ('lat_mean', 'lat_p95', 'cpu_acceptance')]).to_csv(
        os.path.join(a.out, 'paired_vs_kdn2.csv'), index=False)
    print(s.pivot(index='algorithm', columns='lambda', values='lat_mean_mean').round(2).to_string())
    print(s.pivot(index='algorithm', columns='lambda', values='cpu_acceptance_mean').round(2).to_string())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('datagen'); p.add_argument('--env', required=True); p.add_argument('--out', required=True)
    p.add_argument('--jobs', type=int, default=10)
    p = sub.add_parser('train'); p.add_argument('--data', required=True); p.add_argument('--models-dir', required=True)
    p = sub.add_parser('tune'); p.add_argument('--env', required=True); p.add_argument('--out', required=True)
    p.add_argument('--jobs', type=int, default=10)
    p = sub.add_parser('evaluate'); p.add_argument('--env', required=True); p.add_argument('--models-dir', required=True)
    p.add_argument('--out', required=True); p.add_argument('--jobs', type=int, default=10)
    p.add_argument('--lambdas', default=None, help='comma-separated subset (sensitivity runs)')
    p = sub.add_parser('explore'); p.add_argument('--env', required=True); p.add_argument('--models-dir', required=True)
    p.add_argument('--ref', required=True, help='dir with the pre-registered runs.csv and alpha_star.json')
    p.add_argument('--out', required=True); p.add_argument('--policies', required=True); p.add_argument('--jobs', type=int, default=10)
    a = ap.parse_args()
    {'explore': cmd_explore, 'datagen': cmd_datagen, 'train': cmd_train, 'tune': cmd_tune, 'evaluate': cmd_evaluate}[a.cmd](a)


if __name__ == '__main__':
    main()
