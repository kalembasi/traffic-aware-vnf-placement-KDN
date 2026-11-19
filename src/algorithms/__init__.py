"""Algorithm registry: experiment configs refer to algorithms by these names."""
from src.algorithms.greedy import GreedyPlacement
from src.algorithms.kdn import KDNPlacement
from src.algorithms.random import RandomPlacement
from src.algorithms.smart import SmartPlacement

REGISTRY = {
    'greedy': lambda md: GreedyPlacement(),
    'smart': lambda md: SmartPlacement(),
    'random': lambda md: RandomPlacement(),
    # v1 method
    'kdn': lambda md: KDNPlacement(md),
    # ablations sharing the KDN candidate generator
    'kdn-nogate': lambda md: KDNPlacement(md, gatekeeper=False),
    'cands-oracle': lambda md: KDNPlacement(md, gatekeeper=False, selector='oracle'),
    'cands-first': lambda md: KDNPlacement(md, gatekeeper=False, selector='first'),
    'cands-random': lambda md: KDNPlacement(md, gatekeeper=False, selector='random'),
}


def build_algorithm(name, models_dir='models'):
    if name not in REGISTRY:
        raise KeyError(f"unknown algorithm '{name}', choose from {sorted(REGISTRY)}")
    algo = REGISTRY[name](models_dir)
    algo.name = name
    return algo
