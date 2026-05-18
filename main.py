import json
import logging
from src.utils.logger import setup_logger
from src.topology import create_topology, visualize_topology
from src.algorithms.greedy import GreedyPlacement
from src.algorithms.smart import SmartPlacement
from src.engine import run_simulation

def main():
    # Load configuration
    with open('config/config.json', 'r') as f:
        config = json.load(f)
        
    # Setup Advanced Logger
    logger = setup_logger(log_dir="logs")
    
    # 1/2: Topology & Visualization
    logger.info("Initializing Network Topology...")
    graph = create_topology(config)
    visualize_topology(graph, output_path="topology.png")
    
    # 3: Initialize Algorithm
    # greedy_algo = GreedyPlacement()
    smart_algo = SmartPlacement()
    
    # 4/5: Run Event Simulation Framework
    # run_simulation(config, graph, greedy_algo, logger)
    run_simulation(config, graph, smart_algo, logger)

if __name__ == '__main__':
    main()
