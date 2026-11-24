# When Does a Learned Latency Model Help VNF Placement? A Knowledge-Defined Networking Study

A trace-driven simulation study of SFC (service function chain) placement. A controller learns, from per-VNF
telemetry, how long a VNF takes to process traffic on each node, and uses that model to place new SFCs. The study
asks when this learned model helps compared with simple heuristics, and under which load.

- **Paper** (seminar, IEEEtran): [`manuscript/main.pdf`](manuscript/main.pdf); every number in it comes from
  [`results/paper_tables.md`](results/paper_tables.md), [`results/load_levels.md`](results/load_levels.md) and
  [`results/ablation_data.md`](results/ablation_data.md).
- **Slides** (15-min talk, speaker notes included): [`presentation/slides.pdf`](presentation/slides.pdf).
- **Plain-language overview** (Turkish): [`docs/overview.html`](docs/overview.html).
- **Pre-registered protocol and all results** (including variants not in the paper):
  [`experiments/protocol.md`](experiments/protocol.md), [`results/findings.md`](results/findings.md).

**Main result** (σ = 1, hidden slow servers): at normal load (λ = 0.02–0.05) `kdn-greedy` lowers the mean SFC
latency by 13–22% compared with `smart`; with equal servers (σ = 0) by 3–4%. Near capacity the gain disappears,
because optimising each request on its own fills the fast servers first; an oracle with the true delays behaves the same.

## Setup in one paragraph
- **Network:** the 12-node SNDlib Abilene topology. Link delays come from geographic distance.
- **Traffic:** SFC requests arrive and pick their ingress/egress following the real Abilene traffic matrices of 2004.
  Each request is a Web, VoIP or Video chain.
- **Processing delay:** each request carries a traffic profile from the KDN VNF measurement dataset. The processing
  delay of a VNF grows with the load of its host (M/M/1-style). Some nodes are secretly slower than others; the
  spread σ of these hidden node speeds is the main experimental variable.
- **Model:** an XGBoost regressor is trained on simulated per-VNF telemetry to predict the processing delay of a VNF
  on a node.
- **Policies in the paper:**
  - `greedy`: each VNF on the first node (fixed order) with enough free CPU/RAM.
  - `smart`: each VNF on the node with the shortest propagation delay from the previous hop.
  - `kdn-greedy`: each VNF on the node with the lowest path delay + model-predicted processing delay.
  - `oracle-greedy`: the same search with the true delay (reference).
- **Further policies in the repository** (see `results/findings.md`): `kdn` (the model chooses among heuristic
  candidates; the first, pre-registered design), tuned `smart-load`, formula-based `model-nom` / `model-cal`.

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

Paper and slides (after the steps above):
```bash
cd manuscript && latexmk -pdf main.tex         # needs texlive-publishers, texlive-latex-extra
.venv/bin/python -m presentation.make_slides   # presentation/slides.pptx; fonts in presentation/fonts
soffice --headless --convert-to pdf presentation/slides.pptx --outdir presentation
```
Install the fonts in `presentation/fonts` (Source Serif 4, Inter) before opening or converting the `.pptx`.

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
scripts/          run.py (pipeline), ablation_data.py (data ablation), load_levels.py, paper_tables.py,
                  make_figures.py, fetch_data.sh
experiments/      protocol.md, environment configs (envs/), dataset checksums
results/          findings.md, hypotheses.*, one folder per environment (runs, summaries, alpha tuning, model metrics)
tests/            resource and load conservation, determinism, calibration, model policies
manuscript/       seminar paper (IEEEtran LaTeX: main.tex, refs.bib); figures are read from figures/
presentation/     seminar slides: make_slides.py -> slides.pptx / slides.pdf, fonts/
docs/             overview.html (Turkish plain-language overview)
```

Environments: `s0`, `s025`, `s05`, `s1` (node-speed spread σ = 0, 0.25, 0.5, 1) and two sensitivity variants at
σ = 0.5: `s05_linear` (linear instead of M/M/1 delay) and `s05_perm2` (different slow nodes).

## Data sources
- SNDlib: Orlowski et al., *SNDlib 1.0 — Survivable Network Design Library*, Networks 55(3), 2010.
- Abilene traffic matrices: Y. Zhang, via SNDlib.
- KDN VNF datasets: Mestres et al., *Knowledge-Defined Networking*, ACM SIGCOMM CCR 47(3), 2017.
