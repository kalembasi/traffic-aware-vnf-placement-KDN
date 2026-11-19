import random
import networkx as nx

ABILENE_NODES = ['ATLA', 'CHIC', 'DALL', 'DNVR', 'HSTN', 'KANS', 'LOSA', 'NYCG', 'SNVA', 'SEAT', 'WASH', 'INDI']
ABILENE_EDGES = [
    ('ATLA', 'WASH'), ('ATLA', 'HSTN'), ('ATLA', 'INDI'),
    ('CHIC', 'INDI'), ('CHIC', 'NYCG'),
    ('DALL', 'HSTN'), ('DALL', 'LOSA'), ('DALL', 'KANS'),
    ('DNVR', 'KANS'), ('DNVR', 'SEAT'), ('DNVR', 'SNVA'),
    ('LOSA', 'SNVA'), ('NYCG', 'WASH'), ('SEAT', 'SNVA'),
    ('CHIC', 'WASH')
]


def create_topology(config, rng=None):
    """Create the Abilene-like topology used in v1.

    Every node gets CPU/RAM capacity and every edge gets bandwidth and a propagation delay drawn
    uniformly from [min_delay, max_delay]. ``cpu_capacity``/``ram_capacity``/``bandwidth`` are the
    *free* amounts and change during simulation; ``*_max`` attributes keep the installed capacity.

    Args:
        config: full config dict (uses ``config['network']``).
        rng: ``random.Random``-like source for delays; defaults to the global ``random`` module
             (v1 behaviour: delays depend on the global seed).
    """
    rng = rng or random
    net_cfg = config['network']
    G = nx.Graph()
    for node in ABILENE_NODES:
        G.add_node(node,
                   cpu_capacity=net_cfg['node_cpu'], ram_capacity=net_cfg['node_ram'],
                   cpu_max=net_cfg['node_cpu'], ram_max=net_cfg['node_ram'])
    for u, v in ABILENE_EDGES:
        delay = rng.randint(net_cfg['min_delay'], net_cfg['max_delay'])
        G.add_edge(u, v, bandwidth=net_cfg['edge_bw'], bw_max=net_cfg['edge_bw'], delay=delay)
    return G


def visualize_topology(graph, output_path="topology.png"):
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(graph, seed=42)
    nx.draw(graph, pos, with_labels=True, node_color='lightblue',
            node_size=2000, font_size=10, font_weight='bold', edge_color='gray')
    plt.title("Network Topology")
    plt.savefig(output_path)
    plt.close()
