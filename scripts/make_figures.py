"""Paper/report figures generated only from committed result tables (results/**).

Usage: python -m scripts.make_figures   -> figures/*.png (report) and figures/*.pdf (paper)

Colour = entity, fixed across all figures: KDN blue, smart orange, tuned smart-load aqua,
everything else neutral gray (validated default palette, first three slots).
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

OUT = 'figures'
SURFACE, INK, INK2, GRID, MUTED = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df', '#9a9893'
BLUE, ORANGE, AQUA, VIOLET = '#2a78d6', '#eb6834', '#1baf7a', '#6250d6'
ENTITY = {'kdn': BLUE, 'kdn2': BLUE, 'smart': ORANGE, 'smart-load': AQUA}
LABEL = {'kdn': 'KDN (v1)', 'kdn2': 'KDN-v2', 'smart': 'Smart', 'smart-load': 'Smart-load (tuned α)',
         'greedy': 'Greedy', 'random': 'Random', 'oracle': 'Oracle', 'cands-oracle': 'Candidates + oracle',
         'cands-first': 'Co-location candidate only', 'cands-random': 'Candidates + random pick',
         'kdn-nogate': 'KDN (v1) w/o gatekeeper', 'kdn2-gate': 'KDN-v2 + gatekeeper',
         'cands-prop': 'Candidates + propagation only', 'smart-nowake': 'Smart w/o wake-up penalty',
         'smart-nowake-load': 'Smart w/o wake-up + α'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8, 'grid.linestyle': '-',
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.axisbelow': True,
    'font.size': 9, 'axes.titlesize': 10, 'axes.titleweight': 'bold', 'legend.frameon': False,
    'lines.linewidth': 2, 'lines.solid_capstyle': 'round', 'pdf.fonttype': 42,
})


def color(a):
    return ENTITY.get(a, MUTED)


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(OUT, f'{name}.{ext}'), dpi=200 if ext == 'png' else None)
    plt.close(fig)


def paired_ci(runs, a, b, metric):
    rows = []
    for lam, g in runs.groupby('lambda'):
        p = g.pivot(index='seed', columns='algorithm', values=metric)
        d = (p[a] - p[b]).dropna()
        h = stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))
        rows.append((lam, d.mean(), h))
    return pd.DataFrame(rows, columns=['lambda', 'mean', 'ci'])


# --- 1. topology: v1 hand-made vs SNDlib Abilene ---------------------------------------------
def fig_topology():
    from src.topology import ABILENE_EDGES
    from src.v2.data import load_sndlib_network
    nodes, links = load_sndlib_network('data/external/sndlib/abilene.txt')
    m = {'ATLA': 'ATLAng', 'CHIC': 'CHINng', 'DNVR': 'DNVRng', 'HSTN': 'HSTNng', 'INDI': 'IPLSng', 'KANS': 'KSCYng',
         'LOSA': 'LOSAng', 'NYCG': 'NYCMng', 'SNVA': 'SNVAng', 'SEAT': 'STTLng', 'WASH': 'WASHng'}
    xy = dict(nodes); xy['DALL'] = (-96.80, 32.78)
    v1 = {frozenset((m.get(u, u), m.get(v, v))) for u, v in ABILENE_EDGES}
    v2 = {frozenset((u, v)) for u, v, _ in links}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, edges, other, title in ((axes[0], v1, v2, 'v1: hand-made "Abilene-like" (random delays)'),
                                    (axes[1], v2, v1, 'v2: SNDlib Abilene (geographic delays)')):
        for e in edges:
            u, v = tuple(e)
            ax.plot([xy[u][0], xy[v][0]], [xy[u][1], xy[v][1]], color=INK2 if e in other else ORANGE,
                    lw=1.2 if e in other else 2.2, zorder=1)
        used = {n for e in edges for n in e}
        for n in used:
            ax.scatter(*xy[n], s=36, color=INK, edgecolor=SURFACE, linewidth=1.5, zorder=3)
            ax.annotate(n.replace('ng', '').replace('M5', '-M5'), xy[n], xytext=(4, 4), textcoords='offset points',
                        fontsize=7, color=INK2)
        ax.set_title(title, loc='left'); ax.set_xlabel('longitude'); ax.grid(False)
    axes[0].set_ylabel('latitude')
    axes[1].plot([], [], color=ORANGE, lw=2.2, label='link only in this topology')
    axes[1].plot([], [], color=INK2, lw=1.2, label='link in both')
    axes[1].legend(loc='lower left', fontsize=7)
    save(fig, 'fig_topology')


# --- 2. v1 ablation at lambda = 0.2 ---------------------------------------------------------
def fig_v1_ablation():
    s = pd.read_csv('results/v1_sweep/summary.csv')
    s = s[s['lambda'] == 0.2].sort_values('lat_mean_mean')
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    y = np.arange(len(s))
    ax.barh(y, s.lat_mean_mean, height=0.55, color=[color(a) for a in s.algorithm], xerr=s.lat_mean_ci95,
            error_kw=dict(ecolor=INK2, lw=1, capsize=2))
    for yi, (_, r) in zip(y, s.iterrows()):
        ax.text(r.lat_mean_mean + r.lat_mean_ci95 + 0.6, yi, f'{r.lat_mean_mean:.1f}', va='center', fontsize=8, color=INK2)
    ax.set_yticks(y, [LABEL.get(a, a) for a in s.algorithm]); ax.invert_yaxis()
    ax.set_xlabel('mean latency of accepted SFCs (ms), 95% CI, 30 seeds'); ax.grid(axis='y', visible=False)
    ax.set_title('v1 (λ = 0.2): selection is not the bottleneck', loc='left')
    save(fig, 'fig_v1_ablation')


# --- 3. v1 gatekeeper: count vs CPU-weighted acceptance ---------------------------------------
def fig_v1_gate():
    r = pd.read_csv('results/v1_sweep/runs.csv')
    lam_pos = {l: i for i, l in enumerate(sorted(r['lambda'].unique()))}
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    for metric, lab, mk, col, off in (('acceptance', 'request-count acceptance', 'o', INK2, -0.08),
                                      ('cpu_acceptance', 'CPU-weighted acceptance', 's', VIOLET, 0.08)):
        d = paired_ci(r, 'kdn', 'kdn-nogate', metric)
        x = np.array([lam_pos[l] for l in d['lambda']]) + off
        ax.errorbar(x, d['mean'], yerr=d['ci'], fmt=mk, color=col, ms=6, lw=1.2, capsize=2, label=lab,
                    mfc=col if mk == 's' else SURFACE, mew=1.5)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(range(len(lam_pos)), [f'{l:g}' for l in lam_pos]); ax.set_xlabel('arrival rate λ')
    ax.set_ylabel('gatekeeper on − off (pp)'); ax.legend(loc='lower left', fontsize=8)
    ax.set_title('v1 gatekeeper: a gain only when counting requests', loc='left')
    save(fig, 'fig_v1_gate')


# --- 4. v2 latency vs load -----------------------------------------------------------------
def fig_v2_latency():
    s = pd.read_csv('results/v2/main/summary.csv')
    lams = sorted(s['lambda'].unique()); x = np.arange(len(lams))
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    for a, ls in (('greedy', '--'), ('smart', '-'), ('smart-load', '-'), ('kdn2', '-')):
        g = s[s.algorithm == a].set_index('lambda').loc[lams]
        ax.fill_between(x, g.lat_mean_mean - g.lat_mean_ci95, g.lat_mean_mean + g.lat_mean_ci95, color=color(a), alpha=0.15, lw=0)
        ax.plot(x, g.lat_mean_mean, ls, color=color(a), marker='o', ms=5, mec=SURFACE, mew=1.5, label=LABEL[a])
    ax.set_xticks(x, [f'{l:g}' for l in lams]); ax.set_xlabel('mean arrival rate λ (test split, Jul–Sep 2004)')
    ax.set_ylabel('mean setup latency (ms)')
    ax.legend(loc='upper left', fontsize=8, ncol=2)
    ax.set_title('v2: KDN-v2 wins at light/moderate load, loses at heavy load', loc='left')
    save(fig, 'fig_v2_latency')


# --- 5. v2 paired differences ----------------------------------------------------------------
def fig_v2_diff():
    main = pd.read_csv('results/v2/main/runs.csv')
    expl = pd.read_csv('results/v2/main_exploratory/runs.csv')
    r = pd.concat([main, expl], ignore_index=True)
    lams = sorted(r['lambda'].unique()); pos = {l: i for i, l in enumerate(lams)}
    fig, ax = plt.subplots(figsize=(6.0, 3.3))
    for b, off, mk in (('smart', -0.15, 'o'), ('smart-load', 0.0, 'o'), ('cands-prop', 0.15, 'D')):
        d = paired_ci(r, 'kdn2', b, 'lat_mean')
        ax.errorbar(np.array([pos[l] for l in d['lambda']]) + off, d['mean'], yerr=d['ci'], fmt=mk, ms=6,
                    color=color(b) if b != 'cands-prop' else INK2, mec=SURFACE, mew=1, lw=1.2, capsize=2,
                    label=f'KDN-v2 − {LABEL[b]}' + (' (exploratory)' if b == 'cands-prop' else ''))
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(range(len(lams)), [f'{l:g}' for l in lams]); ax.set_xlabel('arrival rate λ')
    ax.set_ylabel('paired latency difference (ms)\n< 0: KDN-v2 faster'); ax.legend(loc='lower right', fontsize=7.5)
    ax.set_title('Where KDN-v2 helps, and how much of it is learning', loc='left')
    save(fig, 'fig_v2_diff')


# --- 6. latency decomposition ----------------------------------------------------------------
def fig_v2_decomp():
    d = pd.read_csv('results/v2/main/latency_decomposition.csv')
    algos = ['smart', 'smart-nowake', 'cands-prop', 'kdn2', 'oracle']
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), sharey=True)
    for ax, lam in zip(axes, (0.02, 0.4)):
        g = d[d['lambda'] == lam].set_index('algorithm').loc[algos]
        x = np.arange(len(algos))
        ax.bar(x, g.prop_mean, width=0.55, color='#c9c7c1', label='propagation (known)')
        ax.bar(x, g.proc_mean, width=0.55, bottom=g.prop_mean + 0.25, color=VIOLET, label='processing (hidden, learned)')
        for xi, (p, q) in zip(x, zip(g.prop_mean, g.proc_mean)):
            ax.text(xi, p + q + 0.6, f'{p + q:.1f}', ha='center', fontsize=7.5, color=INK2)
        ax.set_xticks(x, [LABEL[a].replace(' w/o wake-up penalty', '\nno wake-up').replace('Candidates + propagation only', 'Cands +\nprop. only') for a in algos], fontsize=7)
        ax.set_title(f'λ = {lam:g}', loc='left'); ax.grid(axis='x', visible=False)
    axes[0].set_ylabel('mean latency (ms)'); axes[0].legend(loc='upper right', fontsize=7)
    save(fig, 'fig_v2_decomp')


# --- 7. which candidate KDN-v2 picks ---------------------------------------------------------
def fig_v2_generators():
    g = pd.read_csv('results/v2/main/kdn2_generator_choice.csv', index_col=0)
    groups = {'Smart (α = 0)': ['smart-a0'], 'Smart + load (α = 2, 10, 50)': ['smart-a2', 'smart-a10', 'smart-a50'],
              'Co-location / least-utilised': ['colocate', 'least-util'], 'Random first-fit': ['shuffled']}
    cols = [ORANGE, AQUA, VIOLET, '#c9c7c1']
    lams = list(g.columns); x = np.arange(len(lams)); bottom = np.zeros(len(lams))
    fig, ax = plt.subplots(figsize=(5.8, 3.0))
    for (name, members), c in zip(groups.items(), cols):
        v = g.reindex(members).fillna(0).sum().values
        ax.bar(x, v - 0.006, bottom=bottom, width=0.5, color=c, label=name)
        bottom += v
    ax.set_xticks(x, lams); ax.set_xlabel('arrival rate λ'); ax.set_ylabel('share of accepted SFCs')
    ax.set_ylim(0, 1); ax.grid(axis='x', visible=False); ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=7.5)
    ax.set_title('Candidate generator chosen by KDN-v2', loc='left')
    save(fig, 'fig_v2_generators')


# --- 8. latency vs acceptance trade-off (paired differences to KDN-v2) ------------------------
def fig_v2_tradeoff(lam=0.1):
    r = pd.concat([pd.read_csv('results/v2/main/runs.csv'), pd.read_csv('results/v2/main_exploratory/runs.csv')],
                  ignore_index=True)
    r = r[r['lambda'] == lam]
    others = ['smart', 'smart-load', 'smart-nowake', 'smart-nowake-load', 'cands-prop', 'oracle', 'kdn2-gate']
    offs = {'smart': (6, 4), 'smart-load': (6, -10), 'smart-nowake': (6, 4), 'smart-nowake-load': (6, -10),
            'cands-prop': (-6, 6), 'oracle': (6, 4), 'kdn2-gate': (6, -10)}
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    ax.axhline(0, color=INK2, lw=1); ax.axvline(0, color=INK2, lw=1)
    ax.scatter([0], [0], s=60, color=BLUE, edgecolor=SURFACE, linewidth=1.5, zorder=4)
    ax.annotate('KDN-v2 (reference)', (0, 0), xytext=(6, -12), textcoords='offset points', fontsize=7.5, color=INK2)
    for a in others:
        dl = paired_ci(r, a, 'kdn2', 'lat_mean').iloc[0]
        da = paired_ci(r, a, 'kdn2', 'cpu_acceptance').iloc[0]
        ax.errorbar(da['mean'], dl['mean'], xerr=da['ci'], yerr=dl['ci'], fmt='o', ms=7, color=color(a),
                    mec=SURFACE, mew=1.5, lw=1, capsize=0, zorder=3)
        ha = 'right' if offs[a][0] < 0 else 'left'
        ax.annotate(LABEL[a] + (' *' if a in ('smart-nowake', 'smart-nowake-load', 'cands-prop') else ''),
                    (da['mean'], dl['mean']), xytext=offs[a], textcoords='offset points', fontsize=7, color=INK2, ha=ha)
    ax.set_xlabel('Δ CPU-weighted acceptance vs KDN-v2 (pp)   → admits more')
    ax.set_ylabel('Δ mean latency vs KDN-v2 (ms)   ↓ faster')
    ax.set_title(f'Latency vs. admitted load at λ = {lam:g} (paired, 95% CI)', loc='left')
    ax.text(1.0, -0.2, '* exploratory (not pre-registered)', transform=ax.transAxes, ha='right', fontsize=7, color=INK2)
    save(fig, 'fig_v2_tradeoff')


if __name__ == '__main__':
    for f in (fig_topology, fig_v1_ablation, fig_v1_gate, fig_v2_latency, fig_v2_diff, fig_v2_decomp,
              fig_v2_generators, fig_v2_tradeoff):
        f(); print('ok', f.__name__)
