"""Single source of truth for ML features (used by data generation, training and inference)."""
from src.sfc import SFC_CODES

STATE_FEATURES = [
    'sfc_type_encoded', 'network_active_nodes', 'network_free_cpu',
    'network_free_bw', 'net_max_node_utilization', 'net_bottleneck_bw',
]
ACTION_FEATURES = ['action_max_path_distance', 'action_num_unique_nodes']


def network_state(graph):
    """Aggregate network snapshot: (active_nodes, free_cpu, free_bw, max_node_util_%, bottleneck_bw)."""
    nodes = graph.nodes
    active = sum(1 for n in nodes if nodes[n]['cpu_capacity'] < nodes[n]['cpu_max'])
    free_cpu = sum(nodes[n]['cpu_capacity'] for n in nodes)
    free_bw = sum(graph[u][v]['bandwidth'] for u, v in graph.edges())
    max_util = max(((nodes[n]['cpu_max'] - nodes[n]['cpu_capacity']) / nodes[n]['cpu_max']) * 100
                   for n in nodes) if len(nodes) else 0
    bottleneck = min(graph[u][v]['bandwidth'] for u, v in graph.edges()) if graph.number_of_edges() else 0
    return active, free_cpu, free_bw, max_util, bottleneck


def state_vector(graph, sfc_type):
    return [SFC_CODES[sfc_type], *network_state(graph)]


def action_features(res):
    """(max hop length of any inter-VNF segment, number of distinct hosts) of a placement."""
    max_path = max(len(p) for p in res.paths) if res.paths else 0
    return [max_path, len(set(res.nodes))]
