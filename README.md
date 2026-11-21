# Where Does Learning Help? Knowledge-Defined Networking for Load-Aware VNF Placement

A trace-driven simulation study of SFC (service function chain) placement. A controller learns, from per-VNF
telemetry, how long a VNF takes to process traffic on each node, and uses that model to place new SFCs. The study
asks when this learned model helps compared with tuned heuristics and with analytical models that know the delay
formula.

The evaluation protocol was pre-registered before any data was generated: [`experiments/protocol.md`](experiments/protocol.md).
The results are in [`results/findings.md`](results/findings.md).

## Setup in one paragraph
- **Network:** the 12-node SNDlib Abilene topology. Link delays come from geographic distance.
- **Traffic:** SFC requests arrive and pick their ingress/egress following the real Abilene traffic matrices of 2004.
  Each request is a Web, VoIP or Video chain.
- **Processing delay:** each request carries a traffic profile from the KDN VNF measurement dataset. The processing
  delay of a VNF grows with the load of its host (M/M/1-style). Some nodes are secretly slower than others; the
  spread σ of these hidden node speeds is the main experimental variable.
- **Model:** an XGBoost regressor is trained on simulated per-VNF telemetry to predict the processing delay of a VNF
  on a node.
- **Policies compared:**
  - `kdn` lets the model choose among heuristic candidates.
  - `kdn-greedy` lets the model place the VNFs itself.
  - Baselines: tuned heuristics, formula-based models (`model-nom`, `model-cal`) and oracles that know the true delay.

## Installation
Tested with Python 3.14 on Linux.
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Reproducing everything
```bash
./run_all.sh    # download data -> 6 environments -> hypothesis tests -> data ablation -> paper tables -> figures -> tests   (~30 min, 12 cores)
```
The individual steps:
```bash
scripts/fetch_data.sh                          # public datasets into data/external (SHA256-checked)
.venv/bin/python -m scripts.run run --name s05 # telemetry, training, alpha tuning, evaluation for one environment
.venv/bin/python -m scripts.run analyze        # pre-registered hypothesis tests across environments
.venv/bin/python -m scripts.ablation_data      # does the result depend on the KDN / Abilene traffic data? (~1 min)
.venv/bin/python -m scripts.load_levels        # reserved CPU and acceptance at each arrival rate (smart)
.venv/bin/python -m scripts.paper_tables       # numbers quoted in the paper -> results/paper_tables.md
.venv/bin/python -m scripts.make_figures       # figures/
.venv/bin/python -m pytest -q
```
Every run is seeded; the results are deterministic except the measured decision time (`decision_ms`).

## Layout
```
src/
  sfc.py          SFC catalogue and request model
  data.py         loaders for SNDlib topology/traffic matrices and the KDN VNF dataset
  environment.py  simulated network: topology, request stream, hidden VNF load and delay; SimPy simulation
  placement.py    shared placement core: tentative resource overlay, routing, chain construction, commit/release
  features.py     per-VNF telemetry features of the model
  policies.py     all placement policies (heuristics, candidate selectors, model-built placement, oracles)
  experiment.py   simulation grid, telemetry generation, model training and calibration
  analysis.py     summary tables and hypothesis tests
scripts/          run.py (pipeline), ablation_data.py (data ablation), make_figures.py, fetch_data.sh
experiments/      protocol.md, environment configs (envs/), dataset checksums
results/          findings.md, hypotheses.*, one folder per environment (runs, summaries, alpha tuning, model metrics)
tests/            resource and load conservation, determinism, calibration, model policies
manuscript/       seminar paper (IEEEtran LaTeX: main.tex, refs.bib); figures are read from figures/
```

Environments: `s0`, `s025`, `s05`, `s1` (node-speed spread σ = 0, 0.25, 0.5, 1) and two sensitivity variants at
σ = 0.5: `s05_linear` (linear instead of M/M/1 delay) and `s05_perm2` (different slow nodes).

## Data sources
- SNDlib: Orlowski et al., *SNDlib 1.0 — Survivable Network Design Library*, Networks 55(3), 2010.
- Abilene traffic matrices: Y. Zhang, via SNDlib.
- KDN VNF datasets: Mestres et al., *Knowledge-Defined Networking*, ACM SIGCOMM CCR 47(3), 2017.
