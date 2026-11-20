#!/usr/bin/env bash
# Full pipeline: public data -> 6 environments (telemetry, training, alpha tuning, evaluation)
# -> hypothesis tests -> data ablation -> figures -> tests.  About 30 min on 12 cores.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}

scripts/fetch_data.sh
for env in s0 s025 s05 s1 s05_linear s05_perm2; do
  "$PY" -m scripts.run run --name "$env"
done
"$PY" -m scripts.run analyze
"$PY" -m scripts.ablation_data
"$PY" -m scripts.make_figures
"$PY" -m pytest -q
