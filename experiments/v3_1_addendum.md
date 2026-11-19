# v3.1 Addendum (pre-registered before running)

**Written after the v3 results were known** (`results/v3_findings.md`). Those results motivated this addendum:
at λ ≥ 0.1, every selector over the heuristic candidate set, including the oracle, performed about the same,
which suggests that the candidate set limits what any learned model can do.

**Question.** If the model builds the placement itself instead of choosing among heuristic candidates, does
it do better?

## Policies (no retraining; the same v3 models and calibration are reused)
- **kdn3-greedy:** VNFs are placed one by one, in chain order. For each VNF, every feasible node is scored:
  propagation delay from the previous hop + the predicted processing delay of the SFC's VNFs placed so far
  including this one (for the last VNF, plus the delay to the egress). The lowest score wins. The prediction
  uses the existing kdn3 per-VNF regressor.
- **model-cal-greedy:** the same search, with the model-cal formula instead of the regressor.
- **oracle-greedy:** the same search, with the true processing delay. It is an upper bound for this search, not
  a global optimum.

## Evaluation
- The 4 main v3 environments (σ ∈ {0, 0.25, 0.5, 1}), test split, seeds 1–30, λ ∈ {0.02, 0.05, 0.1, 0.2, 0.4},
  same horizon and warm-up. Sensitivity environments are not run.
- Paired two-sided Wilcoxon over seeds, Holm across the 20 (σ, λ) cells per comparison:
  - **H5:** kdn3-greedy vs smart-load(α*)
  - **H6:** kdn3-greedy vs kdn3 (candidate-based)
- Reported without a test: kdn3-greedy − oracle-greedy and model-cal-greedy.

## Deviations
