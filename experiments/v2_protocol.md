# v2 Evaluation Protocol (pre-registered)

**Status:** frozen before any KDN-v2 model is trained or evaluated.
The commit that adds this file is the registration timestamp. Any later change is listed under
*Deviations* at the end, with date and reason. Results of v1 (`results/v1_findings.md`) were known
when this protocol was written and motivated its design. v1 is exploratory; v2 is confirmatory.

## 1. Research questions
- **RQ1.** If VNF processing load is a non-linear, traffic-dependent function that the orchestrator does not know, does a telemetry-trained latency model (KDN) place SFCs with lower end-to-end latency than load-unaware heuristics?
- **RQ2.** Does the learned policy match or beat a load-aware heuristic whose weight is *tuned* on the same training period, i.e. is "no handcrafted weight tuning" a real advantage?
- **RQ3.** How far is the learned selector from an oracle that knows the true latency of every candidate?

## 2. Environment (ground truth, hidden from the policies unless stated)

### 2.1 Topology: SNDlib Abilene (`data/external/sndlib/abilene.txt`)
- 12 nodes, 15 undirected links, as published by SNDlib. This replaces the hand-made "Abilene-like" topology of v1.
- **Propagation delay:** great-circle distance between node coordinates × 5 µs/km (light in fibre), no route-inflation factor.
- **Link capacity:** SNDlib pre-installed capacity divided by 9.92 (9920 Mbps → 1000 Mbps; 2480 Mbps → 250 Mbps). This keeps v1's SFC bandwidth demands (10/20/50 Mbps) in a range where links can saturate.
- **Node compute:** 100 CPU and 100 RAM units per node, as in v1 (SNDlib has no compute data).
- **Routing:** delay-weighted shortest path; bandwidth is checked on the chosen path.

### 2.2 Traffic: Abilene traffic matrices (Zhang, 5-min, 2004-03-01 … 2004-09-10, via SNDlib)
- **Time compression:** one 5-min matrix interval = 30 simulation time units (t.u.). A run of 10 000 t.u. replays about 28 h of real traffic.
- **Arrivals:** non-homogeneous Poisson process with rate λ(t) = λ · V(t) / V̄, where V(t) is the total matrix volume and V̄ its mean over the split.
- **Ingress/egress:** for each request, the (src, dst) pair is drawn with probability proportional to the current matrix entry.
- **SFC type and duration:** uniform over {Web, VoIP, Video} and duration U{10…600}, as in v1.
- **Splits:**
  - *train/validation* = days 2004-03-01 … 2004-06-30
  - *test* = 2004-07-01 … 2004-09-10
- Each run starts at a random interval (seeded) within its split.

### 2.3 Per-request traffic profile (KDN VNF dataset, Mestres et al. 2017)
- Each request draws one 20-s traffic batch from the KDN datasets. The draw is stratified by packet count: Web from the lowest third of batches, VoIP from the middle third, Video from the top third.
- The request carries the batch's `numPackets` and `flows` as observable traffic features (an orchestrator can measure these at the ingress).

### 2.4 VNF processing load and delay (hidden ground truth)
- **Measurement family per VNF type** (closest available measurements):
  - Firewall, NAT → *Firewall* (OVS with firewall rules)
  - IDS, DPI → *Snort*
  - TrafficMonitor, SBC, VideoTranscoder → *OVS switch*
- **Relative load** r of a VNF for a request: the measured CPU of a random one of the k=5 nearest batches (by `numPackets`) in that family's dataset, divided by the family's median CPU. This is non-parametric and keeps the measured non-linearity (CPU ∝ packets^0.63–0.73) and noise (≈8 %).
- **Instantaneous load** of a placed VNF: u0 · cpu_reservation(VNF) · r, with **u0 = 0.6** (main setting). Node utilisation ρ_n = Σ load / 100.
- **Processing delay** of a VNF on node n: s_v / (1 − min(ρ_n, 0.95)). ρ_n is measured right after the new SFC is placed (its own load included). Base service times s_v (ms):

  | NAT | Firewall | TrafficMonitor | SBC | IDS | DPI | VideoTranscoder |
  |---|---|---|---|---|---|---|
  | 0.5 | 0.5 | 0.3 | 1.0 | 2.0 | 2.0 | 5.0 |

- **End-to-end (setup) latency** of an accepted SFC = propagation(src → VNF₁ → … → VNF_k → dst) + Σ processing delays.
- **Admission** is unchanged from v1: CPU/RAM *reservations* and link bandwidth. Actual load differs from reservations; only telemetry reveals it.

### 2.5 What each policy may observe
| Information | Greedy | Smart-v2 | Smart-load(α) | KDN-v2 | Oracle |
|---|---|---|---|---|---|
| Topology, link delays, reservations | ✓ | ✓ | ✓ | ✓ | ✓ |
| Measured node utilisation ρ_n (telemetry) | | | ✓ | ✓ | ✓ |
| Request traffic features (packets, flows) | | | | ✓ | ✓ |
| Processing delay function, s_v, loads r | | | | | ✓ |

## 3. Policies
- **greedy:** first-fit (v1 algorithm), delay-weighted routing, ingress and egress included in the latency.
- **smart-v2:** per-VNF score = delay from the previous hop (the ingress for VNF₁) + wake-up penalty 1000; for the last VNF, plus the delay to the egress. Load-unaware.
- **smart-load(α):** smart-v2 score + α · ρ_n (measured utilisation of the candidate node). α is tuned once by grid search over {0, 1, 2, 5, 10, 20, 50, 100, 200} on the *train* split (10 seeds × the 5 λ values, minimising mean latency summed over λ). The chosen α* is then fixed for the test split.
- **Candidate set** (shared by KDN-v2 and the oracle), at most 8 candidates: smart-v2; smart-load(α) for α ∈ {2, 10, 50} (fixed, *not* tuned); least-utilised-node; co-location-first starting at the ingress; 2 random feasible placements.
- **kdn2:** the candidate with the lowest predicted latency = known propagation delay + predicted processing delay from an XGBoost regressor.
  - *Features:* SFC type, request packets and flows, number of distinct hosts, max/mean measured ρ of the chosen hosts, max/sum of CPU reserved per host by this SFC, max number of the SFC's VNFs on one host, network-wide mean ρ, free CPU.
  - *Gatekeeper:* none.
- **kdn2-gate:** kdn2 plus a v2-trained gatekeeper classifier (ablation, reported with both acceptance metrics).
- **oracle:** the candidate with the lowest *true* latency (upper bound for any selector over this candidate set).
- **random:** reference.

## 4. Training data for KDN-v2
- Generated on the *train* split only. The behaviour policy picks uniformly at random among feasible candidates, so the logged actions are diverse and not biased towards one heuristic.
- λ ∈ {0.05, 0.1, 0.2, 0.4}; 5 runs per λ; horizon 10 000 t.u.; seeds 1001–1020.
- Only the chosen action's realised processing delay is logged, as in a real network.
- Model: XGBoost regressor, the same hyper-parameters as v1 (150 trees, depth 5, learning rate 0.1). No tuning on test data. The model is validated on held-out runs (seeds 1017–1020).

## 5. Evaluation
- **Split and scale:** *test* split, seeds 1–30, λ ∈ {0.02, 0.05, 0.1, 0.2, 0.4}, horizon 10 000 t.u., warm-up 1 200 t.u. discarded. Every policy sees identical traffic for a given (seed, λ).
- **Primary metric:** mean setup latency of accepted SFCs.
- **Secondary metrics:** p95 latency, request-count acceptance, CPU-weighted acceptance, decision time.
- **Hypotheses** (paired Wilcoxon signed-rank over seeds, Holm–Bonferroni across the 5 λ values within each hypothesis, family α = 0.05):
  - **H1:** kdn2 has lower mean latency than smart-v2.
  - **H2:** kdn2 vs smart-load(α*), two-sided (no directional expectation).
  - **H3:** kdn2's CPU-weighted acceptance is not lower than smart-v2's by more than 1 pp (one-sided check on the mean difference with its 95 % CI).
- **Reported regardless of outcome:** the full table for every policy and λ, the kdn2–oracle gap, and the kdn2-gate ablation.

## 6. Sensitivity analysis (pre-registered, λ = 0.2, 30 test seeds; KDN retrained and α re-tuned for each variant)
- **S1:** load scale u0 ∈ {0.4, 0.8}.
- **S2:** linear processing delay s_v · (1 + 4 ρ_n) instead of the M/M/1-style curve.

## 7. Exploratory (not pre-registered, labelled as such if reported)
- GÉANT topology with its own traffic matrices.
- Closed-loop retraining on kdn2's own telemetry.

## Deviations
_None yet._
