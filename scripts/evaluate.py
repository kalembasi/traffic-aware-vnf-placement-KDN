"""Usage: python -m scripts.evaluate --exp experiments/v1.json --out results/v1 [--jobs 8]"""
import argparse
import json
import os
import time

import pandas as pd

from src.experiment import paired_tests, run_grid, summarize_runs, write_markdown


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--exp', required=True, help='experiment JSON')
    ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', type=int, default=1)
    a = ap.parse_args()

    with open(a.exp) as f:
        exp = json.load(f)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    runs, recs = run_grid(exp, jobs=a.jobs)
    runs.to_csv(os.path.join(a.out, 'runs.csv'), index=False)
    if recs is not None:
        recs.to_csv(os.path.join(a.out, 'requests.csv.gz'), index=False)
    summary = summarize_runs(runs)
    summary.to_csv(os.path.join(a.out, 'summary.csv'), index=False)
    write_markdown(summary, os.path.join(a.out, 'summary.md'), exp.get('name', a.exp))
    ref = exp.get('reference')
    if ref:
        tests = [paired_tests(runs, ref, m) for m in ('lat_mean', 'lat_p95', 'acceptance', 'cpu_acceptance')]
        pd.concat(tests).to_csv(os.path.join(a.out, 'paired_tests.csv'), index=False)
    with open(os.path.join(a.out, 'experiment.json'), 'w') as f:
        json.dump(exp, f, indent=2)
    print(open(os.path.join(a.out, 'summary.md')).read())
    print(f"{len(runs)} runs in {time.time() - t0:.1f}s -> {a.out}")


if __name__ == '__main__':
    main()
