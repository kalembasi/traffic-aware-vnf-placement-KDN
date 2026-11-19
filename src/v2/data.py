"""Loaders for the public datasets used by v2 (see scripts/fetch_data.sh).

- SNDlib native network file -> nodes with coordinates, links with capacities
- Abilene 5-min traffic matrices (Zhang, via SNDlib) -> cached numpy array
- KDN VNF datasets (Mestres et al. 2017) -> per-family (packets, flows, cpu) samples
"""
import math
import os
import re

import numpy as np

_NODE = re.compile(r'^\s*(\S+)\s+\(\s*([-0-9.eE+]+)\s+([-0-9.eE+]+)\s*\)\s*$')
_LINK = re.compile(r'^\s*(\S+)\s+\(\s*(\S+)\s+(\S+)\s*\)\s+([0-9.eE+-]+)')
_DEMAND = re.compile(r'^\s*\S+\s+\(\s*(\S+)\s+(\S+)\s*\)\s+\d+\s+([0-9.eE+-]+)')


def _section(lines, name):
    out, inside = [], False
    for line in lines:
        if line.startswith(name + ' ('):
            inside = True
            continue
        if inside:
            if line.startswith(')'):
                break
            out.append(line)
    return out


def load_sndlib_network(path):
    """Returns (nodes: {name: (lon, lat)}, links: [(u, v, capacity_mbps)])."""
    lines = open(path).read().splitlines()
    nodes = {}
    for line in _section(lines, 'NODES'):
        m = _NODE.match(line)
        if m:
            nodes[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    links = []
    for line in _section(lines, 'LINKS'):
        m = _LINK.match(line)
        if m:
            links.append((m.group(2), m.group(3), float(m.group(4))))
    return nodes, links


def haversine_km(a, b):
    (lon1, lat1), (lon2, lat2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def load_traffic_matrices(tm_dir, cache_path):
    """Returns dict(times=array['YYYYMMDD-HHMM'], nodes=list, tm=float32[T, N, N]) (cached as .npz)."""
    if os.path.exists(cache_path):
        z = np.load(cache_path, allow_pickle=False)
        return {'times': z['times'], 'nodes': list(z['nodes']), 'tm': z['tm']}
    files = sorted(f for f in os.listdir(tm_dir) if f.startswith('demandMatrix'))
    nodes = None
    tms, times = [], []
    for f in files:
        rows = []
        for line in _section(open(os.path.join(tm_dir, f)).read().splitlines(), 'DEMANDS'):
            m = _DEMAND.match(line)
            if m:
                rows.append((m.group(1), m.group(2), float(m.group(3))))
        if nodes is None:
            nodes = sorted({a for a, _, _ in rows} | {b for _, b, _ in rows})
            idx = {n: i for i, n in enumerate(nodes)}
        M = np.zeros((len(nodes), len(nodes)), dtype=np.float32)
        for a, b, v in rows:
            M[idx[a], idx[b]] = v
        tms.append(M)
        times.append(f.rsplit('-', 2)[-2] + '-' + f.rsplit('-', 1)[-1][:4])
    os.makedirs(os.path.dirname(cache_path) or '.', exist_ok=True)
    out = {'times': np.array(times), 'nodes': np.array(nodes), 'tm': np.stack(tms)}
    np.savez_compressed(cache_path, **out)
    out['nodes'] = list(nodes)
    return out


VNF_FAMILIES = {'Snort': 'snort/Snort', 'Firewall': 'firewall/Firewall', 'OVS': 'ovs/OVS'}


def load_vnf_family(base_dir, family):
    """Pairs feature batches with measured CPU following the dataset's own Matlab loader file order.

    Returns dict(packets, flows, cpu) arrays. Pairs whose files are missing are skipped (2 in OVS).
    """
    d = os.path.join(base_dir, VNF_FAMILIES[family])
    mfile = [f for f in os.listdir(d) if f.endswith('.m')][0]
    src = open(os.path.join(d, mfile)).read()
    feats = re.findall(r"load\('([^']+\.csv)'\)", src)
    cpus = re.findall(r"load\('([^']+\.txt)'\)", src)
    P, F, C = [], [], []
    for fa, ca in zip(feats, cpus):
        fp, cp = os.path.join(d, 'features', fa), os.path.join(d, 'cpu', ca)
        if not (os.path.exists(fp) and os.path.exists(cp)):
            continue
        hdr = open(fp).readline().lstrip('%').split()
        X = np.loadtxt(fp, comments='%', ndmin=2)
        y = np.loadtxt(cp, ndmin=1)
        n = min(len(X), len(y))
        P.append(X[:n, hdr.index('numPackets')]); F.append(X[:n, hdr.index('flows')]); C.append(y[:n])
    return {'packets': np.concatenate(P), 'flows': np.concatenate(F), 'cpu': np.concatenate(C)}
