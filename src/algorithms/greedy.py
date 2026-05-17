import networkx as nx
from src.algorithms.base import BasePlacement
from src.sfc import VNF_REQUIREMENTS, SFC_CATALOG, SFC_BANDWIDTH

class GreedyPlacement(BasePlacement):
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
            
            for node in graph.nodes():
                avail_cpu = graph.nodes[node]['cpu_capacity']
                avail_ram = graph.nodes[node]['ram_capacity']
                
                if avail_cpu >= req_cpu and avail_ram >= req_ram:
                    # If this is not the first VNF, check bandwidth
                    path_edges = []
                    path_delay = 0
                    can_route = True
                    
                    if prev_node is not None:
                        if prev_node != node:
                            try:
                                path_nodes = nx.shortest_path(graph, source=prev_node, target=node)
                                
                                # Check bandwidth along the path
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
                        # Deduct resources
                        graph.nodes[node]['cpu_capacity'] -= req_cpu
                        graph.nodes[node]['ram_capacity'] -= req_ram
                        placements.append((node, vnf, req_cpu, req_ram))
                        
                        # Deduct bandwidth
                        for u, v in path_edges:
                            graph[u][v]['bandwidth'] -= bw_demand
                        
                        if path_edges:
                            paths_used.append(path_edges)
                        total_delay += path_delay
                        
                        prev_node = node
                        placed = True
                        break
                    
            if not placed:
                # Rollback CPU/RAM
                for p_node, p_vnf, p_cpu, p_ram in placements:
                    graph.nodes[p_node]['cpu_capacity'] += p_cpu
                    graph.nodes[p_node]['ram_capacity'] += p_ram
                
                # Rollback bandwidth
                for edges in paths_used:
                    for u, v in edges:
                        graph[u][v]['bandwidth'] += bw_demand
                        
                return False, [], [], 0, 0
                
        return True, placements, paths_used, total_delay, bw_demand
