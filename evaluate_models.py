import json
import simpy
import random
import sys

from src.topology import create_topology
from src.engine import traffic_generator, monitor_energy
from src.algorithms.greedy import GreedyPlacement
from src.algorithms.smart import SmartPlacement
from src.algorithms.xgboost import XGBoostPlacement
from src.utils.telemetry import DummyLogger

# Custom simplified Metrics aggregator to bypass verbose Engine limits
class EvalMetrics:
    def __init__(self):
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.total_latency = 0
        self.active_nodes_history = []

def run_isolated_simulation(algo_instance, seed=42):
    random.seed(seed)
    
    with open('config/config.json', 'r') as f:
        config = json.load(f)
        
    config['simulation']['lambda_rate'] = 0.2
    config['simulation']['end_time'] = 1000
    
    graph = create_topology(config)
    env = simpy.Environment()
    metrics = EvalMetrics()
    dummy_logger = DummyLogger()
    
    env.process(traffic_generator(env, graph, metrics, algo_instance, config, dummy_logger))
    env.process(monitor_energy(env, graph, metrics, config))
    
    env.run(until=config['simulation']['end_time'])
    
    total = metrics.accepted_requests + metrics.rejected_requests
    acc_ratio = (metrics.accepted_requests / total) * 100 if total > 0 else 0
    avg_latency = metrics.total_latency / metrics.accepted_requests if metrics.accepted_requests > 0 else 0
    avg_active = sum(metrics.active_nodes_history) / len(metrics.active_nodes_history) if metrics.active_nodes_history else 0
    
    return acc_ratio, avg_latency, avg_active

def main():
    print("Evaluating KDN Algorithms...")
    
    algs = {
        "GreedyPlacement": GreedyPlacement(),
        "SmartPlacement": SmartPlacement(),
        "XGBoostPlacement": XGBoostPlacement()
    }
    
    results = {}
    for name, algo in algs.items():
        print(f"Running simulation for {name}...")
        acc, lat, act = run_isolated_simulation(algo)
        results[name] = {"acc": acc, "lat": lat, "act": act}
        
    print("\n| Algorithm        | Acceptance Ratio | Avg Latency | Avg Active Nodes |")
    print("|------------------|------------------|-------------|------------------|")
    for name, metrics in results.items():
        print(f"| {name.ljust(16)} | {metrics['acc']:>15.2f}% | {metrics['lat']:>11.2f} | {metrics['act']:>16.2f} |")

if __name__ == "__main__":
    main()