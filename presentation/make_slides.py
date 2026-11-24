"""Seminar slides (15 min). Every number is taken from results/ (same sources as manuscript/main.tex).

Usage (from the repo root):  .venv/bin/python -m presentation.make_slides
Output: presentation/slides.pptx (fonts: presentation/fonts, install them before opening).
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from scipy import stats
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from src.experiment import world_for

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
BG, INK, ACC, AUX = '#F9F9F6', '#111111', '#1F4E3D', '#7D807B'    # off-white, black, dark green, grey
SERIF, SANS = 'Source Serif 4 Semibold', 'Inter'
W, H = 13.333, 7.5
LM = 0.85                                   # left margin (in)


def mix(c, t, base=BG):
    """Blend colour c into base: t=1 -> c, t=0 -> base (tints only, no new hues)."""
    a = np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)])
    b = np.array([int(base[i:i + 2], 16) for i in (1, 3, 5)])
    v = np.round(b + (a - b) * t).astype(int)
    return '#%02X%02X%02X' % tuple(v)


def rgb(c):
    return RGBColor.from_string(c.lstrip('#'))


# ----------------------------------------------------------------------------------------------- pptx primitives
def no_shadow(shape):
    """Drop the theme style reference (it carries a drop shadow) so only explicit fill/line apply."""
    st = shape._element.find(qn('p:style'))
    if st is not None:
        shape._element.remove(st)


def text(s, x, y, w, h, paras, size=20, font=SANS, color=INK, bold=False, align='l', anchor='t',
         spacing=1.12, tracking=None, after=0):
    """paras: str | list of paragraphs; a paragraph is str or list of (text, overrides) runs."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE, 'b': MSO_ANCHOR.BOTTOM}[anchor]
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}[align]
        para.line_spacing = spacing
        para.space_after = Pt(after)
        runs = [(p, {})] if isinstance(p, str) else p
        for t, o in runs:
            r = para.add_run()
            r.text = t
            f = r.font
            f.name = o.get('font', font)
            f.size = Pt(o.get('size', size))
            f.bold = o.get('bold', bold)
            f.italic = False
            f.color.rgb = rgb(o.get('color', color))
            tr = o.get('tracking', tracking)
            if tr is not None:
                r._r.get_or_add_rPr().set('spc', str(int(tr * 100)))
    return tb


def line(s, x1, y1, x2, y2, color=AUX, w=0.75, dash=None, head=False):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    no_shadow(c)
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(w)
    ln = c.line._get_or_add_ln()
    if dash:
        d = ln.makeelement(qn('a:prstDash'), {'val': dash})
        ln.append(d)
    if head:
        ln.append(ln.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'sm', 'len': 'sm'}))
    return c


def dot(s, cx, cy, r, fill=INK, outline=None, ow=0.75):
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - r), Inches(cy - r), Inches(2 * r), Inches(2 * r))
    no_shadow(o)
    if fill is None:
        o.fill.background()
    else:
        o.fill.solid()
        o.fill.fore_color.rgb = rgb(fill)
    if outline is None:
        o.line.fill.background()
    else:
        o.line.color.rgb = rgb(outline)
        o.line.width = Pt(ow)
    return o


def rrect(s, x, y, w, h, fill, radius=0.18, outline=None):
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    no_shadow(r)
    r.adjustments[0] = min(0.5, radius / min(w, h))
    if fill is None:
        r.fill.background()
    else:
        r.fill.solid()
        r.fill.fore_color.rgb = rgb(fill)
    if outline is None:
        r.line.fill.background()
    else:
        r.line.color.rgb = rgb(outline)
        r.line.width = Pt(0.75)
    return r


class Deck:
    def __init__(self, n_main):
        self.p = Presentation()
        self.p.slide_width, self.p.slide_height = Inches(W), Inches(H)
        self.n_main = n_main
        self.i = 0

    def slide(self, kicker=None, title=None, notes='', footer=True, title_size=38):
        s = self.p.slides.add_slide(self.p.slide_layouts[6])
        bg = s.background.fill
        bg.solid()
        bg.fore_color.rgb = rgb(BG)
        self.i += 1
        if kicker:
            text(s, LM, 0.62, 9, 0.3, kicker.upper(), size=10.5, bold=True, color=AUX, tracking=2.2)
        if title:
            text(s, LM, 0.92, 11.6, 1.0, title, size=title_size, font=SERIF, spacing=1.0)
        if footer:
            self.footer(s)
        s.notes_slide.notes_text_frame.text = notes.strip()
        return s

    def footer(self, s):
        """Progress drawn as a path: one node per main slide, the current one in the accent colour."""
        y, x0, x1 = 7.0, LM, W - LM - 0.9
        main = self.i <= self.n_main
        line(s, x0, y, x1, y, color=mix(AUX, 0.55), w=0.5)
        n = self.n_main
        for k in range(1, n + 1):
            cx = x0 + (x1 - x0) * (k - 1) / (n - 1)
            if main and k == self.i:
                dot(s, cx, y, 0.055, fill=ACC)
            elif main and k < self.i:
                dot(s, cx, y, 0.03, fill=AUX)
            else:
                dot(s, cx, y, 0.03, fill=BG, outline=AUX, ow=0.5)
        label = f'{self.i:02d} / {n:02d}' if main else 'backup'
        text(s, x1 + 0.2, y - 0.11, W - LM - x1 - 0.2, 0.25, label, size=10, color=AUX, align='r', tracking=1)


# ------------------------------------------------------------------------------------------------------- data
WORLD = world_for('experiments/envs/s1.json')
CITY = {'ATLAM5': 'Atlanta', 'ATLAng': 'Atlanta', 'CHINng': 'Chicago', 'DNVRng': 'Denver', 'HSTNng': 'Houston',
        'IPLSng': 'Indianapolis', 'KSCYng': 'Kansas City', 'LOSAng': 'Los Angeles', 'NYCMng': 'New York',
        'SNVAng': 'Sunnyvale', 'STTLng': 'Seattle', 'WASHng': 'Washington'}
# label offset (dx, dy in inches) and alignment per node; ATLAM5 sits 0.7 ms from ATLAng and is left unlabelled
LABEL = {'STTLng': (0.16, -0.13, 'l'), 'SNVAng': (-0.16, -0.13, 'r'), 'LOSAng': (-0.16, -0.05, 'r'),
         'DNVRng': (0.0, -0.42, 'c'), 'KSCYng': (0.0, 0.14, 'c'), 'HSTNng': (0.0, 0.16, 'c'),
         'IPLSng': (0.16, -0.06, 'l'), 'CHINng': (-0.16, -0.30, 'r'), 'NYCMng': (0.1, -0.36, 'l'),
         'WASHng': (0.16, -0.06, 'l'), 'ATLAng': (-0.16, -0.10, 'r'), 'ATLAM5': None}


def project(x, y, w, h):
    """lon/lat -> slide inches inside the box (equirectangular at 38.5 N, aspect preserved, centred)."""
    xy = WORLD.nodes_xy
    k = np.cos(np.radians(38.5))
    px = {n: (lon * k, lat) for n, (lon, lat) in xy.items()}
    xs, ys = [p[0] for p in px.values()], [p[1] for p in px.values()]
    sx, sy = max(xs) - min(xs), max(ys) - min(ys)
    sc = min(w / sx, h / sy)
    ox, oy = x + (w - sx * sc) / 2, y + (h - sy * sc) / 2
    return {n: (ox + (p[0] - min(xs)) * sc, oy + (max(ys) - p[1]) * sc) for n, p in px.items()}


def draw_network(s, box, edge_color=AUX, edge_w=1.0, node_r=0.07, node_fill=INK, labels=True, delays=False,
                 path=(), sizes=None, label_size=12, label_color=INK):
    pos = project(*box)
    g = WORLD.build_graph()
    on_path = {frozenset(e) for e in zip(path, path[1:])}
    for u, v in g.edges:
        hot = frozenset((u, v)) in on_path
        line(s, *pos[u], *pos[v], color=ACC if hot else edge_color, w=2.25 if hot else edge_w)
        d = g[u][v]['delay']
        if delays and d >= 2:
            mx, my = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
            rrect(s, mx - 0.2, my - 0.11, 0.4, 0.22, BG, radius=0.08)
            text(s, mx - 0.25, my - 0.1, 0.5, 0.2, f'{d:.1f}', size=10.5, color=AUX, align='c', anchor='m')
    for n, (cx, cy) in pos.items():
        if sizes is not None:
            r, fill = sizes[n]
        else:
            r, fill = node_r, (ACC if n in path else node_fill)
        dot(s, cx, cy, r, fill=fill, outline=BG, ow=1.5)
        if labels and LABEL[n]:
            dx, dy, al = LABEL[n]
            bx = {'l': cx + dx, 'r': cx + dx - 2.0, 'c': cx - 1.0}[al]
            text(s, bx, cy + dy, 2.0, 0.3, CITY[n], size=label_size, color=label_color, align=al)
    return pos


# ----------------------------------------------------------------------------------------------- matplotlib
for f in os.listdir(os.path.join(HERE, 'fonts')):
    font_manager.fontManager.addfont(os.path.join(HERE, 'fonts', f))
plt.rcParams.update({
    'font.family': SANS, 'font.size': 13, 'text.color': INK, 'axes.labelcolor': AUX,
    'xtick.color': AUX, 'ytick.color': AUX, 'axes.edgecolor': mix(AUX, 0.6), 'axes.linewidth': 0.8,
    'figure.facecolor': BG, 'axes.facecolor': BG, 'savefig.facecolor': BG,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.spines.left': False,
    'xtick.major.size': 0, 'ytick.major.size': 0, 'xtick.major.pad': 8, 'ytick.major.pad': 8,
})


def chart_results(path):
    series = [('greedy', AUX, 1.4, (0, (4, 3))), ('smart', INK, 2.0, '-'), ('kdn-greedy', ACC, 3.0, '-')]
    panels = [('s0', 'Equal servers  (σ = 0)'), ('s1', 'Hidden slow servers  (σ = 1)')]
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5), sharey=True)
    for ax, (env, title) in zip(axes, panels):
        r = pd.read_csv(f'results/{env}/runs.csv')
        lams = sorted(r['lambda'].unique())
        x = np.arange(len(lams))
        ax.axvspan(-0.45, 1.5, color=mix(INK, 0.05), lw=0, zorder=0)
        ax.text(0.52, 47.2, 'normal load', ha='center', va='top', fontsize=11, color=AUX, fontweight='bold')
        for algo, col, lw, ls in series:
            m, h = [], []
            for lam in lams:
                d = r[(r['lambda'] == lam) & (r['algorithm'] == algo)]['lat_mean']
                m.append(d.mean())
                h.append(stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d)))
            m, h = np.array(m), np.array(h)
            ax.fill_between(x, m - h, m + h, color=mix(col, 0.18), lw=0, zorder=1)
            ax.plot(x, m, color=col, lw=lw, ls=ls, zorder=3, solid_capstyle='round')
            ax.scatter(x, m, s=42 if algo == 'kdn-greedy' else 26, color=col, edgecolor=BG, linewidth=1.8, zorder=4)
            ax.plot([], [], color=col, lw=lw, ls=ls, label=algo)
        ax.set_xticks(x, [f'{l:g}' for l in lams])
        ax.set_xlim(-0.45, len(lams) - 0.55)
        ax.set_ylim(0, 48)
        ax.set_xlabel('request rate λ   (light → heavy)', fontsize=12)
        ax.set_title(title, loc='left', fontsize=14, fontweight='bold', color=INK, pad=12)
        ax.grid(axis='y', color=mix(AUX, 0.3), lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('mean latency (ms)', fontsize=12)
    h, l = axes[0].get_legend_handles_labels()
    leg = fig.legend(h[::-1], l[::-1], loc='upper right', ncol=3, frameon=False, fontsize=12, handlelength=2.2,
                     bbox_to_anchor=(1.0, 1.0))
    for t, (_, col, _, _) in zip(leg.get_texts(), series[::-1]):
        t.set_color(col); t.set_fontweight('bold')
    fig.tight_layout(w_pad=3, rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=250)
    plt.close(fig)


def chart_queue(path):
    rho = np.linspace(0, 0.95, 200)
    fig, ax = plt.subplots(figsize=(5.1, 3.9))
    ax.plot(rho * 100, 1 / (1 - rho), color=ACC, lw=2.8, solid_capstyle='round')
    for r, lab in ((0.5, '×2'), (0.9, '×10')):
        ax.scatter([r * 100], [1 / (1 - r)], s=45, color=INK, zorder=4, edgecolor=BG, linewidth=1.5)
        ax.annotate(lab, (r * 100, 1 / (1 - r)), xytext=(-12, 8), textcoords='offset points', ha='right',
                    fontsize=14, fontweight='bold', color=INK)
    ax.set_xlabel('server load ρ (%)', fontsize=12)
    ax.set_ylabel('delay / base service time', fontsize=12)
    ax.set_xlim(0, 100); ax.set_ylim(0, 21)
    ax.grid(axis='y', color=mix(AUX, 0.3), lw=0.6); ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------------ slides
N_MAIN = 18
D = Deck(N_MAIN)
os.makedirs(BUILD, exist_ok=True)

# 1 ---------------------------------------------------------------------------------------------------- title
s = D.slide(footer=False, notes="""
Hello, I am Malik. My seminar topic is VNF placement with Knowledge-Defined Networking, advised by Tuğçe Bilen.
The question in the title is the whole talk: when does a learned latency model actually help?
(Paper verification: the IEEE-format PDF was shown just before this slide.)""")
text(s, LM, 0.75, 7, 0.3, 'SEMINAR · ISTANBUL TECHNICAL UNIVERSITY', size=10.5, bold=True, color=AUX, tracking=2.2)
text(s, LM, 1.35, 6.4, 3.0, [[('When does a learned latency model help ', {}),
                              ('VNF placement?', {'color': ACC})]], size=46, font=SERIF, spacing=0.98)
text(s, LM, 4.05, 5.8, 0.8, 'A Knowledge-Defined Networking study on the Abilene backbone', size=18, color=AUX)
line(s, LM, 5.25, LM + 0.6, 5.25, color=INK, w=1)
text(s, LM, 5.45, 6, 1.2, [[('Malik Kalembaşı', {'bold': True})], 'Informatics Institute  ·  Advisor: Tuğçe Bilen',
                           '25 November 2026'], size=14, spacing=1.3)
draw_network(s, (7.35, 1.2, 5.3, 4.6), edge_color=mix(AUX, 0.7), node_r=0.06, node_fill=AUX, labels=False,
             path=('SNVAng', 'DNVRng', 'KSCYng', 'IPLSng', 'CHINng', 'NYCMng'))

# 2 ---------------------------------------------------------------------------------------------- the problem
s = D.slide('The problem', 'Every service is a chain of VNFs.', notes="""
NFV replaces hardware boxes (NAT, firewall, IDS) with software VNFs on ordinary servers.
A customer service is a service function chain: traffic must pass these VNFs in order.
When a new chain is ordered, the orchestrator picks a server for every VNF.
Latency of the chain = propagation delay of the path + processing delay at each VNF.""")
chain = ['ingress', 'NAT', 'Firewall', 'SBC', 'IDS', 'egress']
cy, xs = 2.95, np.linspace(LM + 0.3, W - LM - 0.3, len(chain))
line(s, xs[0], cy, xs[-1], cy, color=INK, w=1.25)
servers_y = 4.95
sx = np.linspace(LM + 1.2, W - LM - 1.2, 12)
pick = 7
for k, (x, name) in enumerate(zip(xs, chain)):
    end = k in (0, len(chain) - 1)
    dot(s, x, cy, 0.09 if end else 0.17, fill=BG if end else INK, outline=INK, ow=1.25)
    text(s, x - 1, cy - 0.62, 2, 0.35, name, size=15, color=AUX if end else INK, bold=not end, align='c')
for j, x in enumerate(sx):          # candidate servers for the Firewall
    line(s, xs[2], cy + 0.17, x, servers_y - 0.08, color=ACC if j == pick else mix(AUX, 0.45),
         w=1.75 if j == pick else 0.6)
for j, x in enumerate(sx):
    dot(s, x, servers_y, 0.08, fill=ACC if j == pick else AUX)
text(s, sx[0] - 1.6, servers_y - 0.16, 1.4, 0.35, '12 servers', size=13, color=AUX, align='r')
text(s, LM, 5.65, 11.6, 0.9, [[('Which server for each VNF?  ', {'bold': True}),
                               ('Latency = path delay + processing delay.', {'color': AUX})]], size=20)

# 3 --------------------------------------------------------------------------------------- hidden slow servers
s = D.slide('The catch', [[('Some servers are ', {}), ('secretly slower.', {'color': ACC})]], notes="""
Real data centres mix hardware generations; the same workload runs at very different speeds (Reiss 2012, Paragon).
In our simulator every server gets a hidden speed factor kappa. With sigma = 1 it ranges from 0.18 (Indianapolis)
to 5.65 (Houston): about 30 times. This is OUR assumption, I will come back to that.
The controller knows the topology and path delays exactly, but not these speeds.""")
sp = sorted(WORLD.speed.items(), key=lambda kv: kv[1])
x0, x1, base, scale = LM + 0.6, 8.2, 4.25, 0.95          # log10 scale: 1 decade = 0.95 in
line(s, x0 - 0.3, base, x1 + 0.3, base, color=INK, w=0.75)
text(s, x0 - 0.35 - 1.6, base - 0.15, 1.5, 0.3, '1× (average)', size=11, color=AUX, align='r')
for k, (n, kap) in enumerate(sp):
    x = x0 + (x1 - x0) * k / 11
    y = base - np.log10(kap) * scale * 1.7
    hot = kap == max(WORLD.speed.values())
    col = ACC if hot else (INK if kap > 1 else AUX)
    line(s, x, base, x, y, color=col, w=2 if hot else 1.25)
    dot(s, x, y, 0.08 if hot else 0.06, fill=col)
    if hot or kap == min(WORLD.speed.values()):
        text(s, x - 1, y + (-0.42 if kap > 1 else 0.12), 2, 0.3, f'{CITY[n]}  {kap:.2f}×', size=12,
             color=col, bold=True, align='c')
text(s, x0 - 1.9, base - 1.25, 1.5, 0.3, 'slower ↑', size=11, color=AUX, align='r')
text(s, x0 - 1.9, base + 0.95, 1.5, 0.3, 'faster ↓', size=11, color=AUX, align='r')
text(s, 9.0, 2.6, 3.5, 3, [[('Same VNF, different hardware: ', {'bold': True}),
                            ('up to 30× slower.', {'bold': True, 'color': ACC})],
                           'The orchestrator cannot see this.'], size=20, spacing=1.2, after=10)
text(s, 9.0, 5.35, 3.5, 0.3, 'Hidden speed factor κ — our assumption', size=11, color=AUX)

# 4 ------------------------------------------------------------------------------------------------------ KDN
s = D.slide('The idea', 'Knowledge-Defined Networking', notes="""
KDN (Mestres et al. 2017), building on Clark's knowledge plane: the controller collects telemetry,
learns a model of how the network behaves, and uses the model for decisions.
Here: measure the processing delay of every placed VNF, learn a delay model, use it to choose servers.""")
steps = [('measure', 'per-VNF delay telemetry'), ('learn', 'a model of the delay'), ('decide', 'where to place')]
cxs = [LM + 1.7, W / 2, W - LM - 1.7]
cy = 3.75
for k, ((a, b), x) in enumerate(zip(steps, cxs)):
    dot(s, x, cy, 0.78, fill=BG, outline=INK if k != 1 else ACC, ow=1.5)
    text(s, x - 1.5, cy - 0.25, 3, 0.5, a, size=22, font=SERIF, color=ACC if k == 1 else INK, align='c', anchor='m')
    text(s, x - 1.6, cy + 0.95, 3.2, 0.4, b, size=15, color=AUX, align='c')
    if k < 2:
        line(s, x + 0.88, cy, cxs[k + 1] - 0.88, cy, color=INK, w=1, head=True)
# feedback arc drawn as three thin segments
yb = cy + 1.9
line(s, cxs[2], cy + 1.4, cxs[2], yb, color=mix(AUX, 0.7), w=0.75, dash='dash')
line(s, cxs[2], yb, cxs[0], yb, color=mix(AUX, 0.7), w=0.75, dash='dash')
line(s, cxs[0], yb, cxs[0], cy + 1.4, color=mix(AUX, 0.7), w=0.75, dash='dash', head=True)
text(s, W / 2 - 2, yb + 0.1, 4, 0.3, 'new placements produce new telemetry', size=11, color=AUX, align='c')

# 5 ------------------------------------------------------------------------------------------------- question
s = D.slide('Research question', notes="""
So the narrow question of this paper: if some servers are secretly slower,
can a model learned from past per-VNF measurements find them and place chains better than a simple shortest-path rule?
And under which load conditions? The second half turns out to be the interesting part.""")
text(s, LM, 1.7, 10.8, 3.6, [[('Can a model learned from past measurements ', {}),
                              ('find the slow servers', {'color': ACC}),
                              (', and under which load does it pay off?', {})]],
     size=40, font=SERIF, spacing=1.08)

# 6 ------------------------------------------------------------------------------------------------- testbed
s = D.slide('Testbed', 'The Abilene backbone', notes="""
Trace-driven simulation of Abilene, a US research backbone, SNDlib version: 12 nodes, 15 links.
Link delay = great-circle distance x 5 microseconds per km. Labels are ms.
Each node hosts one server with 100 CPU and 100 RAM units. Link capacities are scaled down so chains can fill them.
Three services: Web (NAT-Firewall-Monitor), VoIP (NAT-SBC-Firewall-IDS), Video (NAT-DPI-Transcoder).""")
draw_network(s, (LM + 0.2, 1.95, 7.4, 4.4), edge_color=AUX, edge_w=1.25, node_r=0.085, delays=True)
text(s, 9.85, 2.4, 2.7, 3.2, [[('12', {'font': SERIF, 'size': 40})], 'nodes, one server each',
                              [('15', {'font': SERIF, 'size': 40})], 'links, delay in ms'],
     size=15, color=INK, spacing=1.05, after=6)

# 7 ------------------------------------------------------------------------------------------- real vs assumed
s = D.slide('Honesty first', 'What is real, what is assumed', notes="""
Real: the topology, the Abilene traffic matrices of 2004 (5-minute volumes between all city pairs), and VNF CPU
measurements from the KDN dataset. The matrices set the arrival rate over time and pick ingress/egress.
The heat strip is real: total Abilene volume, first week of March 2004, one cell per hour.
Assumed by us: the processing-delay formula (an M/M/1 queue), the hidden server speeds, VNF types and chains.
Important: no dataset contains placements or latencies. Latencies come from the simulator.""")
cx = W / 2 + 0.1
line(s, cx, 2.25, cx, 6.35, color=mix(AUX, 0.6), w=0.75)
text(s, LM, 2.2, 5, 0.4, 'REAL DATA', size=11, bold=True, color=ACC, tracking=2.2)
text(s, LM, 2.65, 5.3, 2.0, ['Abilene topology', 'Traffic matrices, 2004', 'Measured VNF CPU load'],
     size=20, spacing=1.15, after=8)
text(s, cx + 0.5, 2.2, 5, 0.4, 'OUR ASSUMPTIONS', size=11, bold=True, color=AUX, tracking=2.2)
text(s, cx + 0.5, 2.65, 5.3, 2.0, ['Processing-delay formula', 'Hidden server speeds', 'VNF types and chains'],
     size=20, spacing=1.15, after=8)
idx = WORLD.split_idx['train'][:7 * 288]
v = WORLD.volume[idx].reshape(7, 24, 12).mean(2)
v = (v - v.min()) / (v.max() - v.min())
cw, ch, gx, gy = 0.2, 0.16, LM, 4.75
for d in range(7):
    for hh in range(24):
        rrect(s, gx + hh * (cw + 0.03), gy + d * (ch + 0.03), cw, ch, mix(ACC, 0.08 + 0.92 * v[d, hh]), radius=0.04)
text(s, gx, gy + 7 * (ch + 0.03) + 0.05, 5.6, 0.3, 'Abilene traffic, first week of March 2004 (hourly)',
     size=10.5, color=AUX)

# 8 ---------------------------------------------------------------------------------------------------- model
s = D.slide('The model', 'Telemetry in, delay out', notes="""
Data: we run the simulator on March-June with randomised placements, so we see many servers at many loads.
Every accepted VNF is one row: 212,621 rows. Inputs are things known at decision time: VNF type, host node,
host load, CPU this chain reserves there, how many of its VNFs share the host, packets, flows, network load.
Target: the processing delay of that VNF. XGBoost, 150 trees, depth 5.
The node identity lets the model learn which servers are slow without ever seeing kappa.
R2 = 0.997 sounds great but the simulator has no noise; the model just re-learns our formula.
Real telemetry would be much noisier.""")
feats = ['VNF type', 'host node', 'host load', 'CPU reserved', 'co-located VNFs', 'packets, flows', 'network load']
fy = np.linspace(1.95, 5.75, len(feats))
mxx, myy = 7.0, (fy[0] + fy[-1]) / 2
for k, (f, y) in enumerate(zip(feats, fy)):
    hot = f == 'host node'
    text(s, LM, y - 0.17, 2.6, 0.35, f, size=16, color=ACC if hot else INK, bold=hot, align='r')
    dot(s, LM + 2.85, y, 0.05, fill=ACC if hot else AUX)
    line(s, LM + 2.9, y, mxx - 0.75, myy, color=ACC if hot else mix(AUX, 0.55), w=1.25 if hot else 0.6)
dot(s, mxx, myy, 0.72, fill=BG, outline=INK, ow=1.5)
text(s, mxx - 0.8, myy - 0.2, 1.6, 0.4, 'XGBoost', size=17, font=SERIF, align='c', anchor='m')
line(s, mxx + 0.75, myy, 9.05, myy, color=INK, w=1, head=True)
text(s, 9.2, myy - 0.48, 3.4, 1.0, [[('processing', {'bold': True})], [('delay (ms)', {'bold': True})]], size=18)
text(s, 9.2, 4.45, 3.4, 1.4, [[('R² = 0.997', {'font': SERIF, 'size': 30})],
                              [('noise-free simulator: it re-learns our formula', {'color': AUX, 'size': 12})]],
     size=14, spacing=1.15)

# 9 -------------------------------------------------------------------------------------------------- methods
s = D.slide('Placement', 'Three ways to place a VNF', notes="""
Same request, same network, three methods. The middle server lies on the shortest path but is secretly slow.
greedy: takes the first server in a fixed list that has room. Knows only capacities -> often a long detour.
smart: takes the server with the shortest path from the previous hop. Knows the topology, nothing about processing
-> short path, but it may land on the slow server.
kdn-greedy (ours): tries every server with room (at most 12) and scores it: path delay + processing delay predicted
by the model. Lowest score wins -> accepts a small detour to reach a fast server.
All methods place VNFs one by one in chain order and never backtrack; if nothing fits, the request is rejected.
oracle-greedy: the same search with the true delay. The best kdn-greedy could do with a perfect model.""")
gap = 0.5
pw = (W - 2 * LM - 2 * gap) / 3
methods = [('greedy', 'knows: capacities', 'long detour', AUX, 'A', 'sysDash'),
           ('smart', 'knows: topology', 'short path, slow server', INK, 'B', None),
           ('kdn-greedy', 'knows: topology + learned delay', 'small detour, fast server', ACC, 'C', None)]
for k, (name, knows, result, col, pick, dash) in enumerate(methods):
    px, py = LM + k * (pw + gap), 2.05
    P = {'in': (px + 0.2, py + 1.15), 'out': (px + pw - 0.2, py + 1.15), 'A': (px + 0.85, py + 0.1),
         'D': (px + pw - 0.85, py + 0.25), 'B': (px + pw / 2, py + 1.15), 'C': (px + pw / 2 + 0.1, py + 1.95)}
    edges = [('in', 'A'), ('A', 'D'), ('D', 'out'), ('in', 'B'), ('B', 'out'), ('in', 'C'), ('C', 'out')]
    route = {'A': [('in', 'A'), ('A', 'D'), ('D', 'out')], 'B': [('in', 'B'), ('B', 'out')],
             'C': [('in', 'C'), ('C', 'out')]}[pick]
    for u, v in edges:
        line(s, *P[u], *P[v], color=mix(AUX, 0.45), w=0.75)
    for u, v in route:
        line(s, *P[u], *P[v], color=col, w=3, dash=dash)
    for n in ('A', 'B', 'C', 'D'):
        chosen = n == pick
        if n == 'B':      # the secretly slow server: thick ring
            dot(s, *P[n], 0.2, fill=col if chosen else BG, outline=INK if not chosen else col, ow=2.5)
            text(s, P[n][0] - 0.6, P[n][1] - 0.52, 1.2, 0.3, 'slow', size=11, bold=True, color=AUX, align='c')
        else:
            dot(s, *P[n], 0.15 if chosen else 0.1, fill=col if chosen else AUX)
    for n, lab in (('in', 'in'), ('out', 'out')):
        dot(s, *P[n], 0.07, fill=BG, outline=INK, ow=1.25)
        text(s, P[n][0] - 0.5, P[n][1] + 0.12, 1.0, 0.3, lab, size=11, color=AUX, align='c')
    ty = 4.55
    text(s, px, ty, pw, 0.5, name, size=26, font=SERIF, color=col)
    text(s, px, ty + 0.62, pw, 0.35, knows, size=13, color=AUX)
    text(s, px, ty + 1.0, pw, 0.4, result, size=16, bold=True, color=col if col != AUX else INK)
    if name == 'kdn-greedy':
        text(s, px + pw - 1.0, ty + 0.12, 1.0, 0.3, 'OURS', size=10.5, bold=True, color=ACC, align='r', tracking=2)
    if k:
        line(s, px - gap / 2, 2.0, px - gap / 2, 6.0, color=mix(AUX, 0.4), w=0.5)

# 10 ------------------------------------------------------------------------------------------------- load
s = D.slide('Experiment', 'Normal load vs overload', notes="""
Test: July-September 2004 traffic, 30 seeds per cell, every method sees the same requests (paired comparison).
lambda is the request rate. At 0.02 and 0.05 less than half the CPU is reserved and 97-100% of requests are accepted:
this is how operators normally run a network, with headroom.
From 0.2 on, almost every server is full and more than half the requests are rejected: a stress test.""")
load = [(0.02, 23.3, 99.6, 'normal'), (0.05, 55.3, 96.6, 'normal'), (0.1, 81.7, 78.5, 'near capacity'),
        (0.2, 92.3, 47.9, 'overload'), (0.4, 95.6, 27.6, 'overload')]
colw = (W - 2 * LM) / 5
rrect(s, LM - 0.1, 2.05, 2 * colw - 0.1, 4.45, mix(INK, 0.05), radius=0.2)
for k, (lam, cpu, acc, reg) in enumerate(load):
    x = LM + k * colw + 0.25
    text(s, x, 2.3, colw - 0.4, 0.3, f'λ = {lam:g}', size=14, color=AUX, bold=True)
    text(s, x, 2.75, colw - 0.4, 0.8, f'{acc:.0f}%', size=40, font=SERIF, color=INK if k < 2 else AUX)
    text(s, x, 3.6, colw - 0.4, 0.3, 'accepted', size=12, color=AUX)
    mw = colw - 0.6
    line(s, x, 4.55, x + mw, 4.55, color=mix(AUX, 0.35), w=3)
    line(s, x, 4.55, x + mw * cpu / 100, 4.55, color=INK if k < 2 else AUX, w=3)
    text(s, x, 4.7, colw - 0.4, 0.3, f'{cpu:.0f}% CPU reserved', size=12, color=AUX)
    text(s, x, 5.75, colw - 0.4, 0.3, reg.upper(), size=10.5, bold=True, color=ACC if k < 2 else AUX, tracking=1.5)

# 11 --------------------------------------------------------------------------------------------- results chart
chart = os.path.join(BUILD, 'chart_results.png')
chart_results(chart)
s = D.slide('Result', 'At normal load, the model wins', notes="""
Mean end-to-end latency of accepted chains, 30 seeds, bands are 95% intervals.
Left: equal servers. kdn-greedy (red) is slightly below smart (black) everywhere.
Right: hidden slow servers. At light load the red line is clearly lower. As load grows the gap closes,
and at the two heaviest levels smart is slightly better. greedy (dashed) is the worst everywhere: long detours.""")
s.shapes.add_picture(chart, Inches(LM), Inches(1.95), width=Inches(W - 2 * LM))

# 12 --------------------------------------------------------------------------------------------- big number
s = D.slide('Headline', notes="""
Hidden slow servers, lightest load: kdn-greedy lowers mean latency by 21.6% vs smart, from 21.45 to 16.82 ms,
paired gain 4.63 +- 0.36 ms, better in all 30 seeds. At lambda 0.05: 13.1%, also 30 of 30.
The slowest requests gain more: p95 drops 29%, 41.9 to 29.7 ms.
With equal servers the gain is only 4.1% (0.75 ms): it comes from load information alone.
So most of the gain comes from finding the hidden slow servers.""")
text(s, LM, 1.35, 7.4, 2.6, '−21.6%', size=150, font=SERIF, color=ACC, spacing=0.9)
text(s, LM + 0.1, 4.2, 6.6, 1.4, [[('mean latency vs smart', {'bold': True})],
                                  [('hidden slow servers, light load · 4.6 ms · 30 of 30 seeds', {'color': AUX,
                                                                                                    'size': 15})]],
     size=22, spacing=1.25)
line(s, 8.55, 1.6, 8.55, 5.6, color=mix(AUX, 0.6), w=0.75)
text(s, 9.1, 2.0, 3.5, 1.3, '−4.1%', size=64, font=SERIF, color=AUX)
text(s, 9.1, 3.35, 3.4, 1.2, [[('with equal servers', {'bold': True})], [('0.75 ms', {'color': AUX, 'size': 15})]],
     size=18, spacing=1.25)

# 13 ---------------------------------------------------------------------------------------------------- heatmap
s = D.slide('Where it helps', [[('The gain lives where servers differ ', {}),
                                ('and the network has headroom.', {'color': ACC})]], title_size=32, notes="""
Change in mean latency of kdn-greedy vs smart in every cell. Red = kdn-greedy faster, grey = slower.
Top row, equal servers: small but positive everywhere, shrinking with load.
Bottom row, hidden slow servers: big at normal load, near zero at 0.1, about 2-3% worse at overload,
where it loses in most seeds (2 and 6 of 30).
Acceptance is the same for both methods within 1.1 points, so the gain is not bought with rejections.""")
gain = {0: [4.1, 2.9, 1.7, 0.8, 0.7], 1: [21.6, 13.1, 1.5, -3.0, -2.2]}
lams = [0.02, 0.05, 0.1, 0.2, 0.4]
gx, gy, cw, ch, gap = LM + 2.6, 3.0, 1.72, 1.15, 0.12
for j, lam in enumerate(lams):
    text(s, gx + j * (cw + gap), gy - 0.45, cw, 0.3, f'λ = {lam:g}', size=13, color=AUX, bold=True, align='c')
for i, (lab, sub) in enumerate([('equal servers', 'σ = 0'), ('hidden slow servers', 'σ = 1')]):
    y = gy + i * (ch + gap)
    text(s, LM, y + 0.3, 2.4, 0.7, [[(lab, {'bold': True})], [(sub, {'color': AUX, 'size': 12})]], size=15,
         align='r', spacing=1.1)
    for j, g in enumerate(gain[i]):
        t = min(1.0, abs(g) / 21.6) if g > 0 else min(1.0, abs(g) / 6)
        fill = mix(ACC, 0.1 + 0.9 * t) if g > 0 else mix(AUX, 0.25 + 0.6 * t)
        x = gx + j * (cw + gap)
        rrect(s, x, y, cw, ch, fill, radius=0.16)
        dark = g > 0 and t > 0.5
        text(s, x, y, cw, ch, f'{-g:+.1f}%'.replace('-', '−'), size=22, font=SERIF, color=BG if dark else INK,
             align='c', anchor='m')
yl = gy + 2 * (ch + gap) + 0.05
text(s, gx, yl, 2 * cw + gap, 0.3, 'NORMAL', size=10.5, bold=True, color=ACC, align='c', tracking=1.5)
text(s, gx + 2 * (cw + gap), yl, cw, 0.3, 'NEAR CAPACITY', size=10.5, bold=True, color=AUX, align='c', tracking=1.5)
text(s, gx + 3 * (cw + gap), yl, 2 * cw + gap, 0.3, 'OVERLOAD', size=10.5, bold=True, color=AUX, align='c',
     tracking=1.5)
text(s, gx, yl + 0.5, 5 * cw + 4 * gap, 0.3, 'Change in mean latency, kdn-greedy vs smart (lower is better)',
     size=12, color=AUX, align='c')

# 14 ------------------------------------------------------------------------------------------------------ why
s = D.slide('Why the gain disappears', 'Near capacity, the fast servers are already full', title_size=34, notes="""
Why does the gain disappear when the network is nearly full?
Light load (left): the fast servers still have room, so kdn-greedy can send the new request there. This is the gain.
Heavy load (right): every earlier request also chose the fastest servers, so they are full.
The new request has to go to a slow or distant server.
kdn-greedy optimises each request on its own and does not keep the fast servers free for later requests.
smart spreads requests along shortest paths, so it does not fill the fast servers first.
This is not a model error: oracle-greedy, which knows the true delays, behaves the same way;
kdn-greedy is within 0.22 ms of it in every cell. A better model would not fix this;
the placement would have to plan for future requests (future work).""")
panels = [('Light load', [0.35, 0.25, 0.4, 0.3, 0.2, 0.15], 0, 'a fast server still has room'),
          ('Heavy load', [1.0, 1.0, 1.0, 1.0, 0.55, 0.45], 4, 'fast servers full: goes to a slow one')]
bw, bh, bgap = 0.42, 2.0, 0.2
for k, (lab, used, pick, cap) in enumerate(panels):
    px, by = LM + k * 4.35, 2.55
    text(s, px, 2.0, 4, 0.4, lab, size=17, bold=True)
    for j, u in enumerate(used):
        x = px + j * (bw + bgap)
        rrect(s, x, by, bw, bh, mix(AUX, 0.15), radius=0.08)
        if u > 0:
            rrect(s, x, by + bh * (1 - u), bw, bh * u, mix(INK, 0.8), radius=0.08)
        if j == pick:
            nh = 0.3
            rrect(s, x, by + bh * (1 - u) - nh - 0.04, bw, nh, ACC, radius=0.08)
    x0b, x1b = px, px + 6 * bw + 5 * bgap
    text(s, x0b, by + bh + 0.1, x1b - x0b, 0.3, 'fast  →  slow servers', size=12, color=AUX, align='c')
    text(s, x0b, by + bh + 0.5, x1b - x0b + 0.3, 0.6, cap, size=14, color=ACC if k == 0 else INK, bold=True)
# legend
lx, ly = LM, 6.0
rrect(s, lx, ly, 0.25, 0.18, mix(INK, 0.8), radius=0.05)
text(s, lx + 0.35, ly - 0.04, 2.5, 0.3, 'used by earlier requests', size=12, color=AUX)
rrect(s, lx + 2.9, ly, 0.25, 0.18, ACC, radius=0.05)
text(s, lx + 3.25, ly - 0.04, 2.0, 0.3, 'new request', size=12, color=AUX)
line(s, 9.35, 2.05, 9.35, 5.9, color=mix(AUX, 0.5), w=0.75)
text(s, 9.8, 2.05, 2.8, 3.8, [[('Not a model error.', {'bold': True})],
                              [('An oracle that knows the true delays does the same.', {'color': AUX})],
                              [('≤ 0.22 ms', {'font': SERIF, 'size': 30, 'color': INK})],
                              [('model vs oracle, in every cell', {'color': AUX, 'size': 12})]],
     size=17, spacing=1.15, after=12)

# 15 ---------------------------------------------------------------------------------------------------- ablation
s = D.slide('Does it depend on the real data?', [[('Swap real data for synthetic: ', {}),
                                                 ('the gain stays the same.', {'color': ACC})]],
            title_size=34, notes="""
Question: is the gain caused by the real datasets? Test: replace them with simple synthetic data and run again.
Synthetic VNF loads: every VNF adds the same fixed load instead of the measured KDN CPU values.
Synthetic traffic: requests arrive at a constant rate between random city pairs instead of following the Abilene matrices.
Bars: latency gain over smart at normal load (lambda = 0.02, sigma = 1, 30 seeds).
(Uses oracle-greedy so the model does not have to be retrained for each variant; it matches kdn-greedy within 0.22 ms.)
All four bars are about 4.5-5 ms; the largest change at any load is 0.58 ms.
So the gain comes from the hidden slow servers and the topology, not from the traffic data.
The real data makes the request stream realistic, but it does not carry the result.""")
rows = [('Real data (original)', 4.63), ('Synthetic VNF loads', 4.46), ('Synthetic traffic', 5.01),
        ('Both synthetic', 4.85)]
ax0, ax1, vmax = LM + 3.6, 10.6, 6.0
X = lambda v: ax0 + (ax1 - ax0) * v / vmax
for k, (lab, v) in enumerate(rows):
    y = 2.2 + k * 0.78
    text(s, LM, y + 0.06, 3.35, 0.4, lab, size=16, bold=k == 0, align='r')
    rrect(s, ax0, y, X(v) - ax0, 0.48, ACC if k == 0 else mix(INK, 0.55), radius=0.1)
    text(s, X(v) + 0.15, y + 0.06, 1.4, 0.4, f'{v:.1f} ms', size=16, bold=True, color=ACC if k == 0 else INK)
ya = 2.2 + 4 * 0.78 + 0.05
line(s, ax0, ya - 0.08, ax1, ya - 0.08, color=mix(AUX, 0.5), w=0.5)
for v in range(0, 7):
    text(s, X(v) - 0.3, ya, 0.6, 0.3, f'{v}', size=12, color=AUX, align='c')
text(s, ax0, ya + 0.32, ax1 - ax0, 0.3, 'latency gain over smart at normal load (ms)', size=12, color=AUX, align='c')
text(s, LM, 6.3, 11, 0.4, [[('→ ', {'color': ACC}), ('The gain comes from the hidden slow servers, not from the data.',
                                                       {})]], size=16, bold=True)

# 16 ------------------------------------------------------------------------------------------------- limitations
s = D.slide('Limitations', 'What this study does not show', notes="""
None of the datasets contains placements or latencies; latencies come from our formula and the slow servers are ours.
So we do not show that ML lowers latency in a real network. We show: IF there is a hidden, learnable difference,
a model trained on telemetry finds it, and we measure how much that is worth under each load.
R2 0.997 is a property of the noise-free simulator; real telemetry would be noisier and the gain likely smaller.
Single 12-node topology, one server per node, one VNF instance per request, model trained once.""")
lim = [('No real latency measurements.', 'Delays come from our simulator.'),
       ('Slow servers are our assumption.', 'The gain scales with it: 4% vs 22%.'),
       ('One small topology.', 'No VNF sharing; model never retrained.')]
y = 2.3
for k, (a, b) in enumerate(lim):
    if k:
        line(s, LM, y - 0.3, W - LM, y - 0.3, color=mix(AUX, 0.45), w=0.5)
    text(s, LM, y, 6.3, 0.5, a, size=22, bold=True)
    text(s, 7.3, y + 0.04, 5.2, 0.5, b, size=18, color=AUX)
    y += 1.2

# 17 ------------------------------------------------------------------------------------------------- conclusion
s = D.slide('Conclusion', notes="""
Answer to the question: a learned latency model helps when there is hidden, learnable variation between servers
and the network has headroom. Then: 13-22% lower latency at normal load. Equal servers: 3-4%. Near capacity: gone.
Future work: (1) train and test on real per-VNF telemetry; (2) near capacity, account for future requests,
e.g. a load-balancing term or reinforcement learning; (3) update the model online, larger topologies, VNF sharing.""")
text(s, LM, 1.45, 11.2, 2.6, [[('A learned latency model helps when servers differ in ', {}),
                               ('hidden, learnable', {'color': ACC}), (' ways and the network has ', {}),
                               ('headroom', {'color': ACC}), ('.', {})]], size=38, font=SERIF, spacing=1.08)
line(s, LM, 4.55, LM + 0.6, 4.55, color=INK, w=1)
text(s, LM, 4.75, 3, 0.3, 'NEXT', size=10.5, bold=True, color=AUX, tracking=2.2)
nxt = ['Real, noisy telemetry', 'Look-ahead near capacity', 'Online model updates']
for k, t in enumerate(nxt):
    text(s, LM + k * 3.9, 5.15, 3.6, 0.5, t, size=18)

# 18 ---------------------------------------------------------------------------------------------------- thanks
s = D.slide(notes="""
Thank you. Code, configuration and all result files are public; the full pipeline runs with one script.""")
text(s, LM, 1.6, 7, 1.6, [[('Thank you.', {})], [('Questions?', {'color': ACC})]], size=58, font=SERIF, spacing=1.0)
text(s, LM, 4.7, 7, 1.2, ['Malik Kalembaşı  ·  kalembasi18@itu.edu.tr',
                          'github.com/kalembasi/traffic-aware-vnf-placement-KDN'], size=14, color=AUX, spacing=1.4)
draw_network(s, (7.6, 1.5, 4.9, 4.3), edge_color=mix(AUX, 0.55), node_r=0.055, node_fill=AUX, labels=False,
             path=('STTLng', 'DNVRng', 'KSCYng', 'HSTNng', 'ATLAng', 'WASHng'))

# backup 1 ---------------------------------------------------------------------------------------- decision time
s = D.slide('Backup', 'Decision time', notes="""
kdn-greedy needs 3.0-8.9 ms per request (Python, one desktop), smart at most 0.37 ms.
Paid once per service order; starting VNFs takes seconds to minutes and a service lives for hours.
The latency gain applies to every packet for the lifetime of the service.
It grows linearly with the number of servers because the model is queried for every feasible server.""")
text(s, LM, 2.1, 5.5, 1.4, '3–9 ms', size=80, font=SERIF, color=ACC)
text(s, LM, 3.55, 5.5, 0.4, 'kdn-greedy, per request', size=16, bold=True)
text(s, 6.9, 2.1, 5.5, 1.4, '< 0.4 ms', size=80, font=SERIF, color=AUX)
text(s, 6.9, 3.55, 5.5, 0.4, 'smart, per request', size=16, bold=True, color=AUX)
text(s, LM, 4.7, 11, 0.9, 'Paid once per service order. The latency gain applies to every packet.', size=20)

# backup 2 --------------------------------------------------------------------------------------- design history
s = D.slide('Backup', 'Design history', notes="""
The evaluation protocol was registered in the repository before data generation.
In its first version the model only chose among up to eight heuristic placements (the ones used for telemetry).
These were generated without knowledge of server speeds, so they rarely avoided slow servers:
the gain was smaller at every load and negative from lambda 0.1 on.
kdn-greedy, where the model builds the placement itself, was added to the protocol after those results and before
it was run. The repository contains the first version and other variants.""")
hist = [('v1', 'Model picks among 8 heuristic placements', 'smaller gain, negative from λ = 0.1'),
        ('v2', 'Model builds the placement itself (kdn-greedy)', 'added to the protocol before its test runs')]
y = 2.4
line(s, LM + 0.35, y + 0.2, LM + 0.35, y + 1.7, color=mix(AUX, 0.6), w=0.75)
for k, (a, b, c) in enumerate(hist):
    dot(s, LM + 0.35, y + 0.2, 0.12, fill=ACC if k else AUX)
    text(s, LM + 0.8, y, 1, 0.4, a, size=20, font=SERIF, color=ACC if k else AUX)
    text(s, LM + 1.7, y, 10, 0.4, b, size=20, bold=True)
    text(s, LM + 1.7, y + 0.48, 10, 0.4, c, size=16, color=AUX)
    y += 1.5

# backup 3 ------------------------------------------------------------------------------------- queueing model
qchart = os.path.join(BUILD, 'chart_queue.png')
chart_queue(qchart)
s = D.slide('Backup', 'Processing delay: an M/M/1 queue', notes="""
If asked about queueing theory:
The simulator computes each VNF's processing delay with the textbook M/M/1 formula (Kleinrock 1975):
the mean time a job spends in a single-server queue. M/M/1 = random (Poisson) arrivals, random (exponential)
service times, one server.
delay = kappa * s / (1 - rho).  s = base service time of the VNF (0.3 ms traffic monitor ... 5 ms video transcoder).
rho = how full the server is (actual load / capacity, measured after the new chain is placed), capped at 0.95 so the
delay stays finite. kappa = hidden speed factor of the server.
Intuition: an empty server serves immediately; at 50% load a job waits as long as it is served (x2);
at 90% load x10. So delay explodes as a server fills up.
Why this form: it is the standard, simplest queueing model; parameters are our choice.
Important: the controller and the model do NOT know this formula. The model only sees measured delays and learns it.
(The repository also contains a run with a different, linear delay form; it is not in the paper.)""")
text(s, LM, 2.1, 6.5, 0.8, [[('delay = ', {}), ('κ', {'color': ACC}), (' · s / (1 − ρ)', {})]], size=36,
     font=SANS)
defs = [('s', 'base service time of the VNF (0.3–5 ms)'), ('ρ', 'how full the server is (capped at 0.95)'),
        ('κ', 'hidden speed of the server')]
for k, (a, b) in enumerate(defs):
    y = 3.35 + k * 0.62
    text(s, LM, y, 0.5, 0.4, a, size=20, bold=True, color=ACC if a == 'κ' else INK)
    text(s, LM + 0.6, y + 0.03, 5.6, 0.4, b, size=16, color=AUX)
text(s, LM, 5.4, 6.0, 0.6, 'The model never sees this formula; it learns it from measurements.', size=15, bold=True)
s.shapes.add_picture(qchart, Inches(7.4), Inches(1.9), width=Inches(5.1))

assert D.i == N_MAIN + 3
out = os.path.join(HERE, 'slides.pptx')
D.p.save(out)
print('written', out)
