import networkx as nx
import random
import matplotlib.pyplot as plt

def create_topology(config):
    G = nx.Graph()
    nodes = ['ATLA', 'CHIC', 'DALL', 'DNVR', 'HSTN', 'KANS', 'LOSA', 'NYCG', 'SNVA', 'SEAT', 'WASH', 'INDI']
    edges = [
        ('ATLA', 'WASH'), ('ATLA', 'HSTN'), ('ATLA', 'INDI'),
        ('CHIC', 'INDI'), ('CHIC', 'NYCG'),
        ('DALL', 'HSTN'), ('DALL', 'LOSA'), ('DALL', 'KANS'),
        ('DNVR', 'KANS'), ('DNVR', 'SEAT'), ('DNVR', 'SNVA'),
        ('LOSA', 'SNVA'), ('NYCG', 'WASH'), ('SEAT', 'SNVA'),
        ('CHIC', 'WASH')
    ]
    
    net_cfg = config['network']
    
    for node in nodes:
        G.add_node(node, cpu_capacity=net_cfg['node_cpu'], ram_capacity=net_cfg['node_ram'])
        
    for u, v in edges:
        delay = random.randint(net_cfg['min_delay'], net_cfg['max_delay'])
        G.add_edge(u, v, bandwidth=net_cfg['edge_bw'], delay=delay)
        
    return G

def visualize_topology(graph, output_path="topology.png"):
    plt.figure(figsize=(10, 8))
    # Using spring layout with a fixed seed for consistent node placement
    pos = nx.spring_layout(graph, seed=42)
    nx.draw(graph, pos, with_labels=True, node_color='lightblue', 
            node_size=2000, font_size=10, font_weight='bold', edge_color='gray')
    plt.title("Network Topology")
    plt.savefig(output_path)
    plt.close()
    print(f"Topology successfully saved to {output_path}")
