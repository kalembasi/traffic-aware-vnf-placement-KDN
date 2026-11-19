"""Usage: python -m scripts.generate_data --seed 2025 --out data/telemetry_v1.csv"""
import argparse
import json
import os

from src.datagen import generate

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--config', default='config/config.json')
ap.add_argument('--seed', type=int, default=2025)
ap.add_argument('--out', default='data/telemetry.csv')
ap.add_argument('--stats-out', default=None)
a = ap.parse_args()

with open(a.config) as f:
    config = json.load(f)
df, stats = generate(config, seed=a.seed)
os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
df.to_csv(a.out, index=False)
print(f"{len(df)} telemetry rows -> {a.out}")
print(stats.to_string(index=False))
if a.stats_out:
    os.makedirs(os.path.dirname(a.stats_out) or '.', exist_ok=True)
    stats.to_csv(a.stats_out, index=False)
