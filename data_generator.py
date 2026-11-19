import json
import random
import copy
import simpy
import os
import pandas as pd

from src.topology import create_topology
from src.sfc import SFC_CATALOG
from src.engine import release_resources
from src.algorithms.greedy import GreedyPlacement
from src.utils.telemetry import TelemetryLogger, DummyLogger

def get_network_state(graph, max_cpu):
    """Helper functional to extract snapshot for MDP states."""
    active_nodes = sum(1 for n in graph.nodes() if graph.nodes[n]['cpu_capacity'] < max_cpu)
    free_cpu = sum(graph.nodes[n]['cpu_capacity'] for n in graph.nodes())
    free_bw = sum(graph[u][v]['bandwidth'] for u, v in graph.edges())
    
    max_node_utilization = max([((max_cpu - graph.nodes[n]['cpu_capacity']) / max_cpu) * 100 for n in graph.nodes()]) if graph.nodes() else 0
    bottleneck_bw = min([graph[u][v]['bandwidth'] for u, v in graph.edges()]) if graph.edges() else 0
    
    return active_nodes, free_cpu, free_bw, max_node_utilization, bottleneck_bw

def data_generation_traffic_generator(env, graph, algorithm, config, logger, max_cpu, stats):
    """Custom Data Generator mapping exactly to your ML parameters."""
    sim_cfg = config['simulation']
    lambda_rate = sim_cfg['lambda_rate']
    
    while True:
        inter_arrival = random.expovariate(lambda_rate)
        yield env.timeout(inter_arrival)
        
        sfc_type = random.choice(list(SFC_CATALOG.keys()))
        duration = random.randint(sim_cfg['min_duration'], sim_cfg['max_duration'])
        
        stats['requests'] += 1
        stats['durations'].append(duration)
        stats['inter_arrivals'].append(inter_arrival)
        
        # Capture strictly existing state *BEFORE* attempting allocation
        active_nodes, free_cpu, free_bw, max_node_utilization, bottleneck_bw = get_network_state(graph, max_cpu)
        
        res = algorithm.place_sfc(graph, sfc_type)
        if len(res) == 2: # Gracefully checks structure
            success, placements = res
            paths_used = []
            total_delay = 0
            bw_demand = 0
        else:
            success, placements, paths_used, total_delay, bw_demand = res
            
        unique_nodes = len(set([p[0] for p in placements])) if success else 0
        accepted_int = 1 if success else 0
        action_max_path_distance = max([len(p) for p in paths_used]) if success and paths_used else 0
        
        # Dump Telemetry iteration locally
        logger.log(
            timestamp=f"{env.now:.2f}",
            sfc_type=sfc_type,
            net_active_nodes=active_nodes,
            net_free_cpu=free_cpu,
            net_free_bw=free_bw,
            net_max_node_utilization=max_node_utilization,
            net_bottleneck_bw=bottleneck_bw,
            action_max_path_distance=action_max_path_distance,
            unique_nodes=unique_nodes,
            accepted=accepted_int,
            latency=total_delay
        )
        
        if success:
            env.process(release_resources(env, graph, placements, paths_used, bw_demand, duration, DummyLogger()))


def run_data_simulation(config, graph, algorithm, logger, stats):
    """Launch parallel sim isolated exclusively for Dataset Generation"""
    env = simpy.Environment()
    max_cpu = config['network']['node_cpu']
    
    # Initialize Generator instead of base engine generator
    env.process(data_generation_traffic_generator(env, graph, algorithm, config, logger, max_cpu, stats))
    env.run(until=config['simulation']['end_time'])


def main(seed=2025, out_path='telemetry_data.csv', stats_path='results/traffic_distributions.csv'):
    print("Initializing Modular Data Generation for 6G KDN Policy Maker...")
    # Seed once: topology delays, arrivals, durations and SFC types all draw from this RNG
    random.seed(seed)
    print(f"  seed={seed}  out={out_path}")
    for path in (out_path, stats_path):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Load configuration
    with open('config/config.json', 'r') as f:
        base_config = json.load(f)
        
    data_gen_config = base_config.get('data_generation', {})
    base_config['simulation']['end_time'] = data_gen_config.get('end_time', 20000)
    
    # Target Profiles (Domain Randomization)
    profiles = data_gen_config.get('profiles', [])
    
    telemetry_logger = TelemetryLogger(out_path)
    distribution_stats = []
    
    for p in profiles:
        print(f"Running iteration: {p['name']}...")
        config = copy.deepcopy(base_config)
        config['simulation']['lambda_rate'] = p['lambda_rate']
        config['simulation']['min_duration'] = p['min_duration']
        config['simulation']['max_duration'] = p['max_duration']
        
        # Instantiate dependencies cleanly per iteration
        graph = create_topology(config)
        algo = GreedyPlacement()
        
        stats = {'requests': 0, 'durations': [], 'inter_arrivals': []}
        run_data_simulation(config, graph, algo, telemetry_logger, stats)
        
        avg_inter_arrival = sum(stats['inter_arrivals']) / len(stats['inter_arrivals']) if stats['inter_arrivals'] else 0
        avg_duration = sum(stats['durations']) / len(stats['durations']) if stats['durations'] else 0
        
        distribution_stats.append({
            'Profile': p['name'],
            'Requests': stats['requests'],
            'Avg_Inter_Arrival': avg_inter_arrival,
            'Avg_Duration': avg_duration
        })
        
    pd.DataFrame(distribution_stats).to_csv(stats_path, index=False)
    print(f"Modular data generation complete! Dataset successfully saved to {out_path}")
    print(f"Traffic distribution saved to {stats_path}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Generate Greedy-labelled telemetry for KDN model training.")
    ap.add_argument('--seed', type=int, default=2025)
    ap.add_argument('--out', default='telemetry_data.csv')
    ap.add_argument('--stats-out', default='results/traffic_distributions.csv')
    a = ap.parse_args()
    main(seed=a.seed, out_path=a.out, stats_path=a.stats_out)