import json
import random
import copy
import simpy

from src.topology import create_topology
from src.sfc import SFC_CATALOG
from src.engine import release_resources
from src.algorithms.random import RandomPlacement
from src.utils.telemetry import TelemetryLogger, DummyLogger

def get_network_state(graph, max_cpu):
    """Helper functional to extract snapshot for MDP states."""
    active_nodes = sum(1 for n in graph.nodes() if graph.nodes[n]['cpu_capacity'] < max_cpu)
    free_cpu = sum(graph.nodes[n]['cpu_capacity'] for n in graph.nodes())
    free_bw = sum(graph[u][v]['bandwidth'] for u, v in graph.edges())
    return active_nodes, free_cpu, free_bw

def data_generation_traffic_generator(env, graph, algorithm, config, logger, max_cpu):
    """Custom Data Generator mapping exactly to your ML parameters."""
    sim_cfg = config['simulation']
    lambda_rate = sim_cfg['lambda_rate']
    
    while True:
        inter_arrival = random.expovariate(lambda_rate)
        yield env.timeout(inter_arrival)
        
        sfc_type = random.choice(list(SFC_CATALOG.keys()))
        duration = random.randint(sim_cfg['min_duration'], sim_cfg['max_duration'])
        
        # Capture strictly existing state *BEFORE* attempting allocation
        active_nodes, free_cpu, free_bw = get_network_state(graph, max_cpu)
        
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
        
        # Dump Telemetry iteration locally
        logger.log(
            timestamp=f"{env.now:.2f}",
            sfc_type=sfc_type,
            net_active_nodes=active_nodes,
            net_free_cpu=free_cpu,
            net_free_bw=free_bw,
            unique_nodes=unique_nodes,
            accepted=accepted_int,
            latency=total_delay
        )
        
        if success:
            env.process(release_resources(env, graph, placements, paths_used, bw_demand, duration, DummyLogger()))


def run_data_simulation(config, graph, algorithm, logger):
    """Launch parallel sim isolated exclusively for Dataset Generation"""
    env = simpy.Environment()
    max_cpu = config['network']['node_cpu']
    
    # Initialize Generator instead of base engine generator
    env.process(data_generation_traffic_generator(env, graph, algorithm, config, logger, max_cpu))
    env.run(until=config['simulation']['end_time'])


def main():
    print("Initializing Modular Data Generation for 6G KDN Policy Maker...")
    # Load configuration
    with open('config/config.json', 'r') as f:
        base_config = json.load(f)
        
    base_config['simulation']['end_time'] = 2000 # Enforce target config
    
    # Target Profiles (Domain Randomization)
    profiles = [
        {"name": "Profile 1 (Low Traffic)", "lambda_rate": 0.05, "min_duration": 10, "max_duration": 50},
        {"name": "Profile 2 (Medium Traffic)", "lambda_rate": 0.2, "min_duration": 30, "max_duration": 150},
        {"name": "Profile 3 (Burst Traffic)", "lambda_rate": 0.8, "min_duration": 10, "max_duration": 300},
    ]
    
    telemetry_logger = TelemetryLogger('telemetry_data.csv')
    
    for p in profiles:
        print(f"Running iteration: {p['name']}...")
        config = copy.deepcopy(base_config)
        config['simulation']['lambda_rate'] = p['lambda_rate']
        config['simulation']['min_duration'] = p['min_duration']
        config['simulation']['max_duration'] = p['max_duration']
        
        # Instantiate dependencies cleanly per iteration
        graph = create_topology(config)
        algo = RandomPlacement()
        
        run_data_simulation(config, graph, algo, telemetry_logger)
        
    print("Modular data generation complete! Dataset successfully saved to telemetry_data.csv")


if __name__ == "__main__":
    main()