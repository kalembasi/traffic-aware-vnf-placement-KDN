import networkx as nx
from src.algorithms.base import BasePlacement
from src.sfc import VNF_REQUIREMENTS, SFC_CATALOG, SFC_BANDWIDTH

class SmartPlacement(BasePlacement):
    WAKE_UP_PENALTY = 1000
    
    # Optional: read from graph/config, but using 100.0 as your default base threshold
    MAX_CPU = 100.0 

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
            
            # List to store eligible node candidates alongside their score
            valid_candidates = []
            
            for node in graph.nodes():
                avail_cpu = graph.nodes[node]['cpu_capacity']
                avail_ram = graph.nodes[node]['ram_capacity']
                
                # 1. Capacity Verification
                if avail_cpu >= req_cpu and avail_ram >= req_ram:
                    score = 0
                    path_edges = []
                    path_delay = 0
                    can_route = True
                    
                    # Condition 1: Energy Active Penalty
                    # If the node's available CPU is at its maximum, it's currently inactive.
                    if avail_cpu >= self.MAX_CPU:
                        score += self.WAKE_UP_PENALTY
                        
                    # Condition 2: Network Latency / Delay Calculation
                    if prev_node is not None:
                        if prev_node != node:
                            try:
                                path_nodes = nx.shortest_path(graph, source=prev_node, target=node)
                                
                                # Check Bandwidth and calculate Delay
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
                                        
                                    score += path_delay
                                    
                            except nx.NetworkXNoPath:
                                can_route = False

                    if can_route:
                        valid_candidates.append({
                            'node': node,
                            'score': score,
                            'path_edges': path_edges,
                            'path_delay': path_delay
                        })
            
            # 3. Selection Node Process
            if valid_candidates:
                # Sort valid nodes by our cost score primarily
                valid_candidates.sort(key=lambda x: x['score'])
                best_candidate = valid_candidates[0]
                best_node = best_candidate['node']
                best_path_edges = best_candidate['path_edges']
                
                # 4. Resources Execution / Deduction
                graph.nodes[best_node]['cpu_capacity'] -= req_cpu
                graph.nodes[best_node]['ram_capacity'] -= req_ram
                placements.append((best_node, vnf, req_cpu, req_ram))

                for u, v in best_path_edges:
                    graph[u][v]['bandwidth'] -= bw_demand
                
                if best_path_edges:
                    paths_used.append(best_path_edges)
                    
                total_delay += best_candidate['path_delay']
                prev_node = best_node
                placed = True
            
            # 5. Rollback on Failure
            if not placed:
                for p_node, p_vnf, p_cpu, p_ram in placements:
                    graph.nodes[p_node]['cpu_capacity'] += p_cpu
                    graph.nodes[p_node]['ram_capacity'] += p_ram
                
                for edges in paths_used:
                    for u, v in edges:
                        graph[u][v]['bandwidth'] += bw_demand
                        
                return False, [], [], 0, 0
                
        # 6. Return standard signature
        return True, placements, paths_used, total_delay, bw_demand