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


# --- v3: per-VNF features (v3 protocol section 3) ----------------------------------------------
VNF_ORDER = sorted(VNF_REQUIREMENTS)
N_NODES = 12                      # SNDlib Abilene
VNF_RAW = ['vnf_idx', 'node_idx', 'rho_before', 'cpu_res_host', 'n_vnf_host', 'packets', 'flows', 'net_rho']
VNF_FEATURES = ([f'vnf_{v}' for v in VNF_ORDER] + [f'node_{i}' for i in range(N_NODES)] +
                ['rho_before', 'cpu_res_host', 'n_vnf_host', 'packets', 'flows', 'net_rho'])


def host_reservations(res):
    """{host: [number of this SFC's VNFs, CPU this SFC reserves]}."""
    hosts = {}
    for node, _, cpu, _ in res.placements:
        h = hosts.setdefault(node, [0, 0.0])
        h[0] += 1
        h[1] += cpu
    return hosts


def _node_index(graph):
    idx = graph.graph.get('node_index')
    if idx is None:
        assert graph.number_of_nodes() == N_NODES
        idx = graph.graph['node_index'] = {n: i for i, n in enumerate(sorted(graph.nodes))}
    return idx


def vnf_rows(graph, req, res, net_rho=None):
    """One raw feature dict per placed VNF, observable before the placement is committed."""
    net_rho = _net(graph)[0] if net_rho is None else net_rho
    hosts, idx = host_reservations(res), _node_index(graph)
    return [{'vnf_idx': VNF_ORDER.index(vnf), 'node_idx': idx[node], 'rho_before': rho(graph, node),
             'cpu_res_host': hosts[node][1], 'n_vnf_host': hosts[node][0], 'packets': req.features['packets'],
             'flows': req.features['flows'], 'net_rho': net_rho}
            for node, vnf, _, _ in res.placements]


def vnf_matrix(rows):
    """Raw rows (list of dicts or a DataFrame with VNF_RAW columns) -> model matrix (VNF_FEATURES order)."""
    import numpy as np
    import pandas as pd
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows, columns=VNF_RAW)
    n = len(df)
    X = np.zeros((n, len(VNF_FEATURES)))
    X[np.arange(n), df['vnf_idx'].to_numpy(int)] = 1.0
    X[np.arange(n), len(VNF_ORDER) + df['node_idx'].to_numpy(int)] = 1.0
    X[:, len(VNF_ORDER) + N_NODES:] = df[['rho_before', 'cpu_res_host', 'n_vnf_host', 'packets', 'flows',
                                          'net_rho']].to_numpy(float)
    return X
