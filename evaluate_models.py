import json
import logging
import simpy
import random
import sys
import os
import numpy as np
import pandas as pd

from src.topology import create_topology
from src.engine import traffic_generator, monitor_energy
from src.sfc import SFC_CATALOG
from src.algorithms.greedy import GreedyPlacement
from src.algorithms.smart import SmartPlacement
from src.algorithms.xgboost import XGBoostPlacement

EVAL_SEEDS = [42, 7, 123, 0, 99]


# ---------------------------------------------------------------------------
# Metrics aggregator
# ---------------------------------------------------------------------------

class EvalMetrics:
    def __init__(self):
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.total_latency = 0
        self.active_nodes_history = []


# ---------------------------------------------------------------------------
# Per-algorithm logger factory
# ---------------------------------------------------------------------------

def _make_algo_logger(prefix: str) -> logging.Logger:
    """Creates a dedicated logger that writes to results/<prefix>_output.log and stdout."""
    logger = logging.getLogger(f"EvalSim_{prefix}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    log_path = os.path.join('results', f'{prefix}_output.log')
    fh = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)

    fmt = logging.Formatter('%(asctime)s  %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def _close_logger(logger: logging.Logger):
    for h in list(logger.handlers):
        h.flush()
        h.close()
        logger.removeHandler(h)


# ---------------------------------------------------------------------------
# Markdown report writer
# ---------------------------------------------------------------------------

def _write_md_report(prefix: str, algo_name: str, config: dict, graph, metrics: EvalMetrics,
                     schedule_len: int, seed: int,
                     acc_ratio: float, avg_latency: float, avg_active: float):
    net_cfg = config['network']
    sim_cfg = config['simulation']

    edge_delays = [graph[u][v]['delay'] for u, v in graph.edges()]
    delay_min = min(edge_delays)
    delay_max = max(edge_delays)
    delay_avg = sum(edge_delays) / len(edge_delays)

    lines = [
        f"# {algo_name} - Evaluation Results (seed={seed})",
        "",
        "## Configuration",
        "",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Seed | {seed} |",
        f"| End Time | {sim_cfg['end_time']} |",
        f"| Lambda Rate | {sim_cfg['lambda_rate']} |",
        f"| Min Duration | {sim_cfg['min_duration']} |",
        f"| Max Duration | {sim_cfg['max_duration']} |",
        f"| Node CPU | {net_cfg['node_cpu']} |",
        f"| Node RAM | {net_cfg['node_ram']} |",
        f"| Edge BW | {net_cfg['edge_bw']} |",
        f"| Min Delay | {net_cfg['min_delay']} |",
        f"| Max Delay | {net_cfg['max_delay']} |",
        "",
        "## Network Topology",
        "",
        f"| Property | Value |",
        f"|----------|-------|",
        f"| Nodes | {graph.number_of_nodes()} |",
        f"| Edges | {graph.number_of_edges()} |",
        f"| Edge Delay Min (ms) | {delay_min} |",
        f"| Edge Delay Max (ms) | {delay_max} |",
        f"| Edge Delay Avg (ms) | {delay_avg:.2f} |",
        "",
        "## Traffic Schedule",
        "",
        f"| Property | Value |",
        f"|----------|-------|",
        f"| Pre-generated Events | {schedule_len} |",
        f"| Seed | {seed} |",
        "",
        "## Simulation Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Requests | {metrics.total_requests} |",
        f"| Accepted Requests | {metrics.accepted_requests} |",
        f"| Rejected Requests | {metrics.rejected_requests} |",
        f"| Acceptance Ratio | {acc_ratio:.2f}% |",
        f"| Avg Latency (ms) | {avg_latency:.2f} |",
        f"| Avg Active Nodes | {avg_active:.2f} |",
        "",
    ]

    md_path = os.path.join('results', f'{prefix}_output.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ---------------------------------------------------------------------------
# Summary markdown report (across all seeds)
# ---------------------------------------------------------------------------

def _write_summary_md(summary_rows: list, seeds: list):
    seed_str = ', '.join(str(s) for s in seeds)
    lines = [
        "# KDN Placement Algorithms - Evaluation Summary",
        "",
        f"**Seeds:** {seed_str}  |  **Runs per algorithm:** {len(seeds)}",
        "",
        "## Results (Mean +/- Std)",
        "",
        "| Algorithm | Acceptance Ratio | Avg Latency (ms) | Avg Active Nodes |",
        "|-----------|-----------------|-----------------|-----------------|",
    ]
    for r in summary_rows:
        lines.append(
            f"| {r['Algorithm']} "
            f"| {r['Acc_Mean']:.2f}% +/- {r['Acc_Std']:.2f}% "
            f"| {r['Lat_Mean']:.2f} +/- {r['Lat_Std']:.2f} "
            f"| {r['Act_Mean']:.2f} +/- {r['Act_Std']:.2f} |"
        )
    lines += ["", "## Per-Algorithm Breakdown", ""]
    for r in summary_rows:
        lines += [
            f"### {r['Algorithm']}",
            "",
            "| Metric | Mean | Std | Min | Max |",
            "|--------|------|-----|-----|-----|",
            f"| Acceptance Ratio (%) | {r['Acc_Mean']:.2f} | {r['Acc_Std']:.2f} | {r['Acc_Min']:.2f} | {r['Acc_Max']:.2f} |",
            f"| Avg Latency (ms)     | {r['Lat_Mean']:.2f} | {r['Lat_Std']:.2f} | {r['Lat_Min']:.2f} | {r['Lat_Max']:.2f} |",
            f"| Avg Active Nodes     | {r['Act_Mean']:.2f} | {r['Act_Std']:.2f} | {r['Act_Min']:.2f} | {r['Act_Max']:.2f} |",
            "",
        ]
    with open(os.path.join('results', 'evaluation_summary.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ---------------------------------------------------------------------------
# Pre-generate traffic schedule from the seeded RNG
# ---------------------------------------------------------------------------

def _generate_schedule(config: dict) -> list:
    """
    Samples the full traffic stream (inter-arrivals, SFC types, durations) from
    the current global RNG state and returns it as a list of tuples.
    This must be called AFTER random.seed() and create_topology() so that the
    schedule is isolated from any random calls made inside placement algorithms.
    """
    sim_cfg = config['simulation']
    lambda_rate = sim_cfg['lambda_rate']
    end_time = sim_cfg['end_time']
    sfc_keys = list(SFC_CATALOG.keys())

    schedule = []
    t = 0.0
    while t < end_time:
        inter_arrival = random.expovariate(lambda_rate)
        sfc_type = random.choice(sfc_keys)
        duration = random.randint(sim_cfg['min_duration'], sim_cfg['max_duration'])
        t += inter_arrival
        if t >= end_time:
            break
        schedule.append((inter_arrival, sfc_type, duration))
    return schedule


# ---------------------------------------------------------------------------
# Isolated simulation runner
# ---------------------------------------------------------------------------

def run_isolated_simulation(algo_name: str, algo_instance, seed: int):
    # --- Phase 1: Seed & config ---
    random.seed(seed)
    prefix = f"{algo_name}_seed{seed}"

    logger = _make_algo_logger(prefix)
    logger.info("=" * 60)
    logger.info(f"ALGORITHM: {algo_name}  |  SEED: {seed}")
    logger.info("=" * 60)
    logger.info("Loading configuration from config/config.json ...")

    with open('config/config.json', 'r') as f:
        config = json.load(f)

    config['simulation']['lambda_rate'] = 0.2
    config['simulation']['end_time'] = 1000

    sim_cfg = config['simulation']
    net_cfg = config['network']
    logger.info(f"  Simulation -> end_time={sim_cfg['end_time']}  lambda_rate={sim_cfg['lambda_rate']}"
                f"  min_duration={sim_cfg['min_duration']}  max_duration={sim_cfg['max_duration']}")
    logger.info(f"  Network    -> node_cpu={net_cfg['node_cpu']}  node_ram={net_cfg['node_ram']}"
                f"  edge_bw={net_cfg['edge_bw']}  delay=[{net_cfg['min_delay']}, {net_cfg['max_delay']}]")

    # --- Phase 2: Topology ---
    logger.info("Creating network topology (Abilene, 12 nodes) ...")
    graph = create_topology(config)

    edge_delays = [graph[u][v]['delay'] for u, v in graph.edges()]
    delay_min = min(edge_delays)
    delay_max = max(edge_delays)
    delay_avg = sum(edge_delays) / len(edge_delays)
    logger.info(f"  Topology created: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.")
    logger.info(f"  Edge delays (ms): min={delay_min}  max={delay_max}  avg={delay_avg:.2f}")

    # --- Phase 3: Pre-generate traffic schedule ---
    logger.info(f"Pre-generating traffic schedule (seed={seed}) ...")
    schedule = _generate_schedule(config)
    logger.info(f"  Traffic schedule ready: {len(schedule)} events (arrivals, SFC types, durations locked).")

    # --- Phase 4: Initialize algorithm ---
    logger.info(f"Initializing {algo_name} ...")
    if isinstance(algo_instance, XGBoostPlacement):
        logger.info("  Loading XGBoost models: models/kdn_classifier.json, models/kdn_regressor.json, models/label_encoder.pkl")

    # --- Phase 5: Run simulation ---
    logger.info(f"Starting simulation: {algo_name} | end_time={sim_cfg['end_time']} | lambda_rate={sim_cfg['lambda_rate']}")
    logger.info("-" * 60)

    env = simpy.Environment()
    metrics = EvalMetrics()

    env.process(traffic_generator(env, graph, metrics, algo_instance, config, logger, schedule=schedule))
    env.process(monitor_energy(env, graph, metrics, config))

    env.run(until=config['simulation']['end_time'])

    # --- Phase 6: Compute results ---
    total = metrics.accepted_requests + metrics.rejected_requests
    acc_ratio = (metrics.accepted_requests / total) * 100 if total > 0 else 0
    avg_latency = metrics.total_latency / metrics.accepted_requests if metrics.accepted_requests > 0 else 0
    avg_active = sum(metrics.active_nodes_history) / len(metrics.active_nodes_history) if metrics.active_nodes_history else 0

    logger.info("-" * 60)
    logger.info("Simulation complete.")
    logger.info(f"  Total={metrics.total_requests}  Accepted={metrics.accepted_requests}  Rejected={metrics.rejected_requests}")
    logger.info(f"  Acceptance Ratio : {acc_ratio:.2f}%")
    logger.info(f"  Avg Latency (ms) : {avg_latency:.2f}")
    logger.info(f"  Avg Active Nodes : {avg_active:.2f}")

    # --- Phase 7: Write markdown report ---
    _write_md_report(prefix, algo_name, config, graph, metrics, len(schedule), seed,
                     acc_ratio, avg_latency, avg_active)
    logger.info(f"  Reports -> results/{prefix}_output.log  |  results/{prefix}_output.md")

    _close_logger(logger)
    return acc_ratio, avg_latency, avg_active


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    os.makedirs('results', exist_ok=True)
    print("=" * 60)
    print("Evaluating KDN Placement Algorithms")
    print(f"Seeds: {EVAL_SEEDS}  ({len(EVAL_SEEDS)} runs per algorithm)")
    print("=" * 60)

    algo_instances = {
        "GreedyPlacement":  GreedyPlacement(),
        "SmartPlacement":   SmartPlacement(),
        "XGBoostPlacement": XGBoostPlacement(),
    }

    results_by_algo = {name: [] for name in algo_instances}
    per_seed_csv = []

    for seed in EVAL_SEEDS:
        print(f"\n{'='*60}")
        print(f"SEED: {seed}")
        print(f"{'='*60}")
        for name, algo in algo_instances.items():
            print(f"\n>>> {name}  (seed={seed})")
            acc, lat, act = run_isolated_simulation(name, algo, seed=seed)
            results_by_algo[name].append((acc, lat, act))
            per_seed_csv.append({
                "Algorithm": name, "Seed": seed,
                "Acceptance_Ratio": acc, "Avg_Latency": lat, "Avg_Active_Nodes": act,
            })

    pd.DataFrame(per_seed_csv).to_csv('results/evaluation_metrics.csv', index=False)

    summary_rows = []
    for name, runs in results_by_algo.items():
        accs = [r[0] for r in runs]
        lats = [r[1] for r in runs]
        acts = [r[2] for r in runs]
        summary_rows.append({
            "Algorithm": name, "Seeds_Run": len(runs),
            "Acc_Mean": np.mean(accs), "Acc_Std": np.std(accs),
            "Acc_Min":  np.min(accs),  "Acc_Max": np.max(accs),
            "Lat_Mean": np.mean(lats), "Lat_Std": np.std(lats),
            "Lat_Min":  np.min(lats),  "Lat_Max": np.max(lats),
            "Act_Mean": np.mean(acts), "Act_Std": np.std(acts),
            "Act_Min":  np.min(acts),  "Act_Max": np.max(acts),
        })

    pd.DataFrame(summary_rows).to_csv('results/evaluation_summary.csv', index=False)
    _write_summary_md(summary_rows, EVAL_SEEDS)

    print(f"\n\n{'='*60}")
    print(f"FINAL RESULTS  (mean +/- std over {len(EVAL_SEEDS)} seeds: {EVAL_SEEDS})")
    print(f"{'='*60}")
    print(f"| {'Algorithm':<18} | {'Acceptance Ratio':>25} | {'Avg Latency (ms)':>22} | {'Avg Active Nodes':>22} |")
    print(f"|{'-'*20}|{'-'*27}|{'-'*24}|{'-'*24}|")
    for r in summary_rows:
        acc_s = f"{r['Acc_Mean']:.2f}% +/- {r['Acc_Std']:.2f}%"
        lat_s = f"{r['Lat_Mean']:.2f} +/- {r['Lat_Std']:.2f}"
        act_s = f"{r['Act_Mean']:.2f} +/- {r['Act_Std']:.2f}"
        print(f"| {r['Algorithm']:<18} | {acc_s:>25} | {lat_s:>22} | {act_s:>22} |")

    print(f"\nOutput files in results/:")
    print(f"  evaluation_metrics.csv    (per-seed raw data, {len(EVAL_SEEDS)*len(algo_instances)} rows)")
    print(f"  evaluation_summary.csv    (mean/std/min/max per algorithm)")
    print(f"  evaluation_summary.md     (formatted summary report)")
    for name in algo_instances:
        for s in EVAL_SEEDS:
            print(f"  {name}_seed{s}_output.log / .md")
    main()