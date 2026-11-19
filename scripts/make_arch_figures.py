"""Figures explaining the data and the hidden VNF model (needs data/external, see scripts/fetch_data.sh).

Usage: python -m scripts.make_arch_figures  -> figures/arch_*.png|pdf
"""
import numpy as np
import pandas as pd

from scripts.make_figures import BLUE, GRID, INK, INK2, MUTED, SURFACE, VIOLET, plt, save
from src.v2.experiment import world_for

ENV = 'experiments/v2/env_main.json'


def fig_vnf_data(w):
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2))
    ax = axes[0]
    for (fam, d), mk, col in zip(w.families.items(), ('o', 's', '^'), (VIOLET, INK, MUTED)):
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
    ax.set_title('What the simulator actually draws', loc='left'); ax.grid(axis='x', visible=False)
    save(fig, 'arch_vnf_data')


def fig_traffic(w):
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6), gridspec_kw={'width_ratios': [1.6, 1]})
    ax = axes[0]
    idx = w.split_idx['train'][:7 * 288]
    v = w.volume[idx] / w.volume[w.split_idx['train']].mean()
    ax.plot(np.arange(len(v)) / 288, v, color=BLUE, lw=1)
    ax.set_xlabel('days since 2004-03-01'); ax.set_ylabel('total volume / train mean')
    ax.set_title('Arrival-rate profile λ(t)/λ (first week)', loc='left')
    ax = axes[1]
    P = w.tm[w.split_idx['train']].sum(0); P = P / P.sum()
    im = ax.imshow(P * 100, cmap='Blues', vmin=0)
    names = [n.replace('ng', '').replace('M5', '-M5') for n in w.tm_nodes]
    ax.set_xticks(range(len(names)), names, rotation=90, fontsize=6); ax.set_yticks(range(len(names)), names, fontsize=6)
    ax.set_xlabel('egress'); ax.set_ylabel('ingress'); ax.grid(False)
    ax.set_title('OD share of traffic (%)', loc='left')
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    save(fig, 'arch_traffic')


def fig_delay_fn():
    t = pd.read_csv('data/v2/main/telemetry.csv.gz')
    a = t[t.accepted == 1]
    rho = np.linspace(0, 0.95, 200)
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    lo, hi = a['c_rho_max_hosts'].quantile([0.01, 0.99])
    ax.axvspan(0, hi, color=GRID, alpha=0.7, zorder=0)
    ax.text(hi / 2, 11.5, f'observed ρ of chosen hosts\n(99% ≤ {hi:.2f}, u0 = 0.6)', ha='center', fontsize=7.5, color=INK2)
    ax.plot(rho, 1 / (1 - rho), color=VIOLET, label='M/M/1-style  1/(1−ρ)  (main)')
    ax.plot(rho, 1 + 4 * rho, color=INK2, ls='--', label='linear  1+4ρ  (sensitivity S2)')
    ax.set_xlabel('node utilisation ρ (measured load / capacity)'); ax.set_ylabel('processing delay / s_v')
    ax.set_ylim(0, 21); ax.legend(fontsize=7.5, loc='upper left')
    ax.set_title('Hidden processing-delay function', loc='left')
    save(fig, 'arch_delay_fn')


if __name__ == '__main__':
    w = world_for(ENV)
    fig_vnf_data(w); fig_traffic(w); fig_delay_fn()
    print('ok')
