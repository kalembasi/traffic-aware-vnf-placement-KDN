# Findings: v1 KDN policy under a rigorous evaluation protocol (Faz 3)

Sources: `results/v1_sweep/` (8 algorithms × 30 seeds × 5 arrival rates, horizon 10 000 t.u.,
warm-up 1 200 t.u. discarded) and `results/v1_models/` (model-level analysis).
Reproduce with:
```
./run_all.sh
.venv/bin/python -m scripts.evaluate --exp experiments/v1_sweep.json --out results/v1_sweep --jobs 10
.venv/bin/python -m scripts.analyze_models --data data/telemetry_v1.csv --models-dir models/v1 --out results/v1_models
```
Statistics: mean over 30 seeds, 95 % t-CI half-width, paired Wilcoxon signed-rank test (same seed,
same traffic) against `kdn`.

## Operating points
| λ (req/t.u.) | 0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|
| Acceptance (any algorithm) | 100 % | ≈99 % | ≈76 % | ≈47 % | ≈27 % |

λ = 0.2 is the operating point of the course report: the network is heavily overloaded (offered load ≈ 2× capacity).

## F1: The v1 KDN policy beats Greedy, but it does not beat the simple Smart heuristic at any load level
Mean latency of accepted SFCs (ms, ±95 % CI ≈ 0.5–1.0 ms for these rows):

| Algorithm | λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|
| smart | **4.95** | **8.04** | **10.21** | **12.15** | **11.74** |
| cands-oracle | 8.69 | 12.56 | 16.18 | 17.57 | 16.91 |
| kdn (v1) | 9.53 | 13.48 | 17.70 | 18.79 | 17.72 |
| kdn-nogate | 9.53 | 13.71 | 17.75 | 19.24 | 18.47 |
| cands-first | 11.23 | 18.13 | 23.00 | 24.66 | 23.26 |
| greedy | 13.79 | 21.85 | 27.80 | 29.64 | 28.81 |
| cands-random | 32.09 | 33.99 | 35.86 | 35.42 | 34.79 |
| random | 38.43 | 38.57 | 38.40 | 37.50 | 36.11 |

- kdn vs greedy: −4.3 to −11.1 ms. kdn is lower in 30/30 seeds at every λ (p < 1e-5).
- kdn vs smart: +4.6 to +7.5 ms. Smart is lower in 30/30 seeds at every λ (p < 1e-5). The same ordering holds for p95 latency (smart 18–40 ms, kdn 29–53 ms).
- The course report's "38 % lower latency than Greedy" is real, but it ranks the ML policy against the weakest baseline.

## F2: Selection is not the bottleneck; the candidate set is
The KDN regressor chooses among 5 first-fit candidates: one co-location-first and four with shuffled node order.
- **Choosing from the same 5 candidates by their *true* latency** (`cands-oracle`) is 0.8–1.5 ms better than the regressor at every λ (p ≤ 6e-4). The true latency of each candidate is computed during candidate generation, so the v1 regressor estimates a quantity the controller already knows.
- **Decision quality** (λ=0.2, 10 seeds, 8 263 decisions): the regressor picks the true-minimum candidate in 82.6 % of decisions. Mean regret is 1.6 ms. Median Spearman correlation between predicted and true latencies within a decision is 0.89.
- **Even the oracle selection is 3.7–6.0 ms worse than Smart.** Smart builds its placement VNF by VNF, minimising path delay plus a wake-up penalty, so it consolidates onto active nodes. That placement is rarely among the 5 first-fit candidates, and no selector, learned or perfect, can recover a placement that is not in the candidate set.
- Most of the improvement over Greedy comes from the heuristic candidate set, not from learning. Taking the co-location candidate alone (`cands-first`) already removes 2.6–5.6 ms of Greedy's latency (44–60 % of KDN's total gain over Greedy); selecting by the regressor removes the rest.

## F3: The gatekeeper's acceptance gain is an artefact of counting requests
- Count-based acceptance: gate on (kdn) vs off (kdn-nogate) is +0.2 to +0.7 pp at λ ≥ 0.1 (p ≤ 0.06).
- **CPU-weighted acceptance** (share of requested CPU demand admitted): the gate *lowers* it by 0.10–0.43 pp at λ = 0.05–0.2 (p = 0.005–0.047; λ=0.4: −0.12 pp, p = 0.07).
- Mechanism: under load the gate rejects 75 % (λ=0.2) to 90 % (λ=0.4) of Video requests (60 CPU) but only 13–28 % of Web requests (25 CPU). Admitting many small chains instead of a few large ones raises the request count but not the carried load. The same artefact makes `random` look best by count at λ=0.4 (28.8 %) while it is worst by CPU-weighted acceptance.
- 2–15 % of gate rejections were requests that first-fit could have placed (false rejects). Video at λ=0.1 is the worst case (14.8 %).

## F4: The models mostly learn simple structure
- **Gatekeeper:** a standardised logistic regression nearly matches XGBoost. Chronological split: accuracy 0.930 vs 0.926, ROC-AUC 0.979 vs 0.986. A depth-2 tree on (sfc_type, free_cpu) reaches 0.82. The random-split accuracy of the report (93.5 %) drops to 92.6 % with a chronological split (mild leakage from near-duplicate consecutive states).
- **Classifier contributions (mean |SHAP|):** network_free_cpu 4.55, sfc_type 2.28, all others ≤ 0.28. `network_active_nodes` and `net_max_node_utilization` are unused (0.00).
- **Regressor contributions (mean |SHAP|):** action_max_path_distance 13.7, action_num_unique_nodes 4.3, all state features ≤ 1.4. A linear model on the two action features alone reaches R² 0.76 (XGBoost 0.79, chronological split).
- This corrects the course report. Its Fig. 5 ranked `network_free_bw` first because it used XGBoost's default `weight` importance (number of splits), which is not a measure of influence. Moreover, state features are identical for all candidates of one request, so they cannot affect the ranking of candidates at all.

## F5: Other observations
- "Average active nodes" saturates at 12/12 for λ ≥ 0.2 and is uninformative there. At low load Smart uses the fewest nodes (λ=0.02: 4.1 vs kdn 5.6).
- Decision time per request: greedy 0.03–0.05 ms, smart 0.06–0.3 ms, kdn 0.8–1.3 ms (two XGBoost calls plus 5 candidate constructions).

## Implications for v2 (Faz 4)
1. Learning can only pay off if the controller has to *estimate* something it cannot compute in closed form. In v1 the latency of a candidate is a sum of known link delays. v2 adds load-dependent, non-linear VNF processing (queueing) delay plus ingress and egress segments; telemetry exposes the measured latency but not the delay function.
2. The candidate set must contain strong placements: Smart's own placement, a load-balanced one and k-shortest-path variants. The learned selector can then only add value on top of the best heuristics.
3. Baselines must include a *tuned* load-aware heuristic (Smart plus a utilisation penalty with the best weight from a grid search). Otherwise the claim "no handcrafted weight tuning" is untested.
4. Report CPU-weighted acceptance next to count acceptance, and evaluate the gatekeeper with both.
