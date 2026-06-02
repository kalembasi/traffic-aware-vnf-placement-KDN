import simpy
import random
from src.sfc import SFC_CATALOG
from src.utils.logger import log_event

class Metrics:
    def __init__(self):
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.total_latency = 0
        self.active_nodes_history = []
        
def monitor_energy(env, graph, metrics, config):
    net_cfg = config['network']
    max_cpu = net_cfg['node_cpu']
    
    while True:
        yield env.timeout(10)
        active_count = 0
        for node in graph.nodes():
            if graph.nodes[node]['cpu_capacity'] < max_cpu:
                active_count += 1
        metrics.active_nodes_history.append(active_count)

def release_resources(env, graph, placements, paths_used, bw_demand, duration, logger):
    yield env.timeout(duration)
    
    for node, vnf, rsp_cpu, rsp_ram in placements:
        graph.nodes[node]['cpu_capacity'] += rsp_cpu
        graph.nodes[node]['ram_capacity'] += rsp_ram
        
    for edges in paths_used:
        for u, v in edges:
            graph[u][v]['bandwidth'] += bw_demand

def traffic_generator(env, graph, metrics, algorithm, config, logger, schedule=None):
    sim_cfg = config['simulation']
    lambda_rate = sim_cfg['lambda_rate']
    schedule_iter = iter(schedule) if schedule is not None else None

    while True:
        if schedule_iter is not None:
            event = next(schedule_iter, None)
            if event is None:
                return
            inter_arrival, sfc_type, duration = event
        else:
            inter_arrival = random.expovariate(lambda_rate)
            sfc_type = random.choice(list(SFC_CATALOG.keys()))
            duration = random.randint(sim_cfg['min_duration'], sim_cfg['max_duration'])

        yield env.timeout(inter_arrival)
        
        metrics.total_requests += 1
        
        # update tuple to matched returned
        res = algorithm.place_sfc(graph, sfc_type)
        if len(res) == 2:  # old algo interface safely
            success, placements = res
            paths_used = []
            total_delay = 0
            bw_demand = 0
        else:
            success, placements, paths_used, total_delay, bw_demand = res
        
        if success:
            metrics.accepted_requests += 1
            metrics.total_latency += total_delay
            assigned_nodes = [p[0] for p in placements]
            log_event(logger, env.now, f"{sfc_type} SFC Accepted. Placed on Nodes {assigned_nodes}.")
            env.process(release_resources(env, graph, placements, paths_used, bw_demand, duration, logger))
        else:
            metrics.rejected_requests += 1
            log_event(logger, env.now, f"{sfc_type} SFC Rejected. (Resource shortage).")

def run_simulation(config, graph, algorithm, logger):
    env = simpy.Environment()
    metrics = Metrics()
    
    logger.info("--- Starting Modular SFC Simulation ---")
    env.process(traffic_generator(env, graph, metrics, algorithm, config, logger))
    env.process(monitor_energy(env, graph, metrics, config))
    
    env.run(until=config['simulation']['end_time'])
    
    logger.info("\n--- Simulation Summary ---")
    logger.info(f"Total Requests: {metrics.total_requests}")
    logger.info(f"Accepted Requests: {metrics.accepted_requests}")
    logger.info(f"Rejected Requests: {metrics.rejected_requests}")
    
    if metrics.total_requests > 0:
        acceptance_ratio = metrics.accepted_requests / metrics.total_requests * 100
        logger.info(f"Acceptance Ratio: {acceptance_ratio:.2f}%")
        
        avg_latency = (metrics.total_latency / metrics.accepted_requests) if metrics.accepted_requests > 0 else 0
        logger.info(f"Average End-to-End Latency per Accepted SFC (ms): {avg_latency:.2f}")
    else:
        logger.info("Acceptance Ratio: N/A")
        logger.info("Average End-to-End Latency per Accepted SFC (ms): N/A")
        
    avg_active_nodes = sum(metrics.active_nodes_history) / len(metrics.active_nodes_history) if metrics.active_nodes_history else 0
    logger.info(f"Average Number of Active Nodes (Energy Consumption): {avg_active_nodes:.2f}")

