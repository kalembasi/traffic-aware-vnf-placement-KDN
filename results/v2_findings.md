# Findings: v2 trace-driven evaluation (Faz 4)

Protocol: [`experiments/v2_protocol.md`](../experiments/v2_protocol.md), registered in commit `48e6edb` before
any KDN-v2 model was trained. Deviations are listed at the end of the protocol.
Sources: `results/v2/main` (pre-registered main study), `results/v2/{u04,u08,linear}` (pre-registered
sensitivity, λ=0.2), `results/v2/*_exploratory` (exploratory ablations; **not pre-registered**),
`results/v2/main/diagnostics.md` (latency decomposition, generator choice; 10 seeds).

## Setup in one paragraph
- **Network and traffic:** SNDlib Abilene (12 nodes, 15 links, geographic propagation delay). Requests arrive as a non-homogeneous Poisson process driven by the 2004 Abilene 5-min traffic matrices (ingress/egress ∝ OD volume).
- **Hidden VNF load:** each VNF's load comes from KDN VNF CPU measurements (Snort / OVS-firewall / OVS-switch), drawn by k-NN on the request's packet count. Processing delay s_v/(1−ρ) depends on the *measured* node utilisation, which only telemetry reveals.
- **Learned policy:** KDN-v2 learns the processing delay from telemetry logged on the train split (Mar–Jun 2004) under a random behaviour policy. It picks, among ≤8 heuristic candidates, the lowest known propagation delay + predicted processing delay.
- **Evaluation:** test split (Jul–Sep 2004), 30 seeds × λ ∈ {0.02 … 0.4}, horizon 10 000 t.u., warm-up 1 200.
- **Acceptance at each λ:** about 99.6 / 97 / 79 / 48 / 27 %.

## Main results (pre-registered), mean latency of accepted SFCs, ms
| Policy | λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|
| greedy | 29.68 | 36.15 | 40.52 | 42.03 | 40.51 |
| smart-v2 (load-unaware) | 26.70 | 26.18 | 27.08 | 28.62 | 28.26 |
| smart-load (α*=10, tuned on train) | 26.93 | 25.83 | 26.76 | **28.27** | **27.82** |
| **kdn2** | **18.41** | 21.03 | 26.65 | 29.72 | 29.57 |
| kdn2-gate (ablation) | 18.39 | **20.95** | **26.31** | 28.84 | 28.10 |
| oracle (true latency, same candidates) | 18.42 | 21.00 | 26.69 | 29.79 | 29.61 |
| random | 50.25 | 50.66 | 49.96 | 48.53 | 45.90 |

95 % CI half-widths are 0.2–1.0 ms. CPU-weighted acceptance of kdn2 vs smart-v2: +1.1 / +3.0 / +1.1 / +0.3 / +0.1 pp.

### Hypotheses (paired Wilcoxon, Holm-corrected over λ)
| | λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|
| **H1** kdn2 < smart-v2 | ✅ −8.29 | ✅ −5.15 | ✅ −0.43 (p_holm=.022) | ❌ +1.10 | ❌ +1.31 |
| **H2** kdn2 vs smart-load (two-sided) | kdn2 better −8.52 | kdn2 better −4.80 | n.s. −0.11 | kdn2 **worse** +1.45 | kdn2 **worse** +1.75 |
| **H3** CPU-acc. non-inferior (−1 pp) | ✅ | ✅ | ✅ | ✅ | ✅ |
| kdn2 − oracle | −0.01 | +0.02 | −0.04 | −0.07 | −0.04 (all CIs include 0) |

### Answers
- **RQ1 (learned vs load-unaware heuristic):** yes at low and moderate load (λ ≤ 0.1, acceptance ≥ 79 %), where kdn2 is 0.4–8.3 ms faster *and* admits more CPU demand. No at high load (λ ≥ 0.2), where it is 1.1–1.3 ms slower.
- **RQ2 (learned vs tuned heuristic):** better at λ ≤ 0.05, equal at λ = 0.1, worse at λ ≥ 0.2. "No weight tuning" is therefore an advantage only in the lightly loaded regime.
- **RQ3 (gap to oracle):** none. The regressor predicts the hidden processing delay with validation R² = 0.994 (RMSE 0.40 ms, mean 6.8 ms), and selection is oracle-quality at every load.

## Sensitivity (pre-registered, λ = 0.2, KDN retrained and α re-tuned per variant)
| Variant | α* | val. R² | kdn2 − smart-v2 | kdn2 − smart-load | kdn2 − oracle |
|---|---|---|---|---|---|
| main (u0=0.6, M/M/1) | 10 | 0.994 | +1.10 | +1.45 | −0.07 |
| S1 u0=0.4 | 20 | 0.999 | +1.09 | +1.40 | −0.04 |
| S1 u0=0.8 | 10 | 0.945 | +1.50 | +1.79 | +0.03 |
| S2 linear delay | 10 | 0.998 | +1.20 | +1.55 | +0.05 |

The high-load conclusion is robust: under every variant the learned selector is oracle-quality and yet slower than the heuristics.

## Exploratory analyses (decided after seeing the main results; not pre-registered)
- **Value of learning itself.** `cands-prop` uses the same candidate set as kdn2 but selects by the *known* propagation delay only. kdn2 is 0.55 / 0.51 ms better at λ = 0.02 / 0.05 (p < 1e-4), 0.22 ms at λ = 0.1 (p = 0.05), and not different at λ ≥ 0.2. Learning the hidden processing delay is worth about 2–3 % of latency.
- **Where the low-load gain comes from.** smart-v2 inherits v1's wake-up penalty (an energy objective), which drives detours to already-active nodes when few nodes are active. Without the penalty (`smart-nowake`) it matches kdn2 at λ = 0.02 (−0.07 ms, n.s.). Most of kdn2's large low-load advantage over smart-v2 therefore comes from latency-oriented candidates (co-location from the ingress, least-utilised node), not from learning. At λ = 0.02 kdn2 picked those two generators for 60 % of accepted SFCs.
- **A simple tuned heuristic is the strongest latency baseline.** `smart-nowake-load` (no wake-up penalty, α* reused) has lower mean latency than kdn2 at λ = 0.02, 0.1, 0.2, 0.4 (by 0.47–1.67 ms) and is slightly worse at λ = 0.05 (+0.09 ms). It admits *less* CPU demand, though: 0.15–1.19 pp lower CPU-weighted acceptance at λ ≥ 0.05, significant at every λ ≥ 0.05 (p ≤ 0.03). The two policies sit at different points of a latency–acceptance trade-off. Lower latency is partly survivor bias (fewer, easier SFCs admitted).
- **Gatekeeper in v2.** kdn2-gate lowers latency at high load (−0.89 / −1.47 ms at λ = 0.2 / 0.4) at a cost of 0.07–0.32 pp CPU-weighted acceptance. This is the same admission-for-latency trade-off as in v1.

## Mechanism (diagnostics, 10 seeds)
- **Processing delay is a minority of latency:** 39 % at λ = 0.02, falling to 18 % at λ = 0.4. Reservation-based admission keeps node utilisation bounded, so queueing delays rarely explode and the hidden, learnable component has limited leverage.
- **Myopia at high load:** kdn2 and the oracle have *both* higher propagation (24.3 vs 23.3 ms) and higher processing delay (5.3 vs 5.0 ms) than smart-v2 at λ = 0.4. Minimising each request's own setup latency degrades the state that later requests face; consistent consolidation does better. This is a limit of per-request (myopic) optimisation, not of the latency model.

## Take-away for the paper
1. A telemetry-trained KDN latency model can learn a hidden, measurement-grounded VNF behaviour almost perfectly (R² ≥ 0.94; oracle-level selection).
2. Placement quality is bounded by two things outside the model: the candidate set and the myopic, per-request objective. The learned policy gains clearly where load is light to moderate. Under heavy load, simple consolidating heuristics stay ahead, and a tuned heuristic beats it.
3. Honest gain statement:
   - **vs greedy:** −10.9 to −15.1 ms (−27 % to −42 %) at every load.
   - **vs the v1-style smart heuristic:** −8.3 ms (−31 %) at λ = 0.02 and −5.1 ms (−20 %) at λ = 0.05, with +1–3 pp CPU-weighted acceptance.
   - Learning *itself* contributes 0.2–0.5 ms at λ ≤ 0.1; the rest comes from the candidate set.
4. Natural future work: long-horizon objectives (RL / value-based admission and placement), richer candidate generation, closed-loop retraining.
