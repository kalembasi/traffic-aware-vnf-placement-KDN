"""Per-VNF telemetry features of the KDN model (protocol section 3). Only observable quantities are used."""
import numpy as np
import pandas as pd

from src.sfc import VNF_REQUIREMENTS

VNF_ORDER = sorted(VNF_REQUIREMENTS)
N_NODES = 12                      # SNDlib Abilene
VNF_RAW = ['vnf_idx', 'node_idx', 'rho_before', 'cpu_res_host', 'n_vnf_host', 'packets', 'flows', 'net_rho']
VNF_FEATURES = ([f'vnf_{v}' for v in VNF_ORDER] + [f'node_{i}' for i in range(N_NODES)] +
                ['rho_before', 'cpu_res_host', 'n_vnf_host', 'packets', 'flows', 'net_rho'])


def rho(graph, n):
    """Measured utilisation of node n (telemetry)."""
    return graph.nodes[n]['load'] / graph.nodes[n]['cpu_max']


def net_rho(graph):
    """Network-wide mean measured utilisation."""
    return sum(rho(graph, n) for n in graph.nodes) / graph.number_of_nodes()


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


def vnf_rows(graph, req, res, network_rho=None):
    """One raw feature dict per placed VNF, observable before the placement is committed."""
    network_rho = net_rho(graph) if network_rho is None else network_rho
    hosts, idx = host_reservations(res), _node_index(graph)
    return [{'vnf_idx': VNF_ORDER.index(vnf), 'node_idx': idx[node], 'rho_before': rho(graph, node),
             'cpu_res_host': hosts[node][1], 'n_vnf_host': hosts[node][0], 'packets': req.features['packets'],
             'flows': req.features['flows'], 'net_rho': network_rho}
            for node, vnf, _, _ in res.placements]


def vnf_matrix(rows):
    """Raw rows (list of dicts or a DataFrame with VNF_RAW columns) -> model matrix (VNF_FEATURES order)."""
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows, columns=VNF_RAW)
    n = len(df)
    X = np.zeros((n, len(VNF_FEATURES)))
    X[np.arange(n), df['vnf_idx'].to_numpy(int)] = 1.0
    X[np.arange(n), len(VNF_ORDER) + df['node_idx'].to_numpy(int)] = 1.0
    X[:, len(VNF_ORDER) + N_NODES:] = df[['rho_before', 'cpu_res_host', 'n_vnf_host', 'packets', 'flows',
                                          'net_rho']].to_numpy(float)
    return X
