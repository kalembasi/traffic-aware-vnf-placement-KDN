#!/usr/bin/env bash
# Reproduce v1 (course report) pipeline end-to-end: telemetry -> training -> evaluation.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
SEED=${SEED:-2025}
OUT=${OUT:-results/v1}

mkdir -p "$OUT"
"$PY" data_generator.py --seed "$SEED" --out data/telemetry_v1.csv --stats-out "$OUT/traffic_distributions.csv"
"$PY" -m src.algorithms.xgboost --data data/telemetry_v1.csv --models-dir models --plots-dir "$OUT/training_plots" | tee "$OUT/training_metrics.txt"
"$PY" evaluate_models.py --out-dir "$OUT"
