from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = ROOT / "minimal_clean_predictions" / "ml_visualization"
OUT.mkdir(exist_ok=True)

COLORS = {
    "ml": "#2F6B8A",
    "graph": "#D08C3F",
    "hybrid": "#4B8B68",
    "positive": "#C84C5A",
    "negative": "#AEB7BF",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def save_pub(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def top_k_precision(y: np.ndarray, score: np.ndarray, ks: np.ndarray) -> np.ndarray:
    order = np.argsort(score)[::-1]
    return np.array([y[order[: min(k, len(order))]].mean() for k in ks])


def plot_diagnostic(frame: pd.DataFrame, title: str, stem: str) -> None:
    y = frame["future_edge_label"].astype(int).to_numpy()
    scores = {
        "ML": frame["ml_score"].to_numpy(),
        "Graph": frame["graph_score"].to_numpy(),
        "Hybrid": frame["hybrid_score"].to_numpy(),
    }
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.0), constrained_layout=True)

    ax = axes[0, 0]
    for label, score in scores.items():
        fpr, tpr, _ = roc_curve(y, score)
        auc = roc_auc_score(y, score)
        ax.plot(fpr, tpr, lw=1.5, color=COLORS[label.lower()], label=f"{label}  AUC={auc:.3f}")
    ax.plot([0, 1], [0, 1], color="#999999", lw=0.8, ls="--")
    ax.set(xlabel="False-positive rate", ylabel="True-positive rate")
    ax.set_title("a  ROC ranking performance", loc="left", fontsize=8)
    ax.legend(fontsize=6, loc="lower right")

    ax = axes[0, 1]
    for label, score in scores.items():
        precision, recall, _ = precision_recall_curve(y, score)
        ap = average_precision_score(y, score)
        ax.plot(recall, precision, lw=1.5, color=COLORS[label.lower()], label=f"{label}  AP={ap:.3f}")
    ax.axhline(y.mean(), color="#999999", lw=0.8, ls="--", label=f"Random={y.mean():.3f}")
    ax.set(xlabel="Recall", ylabel="Precision")
    ax.set_title("b  Precision-recall enrichment", loc="left", fontsize=8)
    ax.legend(fontsize=6, loc="upper right")

    ax = axes[1, 0]
    bins = np.linspace(0, 1, 24)
    ax.hist(
        scores["ML"][y == 0],
        bins=bins,
        density=True,
        alpha=0.72,
        color=COLORS["negative"],
        label="Not observed",
    )
    ax.hist(
        scores["ML"][y == 1],
        bins=bins,
        density=True,
        alpha=0.68,
        color=COLORS["positive"],
        label="Observed",
    )
    ax.set(xlabel="ML rank score", ylabel="Density")
    ax.set_title("c  ML score separation", loc="left", fontsize=8)
    ax.legend(fontsize=6)

    ax = axes[1, 1]
    ax.scatter(
        scores["Graph"][y == 0],
        scores["ML"][y == 0],
        s=7,
        alpha=0.25,
        color=COLORS["negative"],
        linewidths=0,
        label="Not observed",
    )
    ax.scatter(
        scores["Graph"][y == 1],
        scores["ML"][y == 1],
        s=12,
        alpha=0.72,
        color=COLORS["positive"],
        linewidths=0,
        label="Observed",
    )
    ax.set(xlabel="Graph score", ylabel="ML score")
    ax.set_title("d  ML-Graph agreement and disagreement", loc="left", fontsize=8)
    ax.legend(fontsize=6, loc="lower right")

    fig.suptitle(title, x=0.01, ha="left", fontsize=10)
    save_pub(fig, OUT / stem)
    plt.close(fig)

    ks = np.array([10, 25, 50, 100, 250])
    rows = []
    for label, score in scores.items():
        for k, precision in zip(ks, top_k_precision(y, score, ks)):
            rows.append({"model": label, "k": int(k), "precision_at_k": precision})
    pd.DataFrame(rows).to_csv(OUT / f"{stem}_topk.csv", index=False)


def main() -> None:
    transfer = pd.read_csv(
        ROOT
        / "minimal_clean_predictions"
        / "ite_to_tg"
        / "ite_to_tg_scored_candidates_2022_to_2026.csv"
    )
    tg_self = pd.read_csv(
        ROOT
        / "minimal_clean_predictions"
        / "tg_to_tg"
        / "tg_self_scored_candidates_2022_to_2026.csv"
    )
    plot_diagnostic(
        transfer,
        "ML diagnostics for iTE-to-TG knowledge transfer",
        "ite_to_tg_ml_diagnostics",
    )
    plot_diagnostic(
        tg_self,
        "ML diagnostics for TG internal evolution",
        "tg_to_tg_ml_diagnostics",
    )


if __name__ == "__main__":
    main()
