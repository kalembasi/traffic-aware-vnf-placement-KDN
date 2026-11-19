"""Telemetry features for KDN-v2 (protocol section 3). Only observable quantities are used."""
from src.sfc import SFC_CODES, VNF_REQUIREMENTS

CANDIDATE_FEATURES = [
    'sfc_type_encoded', 'packets', 'flows', 'n_hosts', 'rho_max_hosts', 'rho_mean_hosts',
    'cpu_res_max_host', 'cpu_res_sum', 'vnf_max_host', 'net_rho_mean', 'net_free_cpu',
]
STATE_FEATURES = [
    'sfc_type_encoded', 'packets', 'flows', 'net_free_cpu', 'net_rho_mean', 'max_node_free_cpu', 'min_free_bw',
]


def rho(graph, n):
    """Measured utilisation of node n (telemetry)."""
    return graph.nodes[n]['load'] / graph.nodes[n]['cpu_max']


def _net(graph):
    nodes = graph.nodes
    return (sum(rho(graph, n) for n in nodes) / len(nodes), sum(nodes[n]['cpu_capacity'] for n in nodes))


def candidate_features(graph, req, res, net=None):
    net_rho, net_free = net or _net(graph)
    hosts = {}
    for node, vnf, cpu, _ in res.placements:
        h = hosts.setdefault(node, [0, 0.0])
        h[0] += 1
        h[1] += cpu
    rhos = [rho(graph, n) for n in hosts]
    return [SFC_CODES[req.sfc_type], req.features['packets'], req.features['flows'], len(hosts),
            max(rhos), sum(rhos) / len(rhos), max(h[1] for h in hosts.values()), sum(h[1] for h in hosts.values()),
            max(h[0] for h in hosts.values()), net_rho, net_free]


def state_features(graph, req):
    net_rho, net_free = _net(graph)
    return [SFC_CODES[req.sfc_type], req.features['packets'], req.features['flows'], net_free, net_rho,
            max(graph.nodes[n]['cpu_capacity'] for n in graph.nodes),
            min(graph[u][v]['bandwidth'] for u, v in graph.edges)]
