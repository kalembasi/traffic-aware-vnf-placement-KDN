import random
import networkx as nx
from src.algorithms.base import BasePlacement
from src.sfc import VNF_REQUIREMENTS, SFC_CATALOG, SFC_BANDWIDTH

class RandomPlacement(BasePlacement):
    """Exploratory placement that selects randomly from valid physical nodes."""
    def place_sfc(self, graph, sfc_name):
        chain = SFC_CATALOG[sfc_name]
        bw_demand = SFC_BANDWIDTH[sfc_name]
        
        placements = []
        paths_used = []
        total_delay = 0
        prev_node = None
        
        for vnf in chain:
            req_cpu = VNF_REQUIREMENTS[vnf]['cpu']
            req_ram = VNF_REQUIREMENTS[vnf]['ram']
            placed = False
            
            valid_candidates = []
            
            # Find all nodes with sufficient CPU/RAM
            for node in graph.nodes():
                avail_cpu = graph.nodes[node]['cpu_capacity']
                avail_ram = graph.nodes[node]['ram_capacity']
                
                if avail_cpu >= req_cpu and avail_ram >= req_ram:
                    path_edges = []
                    path_delay = 0
                    can_route = True
                    
                    if prev_node is not None and prev_node != node:
                        try:
                            # Evaluate shortest path, verify bandwidth
                            path_nodes = nx.shortest_path(graph, source=prev_node, target=node)
                            for i in range(len(path_nodes) - 1):
                                u = path_nodes[i]
                                v = path_nodes[i+1]
                                if graph[u][v]['bandwidth'] < bw_demand:
                                    can_route = False
                                    break
                                    
                            if can_route:
                                for i in range(len(path_nodes) - 1):
                                    u = path_nodes[i]
                                    v = path_nodes[i+1]
                                    path_edges.append((u, v))
                                    path_delay += graph[u][v]['delay']
                        except nx.NetworkXNoPath:
                            can_route = False

                    if can_route:
                        valid_candidates.append({
                            'node': node,
                            'path_edges': path_edges,
                            'path_delay': path_delay
                        })
            
            if valid_candidates:
                # Randomly pick from any of the valid hardware candidates (Exploration)
                chosen = random.choice(valid_candidates)
                best_node = chosen['node']
                best_path_edges = chosen['path_edges']
                
                graph.nodes[best_node]['cpu_capacity'] -= req_cpu
                graph.nodes[best_node]['ram_capacity'] -= req_ram
                placements.append((best_node, vnf, req_cpu, req_ram))
                
                for u, v in best_path_edges:
                    graph[u][v]['bandwidth'] -= bw_demand
                    
                if best_path_edges:
                    paths_used.append(best_path_edges)
                    
                total_delay += chosen['path_delay']
                prev_node = best_node
                placed = True
                
            if not placed:
                # Standard Rollback
                for p_node, p_vnf, p_cpu, p_ram in placements:
                    graph.nodes[p_node]['cpu_capacity'] += p_cpu
                    graph.nodes[p_node]['ram_capacity'] += p_ram
                for edges in paths_used:
                    for u, v in edges:
                        graph[u][v]['bandwidth'] += bw_demand
                return False, [], [], 0, 0
                
        return True, placements, paths_used, total_delay, bw_demand
