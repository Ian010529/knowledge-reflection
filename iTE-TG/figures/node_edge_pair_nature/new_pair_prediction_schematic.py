from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


OUT = Path(__file__).resolve().parent

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "font.size": 7,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})

INK = "#22272D"
MUTED = "#697680"
ITE = "#21827D"
ITE_FILL = "#D7EFEC"
TG = "#6B54A0"
TG_FILL = "#E9E1F5"
SHARED = "#D98937"
SHARED_FILL = "#FFF0DF"
CANDIDATE = "#C94F45"
PANEL = "#F8FAFB"
BORDER = "#C8D0D6"


def rounded(ax, x, y, w, h, fc=PANEL, ec=BORDER, lw=0.8, radius=0.025, ls="-"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls,
    )
    ax.add_patch(p)
    return p


def node(ax, x, y, text, fc, ec, r=0.072, fs=6.8):
    ax.add_patch(Circle((x, y), r, facecolor=fc, edgecolor=ec, linewidth=1.25, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK, zorder=4, linespacing=1.0)


def edge(ax, a, b, color, label=None, dashed=False, direction=True, yoff=0.045):
    style = "-|>" if direction else "-"
    p = FancyArrowPatch(
        a, b, arrowstyle=style, mutation_scale=8.5,
        linewidth=1.35, color=color,
        linestyle=(0, (4, 3)) if dashed else "-",
        shrinkA=6, shrinkB=6, zorder=2,
    )
    ax.add_patch(p)
    if label:
        ax.text((a[0]+b[0])/2, (a[1]+b[1])/2+yoff, label,
                ha="center", va="center", fontsize=5.8,
                color=color, fontweight="bold")


fig = plt.figure(figsize=(7.2047, 3.05), facecolor="white")  # 183 mm wide
gs = fig.add_gridspec(1, 3, width_ratios=[0.9, 0.9, 1.32], wspace=0.10)
axs = [fig.add_subplot(gs[0, i]) for i in range(3)]
for ax in axs:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

# a: observed iTE pair
ax = axs[0]
ax.text(0.01, 0.97, "a", fontsize=9, fontweight="bold", va="top")
ax.text(0.10, 0.925, "Observed iTE pair", fontsize=8.0, fontweight="bold")
rounded(ax, 0.08, 0.25, 0.84, 0.53)
node(ax, 0.28, 0.56, "A", ITE_FILL, ITE)
node(ax, 0.72, 0.56, "X", SHARED_FILL, SHARED)
edge(ax, (0.35, 0.56), (0.65, 0.56), ITE, "relation 1")
ax.text(0.50, 0.365, "supported by an iTE sentence", ha="center", fontsize=6.1, color=MUTED)
ax.text(0.50, 0.19, "known pair: A–X", ha="center", fontsize=6.5, fontweight="bold", color=ITE)

# b: observed TG pair
ax = axs[1]
ax.text(0.01, 0.97, "b", fontsize=9, fontweight="bold", va="top")
ax.text(0.10, 0.925, "Observed TG pair", fontsize=8.0, fontweight="bold")
rounded(ax, 0.08, 0.25, 0.84, 0.53)
node(ax, 0.28, 0.56, "X", SHARED_FILL, SHARED)
node(ax, 0.72, 0.56, "B", TG_FILL, TG)
edge(ax, (0.35, 0.56), (0.65, 0.56), TG, "relation 2")
ax.text(0.50, 0.365, "supported by a TG sentence", ha="center", fontsize=6.1, color=MUTED)
ax.text(0.50, 0.19, "known pair: X–B", ha="center", fontsize=6.5, fontweight="bold", color=TG)

# c: shared-node path proposes an unobserved endpoint pair
ax = axs[2]
ax.text(0.01, 0.97, "c", fontsize=9, fontweight="bold", va="top")
ax.text(0.085, 0.925, "Shared-node path proposes a candidate", fontsize=8.0, fontweight="bold")
rounded(ax, 0.055, 0.19, 0.89, 0.64, fc="white", ec="#AEB8C0", lw=0.95, radius=0.035)

node(ax, 0.20, 0.57, "A", ITE_FILL, ITE, r=0.067)
node(ax, 0.50, 0.57, "X", SHARED_FILL, SHARED, r=0.076)
node(ax, 0.80, 0.57, "B", TG_FILL, TG, r=0.067)
edge(ax, (0.265, 0.57), (0.425, 0.57), ITE, "iTE evidence", yoff=0.052)
edge(ax, (0.575, 0.57), (0.735, 0.57), TG, "TG evidence", yoff=0.052)
ax.text(0.50, 0.455, "exact shared concept", ha="center", fontsize=5.9, color=SHARED, fontweight="bold")

# Candidate bridge is deliberately separate and dashed.
curve = FancyArrowPatch(
    (0.20, 0.49), (0.80, 0.49),
    connectionstyle="arc3,rad=0.34", arrowstyle="<->",
    mutation_scale=8.5, linewidth=1.45, color=CANDIDATE,
    linestyle=(0, (4, 3)), shrinkA=6, shrinkB=6, zorder=1,
)
ax.add_patch(curve)
ax.text(0.50, 0.285, "candidate pair  A ··· B  ?", ha="center", fontsize=6.7,
        color=CANDIDATE, fontweight="bold")
ax.text(0.50, 0.235, "proposed—not observed", ha="center", fontsize=5.9, color=MUTED)

# Compact legend and take-home rule.
fig.lines.append(plt.Line2D([0.23, 0.275], [0.075, 0.075], transform=fig.transFigure, color=INK, lw=1.35))
fig.text(0.282, 0.075, "solid = source-supported pair", va="center", fontsize=6.1, color=MUTED)
fig.lines.append(plt.Line2D([0.55, 0.595], [0.075, 0.075], transform=fig.transFigure,
                            color=CANDIDATE, lw=1.35, linestyle=(0, (4, 3))))
fig.text(0.602, 0.075, "dashed = untested candidate pair", va="center", fontsize=6.1, color=MUTED)
fig.text(0.5, 0.018,
         "A–X and X–B are observed independently; the shared node X makes A–B a testable hypothesis, not a discovered relation.",
         ha="center", va="bottom", fontsize=6.3, color=INK, fontweight="bold")

base = OUT / "new_pair_prediction_nature"
fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white")
plt.close(fig)
