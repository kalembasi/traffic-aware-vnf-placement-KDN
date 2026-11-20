# Findings

Protocol: [`experiments/protocol.md`](../experiments/protocol.md). Sections 1–6 were registered in commit `82229de`
before any data was generated; section 7 (the model builds the placement) was registered in `fd640b6` after the
results of sections 1–6 were known and before its runs. No deviations.

Sources: `results/{s0,s025,s05,s1}/` (main study), `results/{s05_linear,s05_perm2}/` (sensitivity),
`results/hypotheses.{csv,md}`, `results/hypotheses_sensitivity.csv`, `results/<env>/training_metrics.json`.

## 1. Prediction quality (validation seeds, per-VNF R²)
| σ | kdn | model-nom | model-cal |
|---|---|---|---|
| 0 | 0.999 | 0.997 | 0.997 |
| 0.25 | 0.998 | 0.907 | 0.997 |
| 0.5 | 0.997 | 0.699 | 0.998 |
| 1.0 | 0.997 | 0.296 | 0.998 |
| S1 linear, σ=0.5 | 0.999 | 0.536 | 0.995 |

- **Calibration:** model-cal recovers κ_n exactly, and û0 = 0.5995 against a true u0 of 0.6. Given the measured
  utilisation, the delay is deterministic, so calibration is exact.
- **Learning:** kdn learns the same information without the formula.
- R² is close to 1 because the label is a noise-free function of observable quantities and the node identity.
  Real telemetry would be noisier.

## 2. Mean latency of accepted SFCs (ms), σ = 0.5 and σ = 1
| Policy | σ=0.5: λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 | σ=1: λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|---|---|---|---|---|
| greedy | 30.48 | 37.38 | 41.31 | 42.82 | 41.14 | 33.29 | 41.83 | 44.71 | 45.72 | 43.36 |
| smart | 19.02 | 22.41 | 27.28 | 29.52 | 28.87 | 21.45 | 25.65 | 30.82 | 32.52 | 31.07 |
| smart-load (α*=10) | 18.72 | 21.97 | **26.96** | **29.27** | **28.52** | 21.31 | 25.10 | **30.50** | **32.27** | **30.70** |
| cands-prop | 18.92 | 22.31 | 27.75 | 30.75 | 30.37 | 21.43 | 25.58 | 31.41 | 33.83 | 32.77 |
| model-nom | 18.23 | 21.76 | 27.68 | 30.71 | 30.28 | 20.76 | 25.02 | 31.26 | 33.78 | 32.61 |
| model-cal | 17.55 | 21.56 | 27.78 | 30.85 | 30.37 | **18.17** | **23.56** | 31.30 | 33.92 | 32.54 |
| **kdn** | **17.55** | **21.52** | 27.79 | 30.49 | 30.17 | 18.20 | 23.65 | 31.24 | 33.87 | 32.63 |
| oracle | 17.56 | 21.62 | 27.69 | 30.59 | 30.30 | 18.21 | 23.67 | 31.14 | 33.85 | 32.62 |

- All tables: `results/<env>/summary.csv`.
- **σ = 0** (no heterogeneity): kdn beats smart only by 0.7–0.8 ms at light load, and every candidate selector loses
  at λ ≥ 0.1.

## 3. Pre-registered hypotheses H1–H4 (selection among candidates)
Each cell is the mean paired difference kdn − other, in ms; * means Holm-adjusted p < 0.05 across the 20 (σ, λ)
cells. Negative means kdn is faster.

| | σ | λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|---|
| **H1** vs smart-load(α*) | 0 | −0.38* | −0.30* | +0.70* | +1.55* | +1.65* |
| | 0.25 | −0.62* | −0.19* | +0.73* | +1.52* | +1.65* |
| | 0.5 | −1.17* | −0.45* | +0.82* | +1.22* | +1.66* |
| | 1 | −3.11* | −1.45* | +0.74* | +1.60* | +1.93* |
| **H2** vs model-nom | 0 | +0.01 | +0.01 | +0.05 | −0.02 | +0.06 |
| | 0.25 | −0.15* | +0.05 | +0.03 | +0.09 | −0.08 |
| | 0.5 | −0.68* | −0.24* | +0.11 | −0.22 | −0.11 |
| | 1 | −2.56* | −1.37* | −0.03 | +0.09 | +0.01 |
| **H3** vs model-cal | 0 | +0.01 | +0.01 | +0.05 | −0.02 | +0.06 |
| | 0.25 | +0.02 | +0.11 | −0.12 | +0.19 | −0.04 |
| | 0.5 | −0.01 | −0.04 | +0.01 | −0.36* | −0.20 |
| | 1 | +0.03 | +0.10 | −0.06 | −0.05 | +0.08 |
| **H4** vs cands-prop | 0 | −0.68* | −0.58* | −0.02 | −0.07 | −0.01 |
| | 0.25 | −0.84* | −0.50* | −0.03 | +0.04 | −0.16 |
| | 0.5 | −1.38* | −0.79* | +0.04 | −0.27 | −0.20 |
| | 1 | −3.23* | −1.92* | −0.17 | +0.04 | −0.14 |
| kdn − oracle (no test) | all | within ±0.13 ms in every cell | | | | |

**Expectations stated in the protocol.**
- **H2, H4:** held at light load (λ ≤ 0.05). The kdn advantage grows monotonically with σ, from about 0 to
  2.6 ms against model-nom and from 0.7 to 3.2 ms against cands-prop. It did not hold at λ ≥ 0.1, where all
  selectors are equal within ±0.3 ms at every σ.
- **H3:** held. kdn and model-cal do not differ meaningfully (one cell significant, −0.36 ms).
- **Trend check:** at λ = 0.02, kdn − model-nom is +0.01, −0.15, −0.68, −2.56 ms across σ; at λ = 0.05 it is
  +0.01, +0.05, −0.24, −1.37 ms (monotone from σ = 0.25 on; the first step is within noise). At λ ≥ 0.1 there is no trend.

## 4. Sensitivity (σ = 0.5; Holm across the 5 λ values)
| | variant | λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|---|
| H1 vs smart-load | S1 linear | −1.63* | −0.53* | +0.96* | +1.50* | +1.97* |
| | S2 perm2 | −1.21* | −0.58* | +0.62* | +1.29* | +1.55* |
| H2 vs model-nom | S1 linear | −1.00* | −0.41* | +0.18 | +0.00 | +0.09 |
| | S2 perm2 | −0.62* | −0.29* | −0.15 | −0.16 | −0.20 |
| H3 vs model-cal | S1 linear | +0.01 | +0.07 | +0.10 | −0.03 | +0.22 |
| | S2 perm2 | +0.01 | +0.09 | −0.01 | +0.02 | −0.03 |

- **S2:** the result does not depend on which nodes are slow.
- **S1:** even with the wrong (M/M/1) form, model-cal matches kdn. The linear and M/M/1 curves rank nodes almost
  identically (both increase in ρ; per-node κ dominates), so the form misspecification does not change decisions.

## 5. The model builds the placement: H5–H6 (protocol section 7)
kdn-greedy places VNFs one by one on the node with the lowest propagation + predicted processing delay. It uses the
same kdn model, without retraining.

Mean latency (ms):

| σ | Policy | λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|---|
| 0 | smart-load | 17.89 | 21.16 | 26.03 | 28.26 | 28.02 |
| | kdn (candidates) | 17.51 | 20.86 | 26.73 | 29.82 | 29.67 |
| | **kdn-greedy** | 17.59 | 20.91 | 25.89 | 28.43 | 28.04 |
| 0.5 | smart-load | 18.72 | 21.97 | 26.96 | 29.27 | 28.52 |
| | kdn (candidates) | 17.55 | 21.52 | 27.79 | 30.49 | 30.17 |
| | **kdn-greedy** | 17.12 | 21.19 | 27.00 | 29.43 | 28.69 |
| 1 | smart-load | 21.31 | 25.10 | 30.50 | 32.27 | 30.70 |
| | kdn (candidates) | 18.20 | 23.65 | 31.24 | 33.87 | 32.63 |
| | **kdn-greedy** | 16.82 | 22.28 | 30.35 | 33.50 | 31.76 |

Each cell is the mean paired difference in ms; * means Holm p < 0.05 across the 20 cells.

| | σ | λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|---|
| **H5** kdn-greedy − smart-load | 0 | −0.30* | −0.25* | −0.15 | +0.16 | +0.02 |
| | 0.25 | −0.72* | −0.29* | +0.08 | −0.02 | +0.40* |
| | 0.5 | −1.60* | −0.79* | +0.04 | +0.17 | +0.17 |
| | 1 | −4.49* | −2.82* | −0.15 | +1.23* | +1.06* |
| **H6** kdn-greedy − kdn | 0 | +0.08* | +0.05 | −0.85* | −1.39* | −1.63* |
| | 0.25 | −0.10* | −0.10 | −0.65* | −1.54* | −1.25* |
| | 0.5 | −0.42* | −0.33* | −0.79* | −1.05* | −1.49* |
| | 1 | −1.38* | −1.37* | −0.88* | −0.37* | −0.86* |

- **H6:** building the placement beats choosing among candidates in 18 of 20 cells, by up to 1.6 ms. The two
  exceptions are at σ = 0, light load, and both are below 0.1 ms.
- **H5, against the tuned heuristic:**
  - Light load: kdn-greedy is better, and the gain grows with σ (up to −4.5 ms).
  - Medium and heavy load: no difference up to σ = 0.5. At σ = 1, λ ≥ 0.2, it is about 1.1–1.2 ms worse.
- **Upper bound:** kdn-greedy ≈ oracle-greedy ≈ model-cal-greedy (±0.2 ms). The model is as good as the true
  delay inside this search, so the remaining loss at heavy load comes from the per-request (myopic) objective,
  not from prediction.
- **Acceptance:** CPU-weighted acceptance of kdn-greedy equals smart-load's (±0.3 pp). The candidate selectors'
  +1 pp is gone.

## 6. Secondary metrics
- **CPU-weighted acceptance:** every candidate selector admits +0.4 to +1.1 pp more CPU demand than smart and
  smart-load at λ ≥ 0.05, at every σ. Their latency loss at λ ≥ 0.1 therefore comes with slightly more admitted
  load. Survivor bias may explain part of it.
- **p95 latency, σ = 1:**
  - λ = 0.02: kdn 33.1 ms vs smart 41.9 ms and smart-load 44.1 ms.
  - λ = 0.2: kdn 70.8 ms vs smart-load 65.8 ms.

## 7. Interpretation
1. **Learning works, and so does calibration.** With per-VNF telemetry, kdn learns the hidden node speeds as well
   as an analytical model that knows the formula and calibrates them. The value of learning over a calibrated
   known-form model is not visible here. The form misspecification in S1 was too mild to separate them.
2. **Choosing among heuristic candidates caps the gain.** The prediction quality of model-nom collapses with σ
   (R² 0.997 → 0.30), yet at λ ≥ 0.1 every selector, including the oracle, is within ±0.3 ms of cands-prop. The
   candidates come from heuristics that do not know κ, so a placement that avoids slow nodes is rarely in the set.
   Letting the model build the placement (kdn-greedy) removes this ceiling in 18 of 20 cells.
3. **The myopic loss persists.** At heavy load, the tuned smart-load matches or beats every model-driven policy,
   including the oracles. Each request is optimised on its own, without regard to the requests that follow.
4. **The gain from learning is real but confined to light load.** It grows with heterogeneity: at σ = 1, λ = 0.02,
   kdn-greedy is 4.5 ms faster than tuned smart-load, and kdn's p95 is 9–11 ms lower than smart's and smart-load's.

## 8. Data ablation (`scripts/ablation_data.py`, `results/ablation_data.md`)
σ = 1, 30 test seeds; oracle-greedy stands in for kdn-greedy (they agree within 0.2 ms on the base world).
Removing the KDN CPU measurements (every load factor r = 1) changes the smart − oracle-greedy gain by at most
0.19 ms; also replacing the Abilene matrices by a constant rate and uniform OD pairs changes it by at most 0.58 ms
(at λ = 0.1). The sign of the gain never flips. The KDN load factor r stays within about 0.9–1.1 because the KDN
batches have similar packet counts. The result is carried by the hidden node speeds κ and the topology, not by
the traffic data.
