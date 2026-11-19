"""Usage: python -m scripts.train --data data/telemetry_v1.csv --models-dir models"""
import argparse
import json

from src.training import train_models

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--data', required=True)
ap.add_argument('--models-dir', default='models')
ap.add_argument('--plots-dir', default=None)
a = ap.parse_args()
m = train_models(a.data, a.models_dir, a.plots_dir)
print(json.dumps(m, indent=2))
