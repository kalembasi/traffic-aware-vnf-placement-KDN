import networkx as nx
import xgboost as xgb
import pickle
import random
from src.algorithms.base import BasePlacement
from src.sfc import VNF_REQUIREMENTS, SFC_CATALOG, SFC_BANDWIDTH

class XGBoostPlacement(BasePlacement):
    def __init__(self):
        # 1. Load trained XGBoost weights and the categorical encoder mapping
        self.model = xgb.XGBRegressor()
        self.model.load_model('models/kdn_xgboost.json')
        
        with open('models/label_encoder.pkl', 'rb') as f:
            self.encoder = pickle.load(f)

    def _get_network_state(self, graph):
        # Default node constraint
        max_cpu = 100.0  
        active_nodes = sum(1 for n in graph.nodes() if graph.nodes[n]['cpu_capacity'] < max_cpu)
        free_cpu = sum(graph.nodes[n]['cpu_capacity'] for n in graph.nodes())
        free_bw = sum(graph[u][v]['bandwidth'] for u, v in graph.edges())
        return active_nodes, free_cpu, free_bw

    def place_sfc(self, graph, sfc_name):
        chain = SFC_CATALOG[sfc_name]
        bw_demand = SFC_BANDWIDTH[sfc_name]
        
        # Capture strictly current graph baseline
        active_nodes, free_cpu, free_bw = self._get_network_state(graph)
        sfc_type_encoded = self.encoder.transform([sfc_name])[0]
        
        # --- Candidate Generation ---
        # A full exact-hardware permutation search is O(N!), we map greedy-like candidates as proposals.
        valid_candidates = []
        for _ in range(5):  # Sample 5 different routing strategies locally 
            temp_graph = graph.copy()
            placements, paths_used, total_delay = [], [], 0
            prev_node = None
            placed_chain = True
            
            for vnf in chain:
                req_cpu = VNF_REQUIREMENTS[vnf]['cpu']
                req_ram = VNF_REQUIREMENTS[vnf]['ram']
                placed = False
                
                # Shuffle node traversal to create diverse candidates
                nodes = list(temp_graph.nodes())
                random.shuffle(nodes)
                
                for node in nodes:
                    if temp_graph.nodes[node]['cpu_capacity'] >= req_cpu and temp_graph.nodes[node]['ram_capacity'] >= req_ram:
                        path_edges, path_delay, can_route = [], 0, True
                        
                        if prev_node is not None and prev_node != node:
                            try:
                                path_nodes = nx.shortest_path(temp_graph, source=prev_node, target=node)
                                for i in range(len(path_nodes) - 1):
                                    u, v = path_nodes[i], path_nodes[i+1]
                                    if temp_graph[u][v]['bandwidth'] < bw_demand:
                                        can_route = False
                                        break
                                if can_route:
                                    for i in range(len(path_nodes) - 1):
                                        u, v = path_nodes[i], path_nodes[i+1]
                                        path_edges.append((u, v))
                                        path_delay += temp_graph[u][v]['delay']
                            except nx.NetworkXNoPath:
                                can_route = False

                        if can_route:
                            # Tentative execution on candidate
                            temp_graph.nodes[node]['cpu_capacity'] -= req_cpu
                            temp_graph.nodes[node]['ram_capacity'] -= req_ram
                            for u, v in path_edges:
                                temp_graph[u][v]['bandwidth'] -= bw_demand
                                
                            placements.append((node, vnf, req_cpu, req_ram))
                            if path_edges: paths_used.append(path_edges)
                            total_delay += path_delay
                            prev_node = node
                            placed = True
                            break
                            
                if not placed:
                    placed_chain = False
                    break
            
            if placed_chain:
                unique_n = len(set([p[0] for p in placements]))
                valid_candidates.append({
                    'action_num_unique_nodes': unique_n,
                    'placements': placements,
                    'paths_used': paths_used,
                    'total_delay': total_delay
                })

        # --- ML Selection ---
        if not valid_candidates:
            return False, [], [], 0, 0

        best_candidate = None
        best_pred_latency = float('inf')
        
        # Score each valid proposed chain topology with the ML model
        for c in valid_candidates:
            # Recreate exact ML Array dimensions
            features = [[sfc_type_encoded, active_nodes, free_cpu, free_bw, c['action_num_unique_nodes']]]
            pred_penalty = self.model.predict(features)[0]
            
            # Agent Policy: Pick the action with the lowest expected Latency
            if pred_penalty < best_pred_latency:
                best_pred_latency = pred_penalty
                best_candidate = c
                
        # --- Main Execution ---
        for node, vnf, req_cpu, req_ram in best_candidate['placements']:
            graph.nodes[node]['cpu_capacity'] -= req_cpu
            graph.nodes[node]['ram_capacity'] -= req_ram
        for edges in best_candidate['paths_used']:
            for u, v in edges:
                graph[u][v]['bandwidth'] -= bw_demand

        return True, best_candidate['placements'], best_candidate['paths_used'], best_candidate['total_delay'], bw_demand