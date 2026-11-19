# Findings: v3 evaluation (Faz 4C)

Protocol: [`experiments/v3_protocol.md`](../experiments/v3_protocol.md), registered in commit `82229de` before any v3
data was generated. No deviations. Sources: `results/v3/{s0,s025,s05,s1}` (main study),
`results/v3/{s05_linear,s05_perm2}` (sensitivity), `results/v3/hypotheses*.csv|md`, `models/v3/*/training_metrics.json`.

## What changed from v2
- The smart heuristic and the candidate generators no longer carry the wake-up penalty.
- **Hidden node speed factor κ_n** (geometric mean 1), with spread σ ∈ {0, 0.25, 0.5, 1}. At σ = 1, κ ranges over [0.18, 5.65].
- **New selectors over the same ≤ 8 candidates:**
  - model-nom: knows the delay formula, not the node speeds.
  - model-cal: knows the formula and calibrates per-node speeds from the training telemetry.
  - kdn3: per-VNF XGBoost, no formula; node identity is a feature.

## 1. Prediction quality (validation seeds, per-VNF R²)
| σ | kdn3 | model-nom | model-cal |
|---|---|---|---|
| 0 | 0.999 | 0.997 | 0.997 |
| 0.25 | 0.998 | 0.907 | 0.997 |
| 0.5 | 0.997 | 0.699 | 0.998 |
| 1.0 | 0.997 | 0.296 | 0.998 |
| S1 linear, σ=0.5 | 0.999 | 0.536 | (see json) |

- **Calibration:** model-cal recovers κ_n exactly, and û0 = 0.5995 against a true u0 of 0.6. Given the measured
  utilisation, the delay is deterministic, so calibration is exact.
- **Learning:** kdn3 learns the same information without the formula.

## 2. Mean latency of accepted SFCs (ms), σ = 0.5 and σ = 1
| Policy | σ=0.5: λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 | σ=1: λ=0.02 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|---|---|---|---|---|
| greedy | 30.48 | 37.38 | 41.31 | 42.82 | 41.14 | 33.29 | 41.83 | 44.71 | 45.72 | 43.36 |
| smart | 19.02 | 22.41 | 27.28 | 29.52 | 28.87 | 21.45 | 25.65 | 30.82 | 32.52 | 31.07 |
| smart-load (α*=10) | 18.72 | 21.97 | **26.96** | **29.27** | **28.52** | 21.31 | 25.10 | **30.50** | **32.27** | **30.70** |
| cands-prop | 18.92 | 22.31 | 27.75 | 30.75 | 30.37 | 21.43 | 25.58 | 31.41 | 33.83 | 32.77 |
| model-nom | 18.23 | 21.76 | 27.68 | 30.71 | 30.28 | 20.76 | 25.02 | 31.26 | 33.78 | 32.61 |
| model-cal | 17.55 | 21.56 | 27.78 | 30.85 | 30.37 | **18.17** | **23.56** | 31.30 | 33.92 | 32.54 |
| **kdn3** | **17.55** | **21.52** | 27.79 | 30.49 | 30.17 | 18.20 | 23.65 | 31.24 | 33.87 | 32.63 |
| oracle | 17.56 | 21.62 | 27.69 | 30.59 | 30.30 | 18.21 | 23.67 | 31.14 | 33.85 | 32.62 |

- All tables: `results/v3/<env>/summary.csv`.
- **σ = 0** (no heterogeneity) reproduces the v2 exploratory picture. Without the wake-up penalty, kdn3 beats
  smart only by 0.7–0.8 ms at light load, and every candidate selector loses at λ ≥ 0.1.

## 3. Pre-registered hypotheses
Each cell is the mean paired difference kdn3 − other, in ms; * means Holm-adjusted p < 0.05 across the 20 (σ, λ)
cells. Negative means kdn3 is faster.

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
| kdn3 − oracle (no test) | all | within ±0.13 ms in every cell | | | | |

**Expectations stated in the protocol.**
- **H2, H4:** held at light load (λ ≤ 0.05). The kdn3 advantage grows monotonically with σ, from about 0 to
  2.6 ms against model-nom and from 0.7 to 3.2 ms against cands-prop. It did not hold at λ ≥ 0.1, where all
  selectors are equal within ±0.3 ms at every σ.
- **H3:** held. kdn3 and model-cal do not differ meaningfully (one cell significant, −0.36 ms).
- **Trend check:** at λ = 0.02, kdn3 − model-nom is +0.01, −0.15, −0.68, −2.56 ms across σ; at λ = 0.05 it is
  +0.01, +0.05, −0.24, −1.37 ms (monotone except the σ=0.25 step at λ=0.05, which is +0.04). At λ ≥ 0.1 there is no trend.

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
- **S1:** even with the wrong (M/M/1) form, model-cal matches kdn3. The linear and M/M/1 curves rank nodes almost
  identically (both increase in ρ; per-node κ dominates), so the form misspecification does not change decisions.

## 5. Secondary metrics
- **CPU-weighted acceptance:** every candidate selector admits +0.4 to +1.1 pp more CPU demand than smart and
  smart-load at λ ≥ 0.05, at every σ. Their latency loss at λ ≥ 0.1 therefore comes with slightly more admitted
  load. Survivor bias may explain part of it.
- **p95 latency, σ = 1:**
  - λ = 0.02: kdn3 33.1 ms vs smart 41.9 ms and smart-load 44.1 ms.
  - λ = 0.2: kdn3 70.8 ms vs smart-load 65.8 ms.

## 6. Interpretation
1. **Learning works, and so does calibration.** With per-VNF telemetry, kdn3 learns the hidden node speeds as well
   as an analytical model that knows the formula and calibrates them. The value of learning over a calibrated
   known-form model is not visible here. The form misspecification in S1 was too mild to separate them.
2. **The information does not reach the decisions at medium and heavy load.** The prediction quality of model-nom
   collapses with σ (R² 0.997 → 0.30), yet at λ ≥ 0.1 every selector, including the oracle, is within ±0.3 ms of
   cands-prop. The candidates come from heuristics that do not know κ, so a placement that avoids slow nodes is
   rarely in the set. The ceiling is the candidate set, not the model.
3. **The myopic loss persists.** At λ ≥ 0.1, the stand-alone smart-load beats every candidate selector, including
   the oracle, by 0.7–1.9 ms at every σ. This is the v2 finding again, now without the wake-up penalty.
4. **The gain from learning is real but confined to light load.** It grows with heterogeneity: at σ = 1, λ = 0.02,
   kdn3 is 3.1 ms faster than tuned smart-load and 2.6 ms faster than model-nom, with p95 lower by 9–11 ms.
