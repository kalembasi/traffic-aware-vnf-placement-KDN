# v3 Evaluation Protocol (pre-registered)

**Status:** frozen before any v3 data is generated, any v3 model is trained or any v3 policy is evaluated.
The commit that adds this file is the registration timestamp. Later changes are listed under *Deviations*
at the end, with date and reason.

**Relation to v2.** The v2 results (`experiments/v2_protocol.md`, `results/v2_findings.md`) were known when this
protocol was written and motivated it. Three v2 design choices limited what the study could show:

1. The smart heuristic carried an energy-motivated wake-up penalty (1000) from the course project. The
   exploratory v2 runs showed that most of KDN's low-load gain came from this penalty, not from learning.
2. The hidden processing delay was `s_v / (1 − ρ)` with ρ observable. A controller that knows this form
   could compute the delay without learning; v2 had no such baseline.
3. The hidden behaviour carried little information beyond the reservations (relative load r ≈ 1, all
   nodes identical), so there was little left for a learned model to discover.

v3 removes (1), adds known-form baselines for (2), and makes (3) a controlled variable: the heterogeneity of
node processing speed, which is hidden from every policy except the oracle. v3 is the confirmatory study;
v2 is treated as exploratory.

## 1. Research questions
- **RQ1.** As the hidden heterogeneity of node processing speed grows, does a telemetry-trained latency model
  (KDN) place SFCs with lower latency than (a) a tuned load-aware heuristic and (b) an analytical selector that
  knows the delay formula but not the node speeds?
- **RQ2.** Does learning beat an analytical selector that knows the delay formula *and* calibrates per-node
  speeds from the same training telemetry? In other words, is the value of learning that it does not need
  the functional form?
- **RQ3.** How far is the learned selector from an oracle that knows the true latency of every candidate?

## 2. Environment
Identical to the v2 main environment (v2 protocol section 2: SNDlib Abilene, Abilene traffic matrices with the
same train/test split, KDN VNF measurements, u0 = 0.6, M/M/1-style delay, the same s_v) except:

- **Node speed factor κ_n (hidden).** The processing delay of VNF v on node n is
  `κ_n · s_v / (1 − min(ρ_n, 0.95))`, with ρ_n measured right after the new SFC is placed (as in v2).
- κ_n = exp(σ · z_{π(n)}), where z_i = Φ⁻¹((i + 0.5)/12), i = 0…11, and π is a permutation of the 12 nodes
  (sorted by name) drawn with `numpy.random.default_rng(2026).permutation(12)`. The geometric mean of κ is 1
  for every σ, and the same nodes are slow at every σ; only the spread changes.
- **Levels:** σ ∈ {0, 0.25, 0.5, 1.0}. The κ ranges are [1, 1], [0.65, 1.54], [0.42, 2.38] and [0.18, 5.65].
  σ = 0 is the v2 environment without heterogeneity.
- κ does not change capacity, reservations, load or admission. It changes only how long a VNF takes to
  process traffic on that node.
- Config files: `experiments/v3/env_s0.json`, `env_s025.json`, `env_s05.json`, `env_s1.json`.

### 2.1 What each policy may observe
| Information | Greedy / Smart | Smart-load(α) | cands-prop | model-nom | model-cal | KDN-v3 | Oracle |
|---|---|---|---|---|---|---|---|
| Topology, link delays, reservations | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Measured node utilisation ρ_n (telemetry) | | ✓ | | ✓ | ✓ | ✓ | ✓ |
| Request traffic features (packets, flows) | | | | | | ✓ | ✓ |
| Delay formula and nominal s_v | | | | ✓ | ✓ | | ✓ |
| Training telemetry (train split) | | α tuning | | û0 | û0, κ̂_n | model | |
| True κ_n, true r, true delay | | | | | | | ✓ |

## 3. Policies
- **random**, **greedy:** references, as in v2.
- **smart:** per-VNF score = propagation delay from the previous hop (the ingress for VNF₁); for the last VNF,
  plus the delay to the egress. **No wake-up penalty.**
- **smart-load(α):** smart + α · ρ_n. α is tuned separately for each environment on the train split
  (grid {0, 1, 2, 5, 10, 20, 50, 100, 200}, seeds 101–110, the 5 λ values, minimising the sum over λ of the mean
  latency). The chosen α* is fixed for the test split.
- **Candidate set** (shared by every selector below and by the behaviour policy), at most 8 distinct placements:
  smart; smart-load(α) for α ∈ {2, 10, 50} (fixed, not tuned); least-utilised node; co-location starting at the
  ingress; 2 shuffled first-fit placements. As in v2, but without the wake-up penalty.
- **Selectors over the candidate set** (they differ only in how they score a candidate):
  - **cands-prop:** known propagation delay only (no load information).
  - **model-nom:** propagation + Σ_v s_v / (1 − min(ρ̂_n, 0.95)), where ρ̂_n = (load_n + û0 · CPU reserved by this
    SFC on n) / cpu_max. It knows the formula and the nominal s_v, and assumes κ_n = 1. û0 is one scalar fitted on
    the training telemetry: the observed increase in node load divided by the CPU reserved on that node.
  - **model-cal:** model-nom with κ̂_n · s_v, where κ̂_n is the median over the training telemetry of
    (observed VNF delay on n) / (s_v / (1 − min(ρ_n,after, 0.95))). It knows the formula and calibrates node speeds.
  - **kdn3:** propagation + Σ_v f̂(VNF v on its host), where f̂ is an XGBoost regressor of the per-VNF processing
    delay. Features: VNF type (one-hot), host node (one-hot), measured ρ of the host before placement, CPU reserved
    by this SFC on the host, number of this SFC's VNFs on the host, request packets and flows, network-wide mean ρ.
    It does not know the formula. Same hyper-parameters as v1/v2 (150 trees, depth 5, learning rate 0.1).
  - **oracle:** the candidate with the lowest true latency (upper bound for any selector over this set).
- **Dropped from v2:** the wake-up penalty and the gatekeeper classifier.

## 4. Training and calibration data
- One data set per environment, generated on the *train* split by the behaviour policy (uniform random choice
  among the candidates), λ ∈ {0.05, 0.1, 0.2, 0.4} × seeds 1001–1020, horizon 10 000 t.u.
- One row per VNF of every accepted request: host, VNF type, CPU reserved by the SFC on the host, host load before
  and after placement, observed processing delay of the VNF, request packets and flows, network mean ρ.
  Per-VNF processing delay is assumed to be measurable (per-VNF telemetry).
- kdn3, û0 and κ̂_n are fitted on seeds 1001–1016. Seeds 1017–1020 are held out for validation metrics.

## 5. Evaluation
- Test split, seeds 1–30, λ ∈ {0.02, 0.05, 0.1, 0.2, 0.4}, horizon 10 000 t.u., warm-up 1 200 t.u., for each σ.
  Every policy sees identical traffic for a given (seed, λ).
- **Primary metric:** mean setup latency of accepted SFCs.
- **Secondary:** p95 latency, request-count acceptance, CPU-weighted acceptance, decision time.
- **Hypotheses.** Paired Wilcoxon signed-rank tests over the 30 seeds, two-sided. Holm–Bonferroni correction across
  the 20 (σ, λ) cells within each hypothesis, family α = 0.05.
  - **H1:** kdn3 vs smart-load(α*).
  - **H2:** kdn3 vs model-nom.
  - **H3:** kdn3 vs model-cal.
  - **H4:** kdn3 vs cands-prop (the value of the load/speed information as used by the learned model).
- **Stated expectations** (not tests): H2 and H4 show no or small differences at σ = 0 and kdn3 increasingly
  better as σ grows. H3 shows no practically relevant difference, because a calibrated known-form model has the
  same information as kdn3.
- **Trend check (descriptive):** for each λ, the mean of kdn3 − model-nom across σ, reported as a table.
- **Reported regardless of outcome:** the full table for every policy, σ and λ; kdn3 − oracle; kdn3 vs smart;
  CPU-weighted acceptance; validation metrics of kdn3, û0 and κ̂_n.

## 6. Sensitivity (pre-registered, σ = 0.5, all 5 λ, 30 test seeds; kdn3 retrained, û0/κ̂ refitted, α re-tuned)
- **S1, unknown form:** true delay κ_n · s_v · (1 + 4 ρ_n) (linear). model-nom and model-cal keep the M/M/1 form,
  so they are misspecified; kdn3 does not assume a form. Config `experiments/v3/env_s05_linear.json`.
- **S2, which nodes are slow:** a different permutation π, drawn with `default_rng(2027)`.
  Config `experiments/v3/env_s05_perm2.json`.

## 7. Exploratory (not pre-registered, labelled as such if reported)
- None planned.

## Deviations
Recorded after registration. The pre-registered text above is unchanged.
