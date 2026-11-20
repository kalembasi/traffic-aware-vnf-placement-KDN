"""Paper figures describing the environment (needs data/external and data/telemetry/s0.csv.gz).

Usage: python -m scripts.make_figures   -> figures/*.png and figures/*.pdf
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.experiment import world_for

OUT = 'figures'
ENV = 'experiments/envs/s0.json'
SURFACE, INK, INK2, GRID, MUTED = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df', '#9a9893'
BLUE, VIOLET = '#2a78d6', '#6250d6'

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8, 'grid.linestyle': '-',
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.axisbelow': True,
    'font.size': 9, 'axes.titlesize': 10, 'axes.titleweight': 'bold', 'legend.frameon': False,
    'lines.linewidth': 2, 'lines.solid_capstyle': 'round', 'pdf.fonttype': 42,
})


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(OUT, f'{name}.{ext}'), dpi=200 if ext == 'png' else None)
    plt.close(fig)


def short(n):
    return n.replace('ng', '').replace('M5', '-M5')


def fig_topology(w):
    g = w.build_graph()
    xy = w.nodes_xy
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    for u, v in g.edges:
        ax.plot([xy[u][0], xy[v][0]], [xy[u][1], xy[v][1]], color=INK2, lw=1.2, zorder=1)
        if g[u][v]['delay'] < 2:
            continue
        ax.annotate(f"{g[u][v]['delay']:.1f}", ((xy[u][0] + xy[v][0]) / 2, (xy[u][1] + xy[v][1]) / 2),
                    fontsize=6, color=MUTED, ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.1', fc=SURFACE, ec='none'))
    for n in g.nodes:
        ax.scatter(*xy[n], s=36, color=INK, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.annotate(short(n), xy[n], xytext=(4, 4), textcoords='offset points', fontsize=7, color=INK2)
    ax.set_xlabel('longitude'); ax.set_ylabel('latitude'); ax.grid(False)
    ax.set_title('SNDlib Abilene (link delay in ms; links < 2 ms unlabelled)', loc='left')
    save(fig, 'fig_topology')


def fig_vnf_data(w):
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2))
    ax = axes[0]
    for (fam, d), mk, col in zip(sorted(w.families.items()), ('o', 's', '^'), (VIOLET, INK, MUTED)):
        ax.scatter(d['packets'] / 1e3, d['cpu'] / d['median_cpu'], s=9, marker=mk, color=col, alpha=0.55,
                   linewidths=0, label=f'{fam} (n={len(d["cpu"])})')
    ax.set_xlabel('packets per 20-s batch (×1000)'); ax.set_ylabel('CPU / family median')
    ax.set_title('KDN VNF measurements (Mestres et al.)', loc='left'); ax.legend(fontsize=7, loc='upper left')
    ax = axes[1]
    sched, _ = w.schedule('train', 1, 0.2, 10000)
    r = np.concatenate([x.request.hidden['r'] for x in sched])
    ax.hist(r, bins=40, color=VIOLET, edgecolor=SURFACE, linewidth=0.6)
    lo, hi = np.quantile(r, [0.05, 0.95])
    ax.axvspan(lo, hi, color=GRID, alpha=0.6, zorder=0)
    ax.text(hi + 0.02, ax.get_ylim()[1] * 0.85, f'90% of VNFs:\n{lo:.2f}–{hi:.2f}', fontsize=7.5, color=INK2)
    ax.set_xlabel('hidden relative load r of a placed VNF'); ax.set_ylabel('VNFs (1 run, λ=0.2)')
    ax.set_title('Relative load drawn by the simulator', loc='left'); ax.grid(axis='x', visible=False)
    save(fig, 'fig_vnf_data')


def fig_traffic(w):
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6), gridspec_kw={'width_ratios': [1.6, 1]})
    ax = axes[0]
    idx = w.split_idx['train'][:7 * 288]
    v = w.volume[idx] / w.volume[w.split_idx['train']].mean()
    ax.plot(np.arange(len(v)) / 288, v, color=BLUE, lw=1)
    ax.set_xlabel('days since 2004-03-01'); ax.set_ylabel('total volume / train mean')
    ax.set_title('Arrival-rate profile λ(t)/λ (first week)', loc='left')
    ax = axes[1]
    P = w.tm[w.split_idx['train']].sum(0)
    P = P / P.sum()
    im = ax.imshow(P * 100, cmap='Blues', vmin=0)
    names = [short(n) for n in w.tm_nodes]
    ax.set_xticks(range(len(names)), names, rotation=90, fontsize=6)
    ax.set_yticks(range(len(names)), names, fontsize=6)
    ax.set_xlabel('egress'); ax.set_ylabel('ingress'); ax.grid(False)
    ax.set_title('OD share of traffic (%)', loc='left')
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    save(fig, 'fig_traffic')


def fig_delay_fn():
    t = pd.read_csv('data/telemetry/s0.csv.gz', usecols=['rho_after'])
    hi = t.rho_after.quantile(0.99)
    rho = np.linspace(0, 0.95, 200)
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    ax.axvspan(0, hi, color=GRID, alpha=0.7, zorder=0)
    ax.text(hi / 2, 11.5, f'observed ρ of hosts after placement\n(99% ≤ {hi:.2f}, u0 = 0.6)', ha='center',
            fontsize=7.5, color=INK2)
    ax.plot(rho, 1 / (1 - rho), color=VIOLET, label='M/M/1-style  1/(1−ρ)  (main)')
    ax.plot(rho, 1 + 4 * rho, color=INK2, ls='--', label='linear  1+4ρ  (sensitivity S1)')
    ax.set_xlabel('node utilisation ρ (measured load / capacity)'); ax.set_ylabel('processing delay / (κ_n s_v)')
    ax.set_ylim(0, 21); ax.legend(fontsize=7.5, loc='upper left')
    ax.set_title('Hidden processing-delay function', loc='left')
    save(fig, 'fig_delay_fn')


if __name__ == '__main__':
    w = world_for(ENV)
    fig_topology(w); fig_vnf_data(w); fig_traffic(w); fig_delay_fn()
    print(f'figures written to {OUT}/')
