from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


OUT = Path(__file__).resolve().parent

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7,
        "axes.linewidth": 0.8,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)

INK = "#20252B"
MUTED = "#66727D"
LIGHT = "#E9EEF2"
ITE = "#7CCBC4"
ITE_DARK = "#237D78"
TG = "#B9A7DB"
TG_DARK = "#6D559A"
ACCENT = "#E7A35A"
PAPER = "#F7F9FA"


def rounded(ax, xy, w, h, fc="white", ec=INK, lw=0.9, radius=0.04, ls="-"):
    patch = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        linestyle=ls,
    )
    ax.add_patch(patch)
    return patch


def node(ax, x, y, label, color, edge, r=0.085, fs=6.4):
    ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor=edge, linewidth=1.15))
    ax.text(x, y, label, ha="center", va="center", color=INK, fontsize=fs, linespacing=1.05)


def arrow(ax, p0, p1, color=INK, lw=1.1, style="-|>", mutation=10, ls="-"):
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle=style,
            mutation_scale=mutation,
            linewidth=lw,
            color=color,
            linestyle=ls,
            shrinkA=1,
            shrinkB=1,
        )
    )


fig = plt.figure(figsize=(7.2047, 3.5827), facecolor="white")  # 183 × 91 mm
gs = fig.add_gridspec(1, 3, width_ratios=[0.92, 1.08, 1.12], wspace=0.11)
axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
for ax in axes:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

# a — concepts are grounded spans
ax = axes[0]
ax.text(0.015, 0.965, "a", fontweight="bold", fontsize=9, va="top")
ax.text(0.09, 0.925, "Concept extraction", fontweight="bold", fontsize=8.2)
rounded(ax, (0.08, 0.23), 0.72, 0.57, fc=PAPER, ec="#C9D1D7", lw=0.8, radius=0.025)
ax.text(0.13, 0.735, "ABSTRACT", fontsize=5.7, fontweight="bold", color=MUTED)
ax.plot([0.13, 0.72], [0.69, 0.69], color="#CCD3D8", lw=2.2, solid_capstyle="round")
ax.plot([0.13, 0.68], [0.64, 0.64], color="#CCD3D8", lw=2.2, solid_capstyle="round")
rounded(ax, (0.125, 0.50), 0.29, 0.075, fc="#D9F0ED", ec="none", radius=0.018)
rounded(ax, (0.49, 0.50), 0.24, 0.075, fc="#E8E0F4", ec="none", radius=0.018)
ax.text(0.27, 0.538, "Concept A", ha="center", va="center", fontsize=6.4, color=ITE_DARK)
ax.text(0.61, 0.538, "Concept B", ha="center", va="center", fontsize=6.4, color=TG_DARK)
ax.text(0.44, 0.538, "…", ha="center", va="center", fontsize=7, color=MUTED)
ax.plot([0.13, 0.72], [0.44, 0.44], color="#CCD3D8", lw=2.2, solid_capstyle="round")
ax.plot([0.13, 0.62], [0.39, 0.39], color="#CCD3D8", lw=2.2, solid_capstyle="round")
arrow(ax, (0.82, 0.51), (0.92, 0.51), color=MUTED, lw=0.9)
node(ax, 0.93, 0.64, "A", "#D9F0ED", ITE_DARK, r=0.055, fs=7)
node(ax, 0.93, 0.39, "B", "#E8E0F4", TG_DARK, r=0.055, fs=7)
ax.text(0.44, 0.145, "Node = one normalized concept\nanchored to an exact text span", ha="center", color=MUTED, fontsize=6.2)

# b — pair as minimum evidence unit (hero panel)
ax = axes[1]
ax.text(0.015, 0.965, "b", fontweight="bold", fontsize=9, va="top")
ax.text(0.09, 0.925, "Evidence-backed pair", fontweight="bold", fontsize=8.2)
rounded(ax, (0.07, 0.22), 0.86, 0.60, fc="white", ec="#AAB4BC", lw=1.0, radius=0.04)
ax.text(0.50, 0.765, "PAIR", ha="center", fontsize=6.2, fontweight="bold", color=MUTED)
node(ax, 0.26, 0.51, "Concept A", "#D9F0ED", ITE_DARK, r=0.105)
node(ax, 0.74, 0.51, "Concept B", "#E8E0F4", TG_DARK, r=0.105)
arrow(ax, (0.37, 0.51), (0.63, 0.51), color=INK, lw=1.35, mutation=9)
rounded(ax, (0.405, 0.555), 0.19, 0.072, fc="#FFF1E3", ec=ACCENT, lw=0.75, radius=0.02)
ax.text(0.50, 0.591, "relation", ha="center", va="center", color="#9A5C1D", fontsize=6.1, fontweight="bold")
ax.text(0.50, 0.385, "supported by the same sentence", ha="center", fontsize=6.1, color=MUTED)
ax.plot([0.26, 0.74], [0.348, 0.348], color="#CAD1D6", lw=0.7)
ax.text(0.50, 0.292, "Pair = (node A, evidence edge, node B)", ha="center", fontsize=6.5, fontweight="bold", color=INK)
ax.text(0.50, 0.14, "Co-occurrence alone does not create an edge", ha="center", fontsize=6.2, color="#A55245")

# c — shared nodes assemble pairs into a graph
ax = axes[2]
ax.text(0.015, 0.965, "c", fontweight="bold", fontsize=9, va="top")
ax.text(0.09, 0.925, "Graph assembly", fontweight="bold", fontsize=8.2)

coords = {
    "A": (0.18, 0.66),
    "B": (0.46, 0.66),
    "C": (0.46, 0.38),
    "D": (0.76, 0.52),
    "E": (0.86, 0.76),
}
for u, v, col in [("A", "B", ITE_DARK), ("B", "C", ITE_DARK), ("C", "D", TG_DARK), ("D", "E", TG_DARK)]:
    arrow(ax, coords[u], coords[v], color=col, lw=1.15, mutation=7)

node(ax, *coords["A"], "A", "#D9F0ED", ITE_DARK, r=0.066, fs=6.5)
node(ax, *coords["B"], "B", "#D9F0ED", ITE_DARK, r=0.066, fs=6.5)
node(ax, *coords["C"], "shared\nconcept", "#FFF1E3", ACCENT, r=0.078, fs=5.7)
node(ax, *coords["D"], "D", "#E8E0F4", TG_DARK, r=0.066, fs=6.5)
node(ax, *coords["E"], "E", "#E8E0F4", TG_DARK, r=0.066, fs=6.5)

rounded(ax, (0.075, 0.835), 0.21, 0.055, fc="#D9F0ED", ec="none", radius=0.014)
ax.text(0.18, 0.862, "iTE pairs", ha="center", va="center", fontsize=5.8, color=ITE_DARK, fontweight="bold")
rounded(ax, (0.695, 0.835), 0.21, 0.055, fc="#E8E0F4", ec="none", radius=0.014)
ax.text(0.80, 0.862, "TG pairs", ha="center", va="center", fontsize=5.8, color=TG_DARK, fontweight="bold")

ax.text(0.50, 0.23, "Pairs merge only through identical,\ntraceable concept nodes", ha="center", fontsize=6.2, color=MUTED)
ax.plot([0.15, 0.85], [0.165, 0.165], color=LIGHT, lw=0.8)
ax.text(0.50, 0.105, "nodes → evidence edges → pairs → graph", ha="center", fontsize=6.5, fontweight="bold", color=INK)

fig.text(
    0.5,
    0.015,
    "Observed relations are retained as solid edges; inferred cross-system hypotheses must be represented separately.",
    ha="center",
    va="bottom",
    fontsize=6.2,
    color=MUTED,
)

base = OUT / "node_edge_pair_nature"
fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white")
plt.close(fig)
