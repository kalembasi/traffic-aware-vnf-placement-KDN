"""Experiment pipeline (experiments/protocol.md).

  run      : telemetry -> train/calibrate -> tune alpha -> evaluate, for one environment   (sections 3-5, 7)
  analyze  : pre-registered hypotheses across sigma levels + sensitivity S1/S2           (sections 5-7)

Example:
  python -m scripts.run run --name s05
  python -m scripts.run analyze
"""
import argparse
import json
import os
import time

import pandas as pd

LAMBDAS = [0.02, 0.05, 0.1, 0.2, 0.4]
HORIZON, WARMUP = 10000, 1200
TELEMETRY = dict(lambdas=[0.05, 0.1, 0.2, 0.4], seeds=list(range(1001, 1021)), val_seeds=[1017, 1018, 1019, 1020])
TUNE = dict(seeds=list(range(101, 111)), alphas=[0, 1, 2, 5, 10, 20, 50, 100, 200])
EVAL_SEEDS = list(range(1, 31))
SELECTORS = ['random', 'greedy', 'smart', 'smart-load', 'cands-prop', 'model-nom', 'model-cal', 'kdn', 'oracle']
GREEDY = ['kdn-greedy', 'model-cal-greedy', 'oracle-greedy']
MAIN = {'s0': 0.0, 's025': 0.25, 's05': 0.5, 's1': 1.0}     # all policies
SENS = {'s05_linear': 0.5, 's05_perm2': 0.5}                # SELECTORS only (protocol section 7)


def paths(name):
    return f'experiments/envs/{name}.json', f'data/telemetry/{name}.csv.gz', f'models/{name}', f'results/{name}'


def cmd_run(a):
    from src.analysis import summarize_runs, write_markdown
    from src.experiment import generate_telemetry, run_grid, train_models, world_for
    env, data, models, out = paths(a.name)
    for d in (os.path.dirname(data), models, out):
        os.makedirs(d, exist_ok=True)
    t0 = time.time()
    if not os.path.exists(data):
        df = generate_telemetry(env, TELEMETRY['seeds'], TELEMETRY['lambdas'], HORIZON, jobs=a.jobs)
        df.to_csv(data, index=False)
        print(f'[{a.name}] telemetry: {len(df)} VNF rows, {time.time() - t0:.0f}s', flush=True)
    df = pd.read_csv(data)
    m = train_models(df, models, TELEMETRY['val_seeds'], world_for(env))
    with open(os.path.join(out, 'training_metrics.json'), 'w') as f:
        json.dump(m, f, indent=2)
    print(f'[{a.name}] train: ' + json.dumps({k: m[k] for k in ('u0_hat', 'kdn', 'model-nom', 'model-cal')}), flush=True)

    pols = [f'smart-a{x:g}' for x in TUNE['alphas']]
    tune = run_grid(env, pols, TUNE['seeds'], LAMBDAS, 'train', HORIZON, WARMUP, jobs=a.jobs)
    tune.to_csv(os.path.join(out, 'tune_runs.csv'), index=False)
    score = tune.groupby(['algorithm', 'lambda'])['lat_mean'].mean().groupby('algorithm').sum()
    table = score.rename('sum_over_lambda_of_mean_latency').reset_index()
    table['alpha'] = table.algorithm.str[len('smart-a'):].astype(float)
    table = table.sort_values('alpha')
    alpha_star = float(table.loc[table.sum_over_lambda_of_mean_latency.idxmin(), 'alpha'])
    table.to_csv(os.path.join(out, 'tune_summary.csv'), index=False)
    with open(os.path.join(out, 'alpha_star.json'), 'w') as f:
        json.dump({'alpha_star': alpha_star}, f)
    print(f'[{a.name}] tune: alpha* = {alpha_star:g}', flush=True)

    policies = SELECTORS + (GREEDY if a.name in MAIN else [])
    runs = run_grid(env, policies, EVAL_SEEDS, LAMBDAS, 'test', HORIZON, WARMUP,
                    models_dir=models, alpha_star=alpha_star, jobs=a.jobs)
    runs.to_csv(os.path.join(out, 'runs.csv'), index=False)
    s = summarize_runs(runs)
    s.to_csv(os.path.join(out, 'summary.csv'), index=False)
    write_markdown(s, os.path.join(out, 'summary.md'), f'{a.name} ({env}), alpha*={alpha_star:g}')
    print(f'[{a.name}] evaluate: {len(runs)} runs, total {time.time() - t0:.0f}s', flush=True)
    print(s.pivot(index='algorithm', columns='lambda', values='lat_mean_mean').round(2).to_string(), flush=True)


def cmd_analyze(a):
    from src.analysis import HYPOTHESES, REPORTED, SENSITIVITY, hypotheses
    load = lambda n, s: pd.read_csv(os.path.join(paths(n)[3], 'runs.csv')).assign(env=n, sigma=s)
    h = hypotheses(pd.concat([load(n, s) for n, s in MAIN.items()], ignore_index=True), HYPOTHESES + REPORTED)
    h.to_csv('results/hypotheses.csv', index=False)
    sens = pd.concat([hypotheses(load(n, s), SENSITIVITY).assign(env=n) for n, s in SENS.items()], ignore_index=True)
    sens.to_csv('results/hypotheses_sensitivity.csv', index=False)
    with open('results/hypotheses.md', 'w') as f:
        f.write('# Pre-registered hypotheses (Holm across the 20 sigma x lambda cells per hypothesis)\n\n')
        f.write(h.to_markdown(index=False, floatfmt='.4g'))
        f.write('\n\n# Sensitivity (sigma = 0.5; Holm across the 5 lambda values per hypothesis and variant)\n\n')
        f.write(sens.to_markdown(index=False, floatfmt='.4g'))
        f.write('\n')
    print(h[h.hypothesis.str.startswith('H')].pivot_table(index=['hypothesis', 'sigma'], columns='lambda',
                                                         values='mean_diff').round(2).to_string())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('run')
    p.add_argument('--name', required=True, choices=[*MAIN, *SENS])
    p.add_argument('--jobs', type=int, default=os.cpu_count())
    sub.add_parser('analyze')
    a = ap.parse_args()
    {'run': cmd_run, 'analyze': cmd_analyze}[a.cmd](a)


if __name__ == '__main__':
    main()
