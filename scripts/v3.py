"""v3 pipeline (experiments/v3_protocol.md).

  run      : datagen -> train/calibrate -> tune alpha -> evaluate, for one environment   (sections 3-5)
  analyze  : pre-registered hypotheses H1-H4 across sigma levels + sensitivity S1/S2     (sections 5-6)

Example:
  python -m scripts.v3 run --name s05 --env experiments/v3/env_s05.json
  python -m scripts.v3 analyze
"""
import argparse
import json
import os
import time

import pandas as pd

LAMBDAS = [0.02, 0.05, 0.1, 0.2, 0.4]
HORIZON, WARMUP = 10000, 1200
DATAGEN = dict(lambdas=[0.05, 0.1, 0.2, 0.4], seeds=list(range(1001, 1021)), val_seeds=[1017, 1018, 1019, 1020])
TUNE = dict(seeds=list(range(101, 111)), alphas=[0, 1, 2, 5, 10, 20, 50, 100, 200])
EVAL = dict(seeds=list(range(1, 31)),
            policies=['random', 'greedy', 'smart', 'smart-load', 'cands-prop', 'model-nom', 'model-cal', 'kdn3',
                      'oracle'])
MAIN = {'s0': 0.0, 's025': 0.25, 's05': 0.5, 's1': 1.0}
SENS = ['s05_linear', 's05_perm2']


def paths(name):
    return (f'data/v3/{name}/vnf_telemetry.csv.gz', f'models/v3/{name}', f'results/v3/{name}')


def cmd_run(a):
    from src.v2.experiment import generate_vnf_telemetry, run_grid, train_v3, world_for
    from src.experiment import summarize_runs, write_markdown
    data, models, out = paths(a.name)
    for d in (os.path.dirname(data), models, out):
        os.makedirs(d, exist_ok=True)
    t0 = time.time()
    if not os.path.exists(data):
        df = generate_vnf_telemetry(a.env, DATAGEN['seeds'], DATAGEN['lambdas'], HORIZON, jobs=a.jobs)
        df.to_csv(data, index=False)
        print(f'[{a.name}] datagen: {len(df)} VNF rows, {time.time() - t0:.0f}s', flush=True)
    df = pd.read_csv(data)
    m = train_v3(df, models, DATAGEN['val_seeds'], world_for(a.env))
    print(f'[{a.name}] train: ' + json.dumps({k: m[k] for k in ('u0_hat', 'kdn3', 'model-nom', 'model-cal')}), flush=True)

    pols = [f'smart-a{x:g}' for x in TUNE['alphas']]
    tune = run_grid(a.env, pols, TUNE['seeds'], LAMBDAS, 'train', HORIZON, WARMUP, jobs=a.jobs)
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

    runs = run_grid(a.env, EVAL['policies'], EVAL['seeds'], LAMBDAS, 'test', HORIZON, WARMUP,
                    models_dir=models, alpha_star=alpha_star, jobs=a.jobs)
    runs.to_csv(os.path.join(out, 'runs.csv'), index=False)
    s = summarize_runs(runs)
    s.to_csv(os.path.join(out, 'summary.csv'), index=False)
    write_markdown(s, os.path.join(out, 'summary.md'), f'v3 {a.name} ({a.env}), alpha*={alpha_star:g}')
    print(f'[{a.name}] evaluate: {len(runs)} runs, total {time.time() - t0:.0f}s', flush=True)
    print(s.pivot(index='algorithm', columns='lambda', values='lat_mean_mean').round(2).to_string(), flush=True)


def cmd_analyze(a):
    from src.v2.analysis import hypotheses_v3
    main = pd.concat([pd.read_csv(os.path.join(paths(n)[2], 'runs.csv')).assign(env=n, sigma=s)
                      for n, s in MAIN.items()], ignore_index=True)
    h = hypotheses_v3(main)
    h.to_csv('results/v3/hypotheses.csv', index=False)
    sens = []
    for n in SENS:
        p = os.path.join(paths(n)[2], 'runs.csv')
        if os.path.exists(p):
            sens.append(hypotheses_v3(pd.read_csv(p).assign(env=n, sigma=0.5)).assign(env=n))
    if sens:
        pd.concat(sens).to_csv('results/v3/hypotheses_sensitivity.csv', index=False)
    with open('results/v3/hypotheses.md', 'w') as f:
        f.write('# v3 pre-registered hypotheses (Holm across the 20 sigma x lambda cells per hypothesis)\n\n')
        f.write(h.to_markdown(index=False, floatfmt='.4g'))
        if sens:
            f.write('\n\n# Sensitivity (sigma = 0.5; Holm across the 5 lambda values per hypothesis and variant)\n\n')
            f.write(pd.concat(sens).to_markdown(index=False, floatfmt='.4g'))
        f.write('\n')
    print(h[h.hypothesis.str.startswith('H')].pivot_table(index=['hypothesis', 'sigma'], columns='lambda',
                                                         values='mean_diff').round(2).to_string())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('run'); p.add_argument('--name', required=True); p.add_argument('--env', required=True)
    p.add_argument('--jobs', type=int, default=10)
    sub.add_parser('analyze')
    a = ap.parse_args()
    {'run': cmd_run, 'analyze': cmd_analyze}[a.cmd](a)


if __name__ == '__main__':
    main()
