# Evaluation Protocol (pre-registered)

**Registration.** Sections 1–6 were committed in `82229de` before any data was generated, any model was trained or
any policy was evaluated. Section 7 was committed in `fd640b6` after the results of sections 1–6 were known and
before any of its runs. This file merges the two texts. Section 2 inlines the environment that `82229de`
incorporated by reference (registered in `48e6edb`). Editorial changes only: policy names were shortened
(`kdn3` → `kdn`, `kdn3-greedy` → `kdn-greedy`), file paths were updated, references to earlier versions of the
project were removed, and the SFC catalogue and one-line descriptions of random/greedy were added. No design choice
was changed. The original texts are in the git history.

## 1. Research questions
- **RQ1.** As the hidden heterogeneity of node processing speed grows, does a telemetry-trained latency model
  (KDN) place SFCs with lower latency than (a) a tuned load-aware heuristic and (b) an analytical selector that
  knows the delay formula but not the node speeds?
- **RQ2.** Does learning beat an analytical selector that knows the delay formula *and* calibrates per-node
  speeds from the same training telemetry? In other words, is the value of learning that it does not need
  the functional form?
- **RQ3.** How far is the learned selector from an oracle that knows the true latency of every candidate?

## 2. Environment (ground truth, hidden from the policies unless stated)

### 2.1 Topology: SNDlib Abilene (`data/external/sndlib/abilene.txt`)
- 12 nodes, 15 undirected links, as published by SNDlib.
- **Propagation delay:** great-circle distance between node coordinates × 5 µs/km (light in fibre).
- **Link capacity:** SNDlib pre-installed capacity divided by 9.92 (9920 Mbps → 1000 Mbps; 2480 Mbps → 250 Mbps),
  so that the SFC bandwidth demands (10/20/50 Mbps) can saturate links.
- **Node compute:** 100 CPU and 100 RAM units per node (SNDlib has no compute data).
- **Routing:** delay-weighted shortest path; bandwidth is checked on the chosen path.

### 2.2 Traffic: Abilene traffic matrices (Zhang, 5-min, 2004-03-01 … 2004-09-10, via SNDlib)
- **Time compression:** one 5-min matrix interval = 30 simulation time units (t.u.). A run of 10 000 t.u. replays
  about 28 h of real traffic.
- **Arrivals:** non-homogeneous Poisson process with rate λ(t) = λ · V(t) / V̄, where V(t) is the total matrix
  volume and V̄ its mean over the split.
- **Ingress/egress:** for each request, the (src, dst) pair is drawn with probability proportional to the current
  matrix entry.
- **SFC type and duration:** uniform over {Web, VoIP, Video}; duration uniform over {10, …, 600} t.u.

  | SFC | Chain | Bandwidth (Mbps) |
  |---|---|---|
  | Web | NAT → Firewall → TrafficMonitor | 10 |
  | VoIP | NAT → SBC → Firewall → IDS | 20 |
  | Video | NAT → DPI → VideoTranscoder | 50 |

- **Splits:** *train/validation* = 2004-03-01 … 2004-06-30; *test* = 2004-07-01 … 2004-09-10.
  Each run starts at a random (seeded) interval within its split.

### 2.3 Per-request traffic profile (KDN VNF dataset, Mestres et al. 2017)
- Each request draws one 20-s traffic batch from the KDN datasets, stratified by packet count: Web from the lowest
  third of batches, VoIP from the middle third, Video from the top third.
- The request carries the batch's `numPackets` and `flows` as observable traffic features (an orchestrator can
  measure these at the ingress).

### 2.4 VNF processing load and delay (hidden)
- **Measurement family per VNF type** (closest available measurements): Firewall, NAT → *Firewall*;
  IDS, DPI → *Snort*; TrafficMonitor, SBC, VideoTranscoder → *OVS switch*.
- **Relative load** r of a VNF for a request: the measured CPU of a random one of the k = 5 nearest batches
  (by `numPackets`) in that family's dataset, divided by the family's median CPU.
- **Instantaneous load** of a placed VNF: u0 · cpu_reservation(VNF) · r, with u0 = 0.6.
  Node utilisation ρ_n = Σ load / 100.
- **Node speed factor κ_n.** κ_n = exp(σ · z_{π(n)}), where z_i = Φ⁻¹((i + 0.5)/12), i = 0…11, and π is a permutation
  of the 12 nodes (sorted by name) drawn with `numpy.random.default_rng(2026).permutation(12)`. The geometric mean of
  κ is 1 for every σ, and the same nodes are slow at every σ; only the spread changes.
  **Levels:** σ ∈ {0, 0.25, 0.5, 1.0}; the κ ranges are [1, 1], [0.65, 1.54], [0.42, 2.38] and [0.18, 5.65].
  κ does not change capacity, reservations, load or admission. It changes only how long a VNF takes to process
  traffic on that node.
- **Processing delay** of VNF v on node n: κ_n · s_v / (1 − min(ρ_n, 0.95)), with ρ_n measured right after the new
  SFC is placed (its own load included). Base service times s_v (ms):

  | NAT | Firewall | TrafficMonitor | SBC | IDS | DPI | VideoTranscoder |
  |---|---|---|---|---|---|---|
  | 0.5 | 0.5 | 0.3 | 1.0 | 2.0 | 2.0 | 5.0 |

- **End-to-end (setup) latency** of an accepted SFC = propagation(src → VNF₁ → … → VNF_k → dst) + Σ processing delays.
- **Admission** uses CPU/RAM *reservations* and link bandwidth only. Actual load differs from reservations; only
  telemetry reveals it.
- Config files: `experiments/envs/s0.json`, `s025.json`, `s05.json`, `s1.json`.

### 2.5 What each policy may observe
| Information | Greedy / Smart | Smart-load(α) | cands-prop | model-nom | model-cal | KDN | Oracle |
|---|---|---|---|---|---|---|---|
| Topology, link delays, reservations | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Measured node utilisation ρ_n (telemetry) | | ✓ | | ✓ | ✓ | ✓ | ✓ |
| Request traffic features (packets, flows) | | | | | | ✓ | ✓ |
| Delay formula and nominal s_v | | | | ✓ | ✓ | | ✓ |
| Training telemetry (train split) | | α tuning | | û0 | û0, κ̂_n | model | |
| True κ_n, true r, true delay | | | | | | | ✓ |

## 3. Policies
- **random:** each VNF on a uniformly random feasible node. **greedy:** first-fit in a fixed node order.
- **smart:** per-VNF score = propagation delay from the previous hop (the ingress for VNF₁); for the last VNF,
  plus the delay to the egress.
- **smart-load(α):** smart + α · ρ_n. α is tuned separately for each environment on the train split
  (grid {0, 1, 2, 5, 10, 20, 50, 100, 200}, seeds 101–110, the 5 λ values, minimising the sum over λ of the mean
  latency). The chosen α* is fixed for the test split.
- **Candidate set** (shared by every selector below and by the behaviour policy), at most 8 distinct placements:
  smart; smart-load(α) for α ∈ {2, 10, 50} (fixed, not tuned); least-utilised node; co-location starting at the
  ingress; 2 shuffled first-fit placements.
- **Selectors over the candidate set** (they differ only in how they score a candidate):
  - **cands-prop:** known propagation delay only (no load information).
  - **model-nom:** propagation + Σ_v s_v / (1 − min(ρ̂_n, 0.95)), where ρ̂_n = (load_n + û0 · CPU reserved by this
    SFC on n) / cpu_max. It knows the formula and the nominal s_v, and assumes κ_n = 1. û0 is one scalar fitted on
    the training telemetry: the observed increase in node load divided by the CPU reserved on that node.
  - **model-cal:** model-nom with κ̂_n · s_v, where κ̂_n is the median over the training telemetry of
    (observed VNF delay on n) / (s_v / (1 − min(ρ_n,after, 0.95))). It knows the formula and calibrates node speeds.
  - **kdn:** propagation + Σ_v f̂(VNF v on its host), where f̂ is an XGBoost regressor of the per-VNF processing
    delay. Features: VNF type (one-hot), host node (one-hot), measured ρ of the host before placement, CPU reserved
    by this SFC on the host, number of this SFC's VNFs on the host, request packets and flows, network-wide mean ρ.
    It does not know the formula. 150 trees, depth 5, learning rate 0.1.
  - **oracle:** the candidate with the lowest true latency (upper bound for any selector over this set).

## 4. Training and calibration data
- One data set per environment, generated on the *train* split by the behaviour policy (uniform random choice
  among the candidates), λ ∈ {0.05, 0.1, 0.2, 0.4} × seeds 1001–1020, horizon 10 000 t.u.
- One row per VNF of every accepted request: host, VNF type, CPU reserved by the SFC on the host, host load before
  and after placement, observed processing delay of the VNF, request packets and flows, network mean ρ.
  Per-VNF processing delay is assumed to be measurable (per-VNF telemetry).
- kdn, û0 and κ̂_n are fitted on seeds 1001–1016. Seeds 1017–1020 are held out for validation metrics.

## 5. Evaluation
- Test split, seeds 1–30, λ ∈ {0.02, 0.05, 0.1, 0.2, 0.4}, horizon 10 000 t.u., warm-up 1 200 t.u., for each σ.
  Every policy sees identical traffic for a given (seed, λ).
- **Primary metric:** mean setup latency of accepted SFCs.
- **Secondary:** p95 latency, request-count acceptance, CPU-weighted acceptance, decision time.
- **Hypotheses.** Paired Wilcoxon signed-rank tests over the 30 seeds, two-sided. Holm–Bonferroni correction across
  the 20 (σ, λ) cells within each hypothesis, family α = 0.05.
  - **H1:** kdn vs smart-load(α*).
  - **H2:** kdn vs model-nom.
  - **H3:** kdn vs model-cal.
  - **H4:** kdn vs cands-prop (the value of the load/speed information as used by the learned model).
- **Stated expectations** (not tests): H2 and H4 show no or small differences at σ = 0 and kdn increasingly
  better as σ grows. H3 shows no practically relevant difference, because a calibrated known-form model has the
  same information as kdn.
- **Trend check (descriptive):** for each λ, the mean of kdn − model-nom across σ, reported as a table.
- **Reported regardless of outcome:** the full table for every policy, σ and λ; kdn − oracle; kdn vs smart;
  CPU-weighted acceptance; validation metrics of kdn, û0 and κ̂_n.

## 6. Sensitivity (σ = 0.5, all 5 λ, 30 test seeds; kdn retrained, û0/κ̂ refitted, α re-tuned)
- **S1, unknown form:** true delay κ_n · s_v · (1 + 4 ρ_n) (linear). model-nom and model-cal keep the M/M/1 form,
  so they are misspecified; kdn does not assume a form. Config `experiments/envs/s05_linear.json`.
- **S2, which nodes are slow:** a different permutation π, drawn with `default_rng(2027)`.
  Config `experiments/envs/s05_perm2.json`.

## 7. Addendum: the model builds the placement (registered after the results of sections 1–6)
**Motivation.** At λ ≥ 0.1, every selector over the heuristic candidate set, including the oracle, performed about
the same, which suggests that the candidate set limits what any learned model can do.
**Question.** If the model builds the placement itself instead of choosing among heuristic candidates, does it do
better?

- **Policies** (no retraining; the models and calibration of sections 4–5 are reused):
  - **kdn-greedy:** VNFs are placed one by one, in chain order. For each VNF, every feasible node is scored:
    propagation delay from the previous hop + the predicted processing delay of the SFC's VNFs placed so far
    including this one (for the last VNF, plus the delay to the egress). The lowest score wins. The prediction
    uses the kdn per-VNF regressor.
  - **model-cal-greedy:** the same search, with the model-cal formula instead of the regressor.
  - **oracle-greedy:** the same search, with the true processing delay. It is an upper bound for this search, not
    a global optimum.
- **Evaluation:** the 4 main environments (σ ∈ {0, 0.25, 0.5, 1}), test split, seeds 1–30, the 5 λ values, same
  horizon and warm-up. Sensitivity environments are not run. Paired two-sided Wilcoxon over seeds, Holm across the
  20 (σ, λ) cells per comparison:
  - **H5:** kdn-greedy vs smart-load(α*).
  - **H6:** kdn-greedy vs kdn (candidate-based).
- Reported without a test: kdn-greedy − oracle-greedy and kdn-greedy − model-cal-greedy.

## Deviations
None.
