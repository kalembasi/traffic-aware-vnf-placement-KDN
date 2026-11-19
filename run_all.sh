#!/usr/bin/env bash
# Reproduce the v1 (course report) pipeline end-to-end: telemetry -> training -> evaluation -> tests.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
SEED=${SEED:-2025}
OUT=results/v1

"$PY" -m scripts.generate_data --seed "$SEED" --out data/telemetry_v1.csv --stats-out "$OUT/traffic_distributions.csv"
"$PY" -m scripts.train --data data/telemetry_v1.csv --models-dir models/v1 --plots-dir "$OUT/training_plots" > "$OUT/training_metrics.json"
"$PY" -m scripts.evaluate --exp experiments/v1.json --out "$OUT"
"$PY" -m pytest -q
