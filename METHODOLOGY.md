# 6G Knowledge-Defined Networking (KDN): System Architecture & Methodology

This report documents the architectural design, environmental setup, and algorithmic methodologies powering the 6G Knowledge-Defined Networking (KDN) orchestration pipeline. It covers everything from simulated environment mechanics to the two-stage machine learning placement architecture.

## 1. System Architecture & Environment
The project relies on a deeply integrated, event-driven orchestration simulation built primarily around two frameworks:
* **Event-Driven Mechanics (`simpy`):** Resource allocation, network metrics tracking (`monitor_energy`), and traffic influxes execute concurrently based on simulated time (`env.timeout()`).
* **Topology Management (`networkx`):** The system mimics the **12-Node Abilene Network**, mapping connections between major geographical hubs (e.g., NYCG, LOSA, CHIC). 

### Resource Constraints
The topology maintains stateful constraints mimicking real-world virtualized infrastructures:
* **Nodes:** Bounded by strict `cpu_capacity` and `ram_capacity` (base 100.0). Utilization states dictate energy efficiency.
* **Edges (Links):** Bounded by `bandwidth` limitations (base 1000.0) with randomly assigned propagation `delay` constraints parameters (2ms – 10ms), essential for realistically modeling end-to-end telemetry.

## 2. Traffic Modeling & Data Generation Pipeline
To train an overarching KDN agent, the system requires diverse, voluminous, and highly realistic telemetry data representing telecommunication fluctuations.

### Dynamic Configuration and Stochastic Arrival
System configurations are entirely decentralized using `config/config.json`. The `data_generator.py` pipeline utilizes a mathematical **Poisson point process**. By mapping traffic generation using an exponential distribution (`random.expovariate(lambda_rate)`), the timing between Service Function Chain (SFC) requests precisely mimics unpredictable, bursty real-world network traffic.

### Domain Randomization Strategy
To ensure the machine learning models (XGBoost) do not overfit to a specific network state, the platform implements **Domain Randomization** through distinctive traffic profiles:
1. **Low Traffic ($\lambda=0.05$):** Sparse requests allowing the network to fully clear resources.
2. **Medium Traffic ($\lambda=0.2$):** Steady-state operations representing standard daily usage.
3. **Burst Traffic ($\lambda=0.8$):** Stretches node limits and heavily congests bandwidth bottlenecks.

Telemetry data (active nodes, free resources, bandwidth bottlenecks) is strictly scraped instantly *prior* to algorithm routing execution to reflect the exact Markov Decision Process (MDP) observational state. The generator logs iterations deterministically to `results/traffic_distributions.csv` and outputs the final training corpus to `telemetry_data.csv`.

## 3. Baseline Placement Algorithms
To evaluate the ML-based KDN architecture, two deterministic algorithm baselines operate as control groups.

### GreedyPlacement (The First-Fit Baseline)
The `GreedyPlacement` algorithm acts as the naive baseline. It iterates sequentially through the available topology and assigns the Virtual Network Function (VNF) to the very first node possessing sufficient CPU/RAM and an open bandwidth path.
* **Limitations:** The greedy strategy severely lacks spatial awareness. It frequently subjects traffic to "node tromboning"—bouncing connections inefficiently back and forth across the network. This yields significantly inflated latency and sub-optimal bandwidth exhaustion.

### SmartPlacement (The Heuristic Baseline)
The `SmartPlacement` algorithm introduces a strict mathematical scoring function designed to jointly optimize performance and energy consumption. It evaluates all viable nodes simultaneously:
* **Co-location / Energy Priority:** It implements a substantial `WAKE_UP_PENALTY` (1000 points) applied entirely to dormant nodes. It heavily prefers stacking VNFs into nodes already active, mirroring real-world energy preservation mechanics.
* **Shortest-Path Logic:** The algorithm computes Dijkstra's shortest path from the previous node, adding aggregate path delay to the candidate's score. 
The algorithm systematically selects the topology configuration with the lowest possible penalty score.

## 4. KDN Architecture: XGBoost Placement Strategy
Surpassing traditional Software-Defined Networking (SDN) protocols, the core of the thesis leverages historical traffic telemetry to orchestrate routing proactively via a **Two-Stage Machine Learning Architecture**.

### Stage 1: The Gatekeeper (Admission Classifier)
Using the pre-trained `models/kdn_classifier.json`, the orchestrator predicts absolute network capability using state-array features (Current Free CPU, Bottleneck BW, Max Utilization). 
* **Mechanism:** Rather than running computationally expensive search algorithms on doomed requests, the Gatekeeper predicts a binary outcome (`1` for Routable, `0` for Unroutable). Unroutable requests are gracefully skipped, significantly lowering systematic overhead.

### Stage 2: The Optimizer (Policy Regressor)
If admitted by the Gatekeeper, the methodology pivots to identifying the most highly optimized path using `models/kdn_regressor.json`. 
* **Candidate Generation:** Because calculating all possible permutations inside the Abilene network scales at $O(N!)$, the system generates 5 controlled "Candidate Action Proposals": one structurally mapped topology-aware candidate and four randomized exploratory candidates.
* **Prediction & Execution:** The XGBoost Regressor consumes the network state bundled with the proposed actions (unique nodes used, max path jumps) and quantitatively predicts expected **End-to-End Latency**. The orchestrator enforces the candidate that promises the lowest predicted latency, effectively substituting exhaustive algorithm searching with sub-millisecond AI inference.