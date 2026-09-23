from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
WORK = ROOT / "work" / "tg_adoption_iter"
SCORED = WORK / "tg_adoption_scored_candidates_2022_to_2026.csv"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.7,
        "legend.frameon": False,
    }
)


MODELS = [
    ("ML", "ml_score", "#2b8cbe"),
    ("Graph", "graph_adoption_score", "#756bb1"),
    ("Hybrid", "hybrid_adoption_score", "#238b45"),
]


def rank01(values):
    return pd.Series(values).rank(pct=True).to_numpy()


def normalize_for_threshold(df):
    out = df.copy()
    # NMI marks threshold=0.5 on model probabilities. Our graph/hybrid scores
    # are rank-style scores, so convert all displayed decision scores to ranks
    # on [0, 1] for a comparable threshold panel.
    for _, col, _ in MODELS:
        out[f"{col}_rank01"] = rank01(out[col].fillna(0))
    return out


def metrics_at_threshold(y, score, threshold=0.5):
    pred = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1": 0 if (2 * tp + fp + fn) == 0 else 2 * tp / (2 * tp + fp + fn),
    }


def metrics_at_k(y, score, k):
    pred = np.zeros(len(y), dtype=int)
    idx = np.argsort(score)[::-1][: min(k, len(score))]
    pred[idx] = 1
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "k": k,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1": 0 if (2 * tp + fp + fn) == 0 else 2 * tp / (2 * tp + fp + fn),
    }


def write_nmi_tables(df):
    y = df["future_TG_edge_label"].astype(int).to_numpy()
    rows = []
    threshold_rows = []
    k_rows = []
    for model, col, _ in MODELS:
        raw_score = df[col].fillna(0).to_numpy()
        rank_score = df[f"{col}_rank01"].to_numpy()
        rows.append(
            {
                "model": model,
                "roc_auc_raw_score": roc_auc_score(y, raw_score),
                "average_precision_raw_score": average_precision_score(y, raw_score),
                "positive_rate": y.mean(),
                "n_candidates": len(y),
                "n_positives": int(y.sum()),
            }
        )
        thr = metrics_at_threshold(y, rank_score, threshold=0.5)
        thr.update({"model": model, "decision_score": f"{col}_rank01"})
        threshold_rows.append(thr)
        for k in [10, 25, 50, 100]:
            kr = metrics_at_k(y, raw_score, k)
            kr.update({"model": model, "score": col})
            k_rows.append(kr)

    pd.DataFrame(rows).to_csv(WORK / "tg_nmi_style_auc_ap_summary.csv", index=False)
    pd.DataFrame(threshold_rows).to_csv(WORK / "tg_nmi_style_threshold_0p5_confusion.csv", index=False)
    pd.DataFrame(k_rows).to_csv(WORK / "tg_nmi_style_precision_recall_at_k.csv", index=False)


def plot_roc_pr(df):
    y = df["future_TG_edge_label"].astype(int).to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), constrained_layout=True)

    for model, col, color in MODELS:
        score = df[col].fillna(0).to_numpy()
        fpr, tpr, _ = roc_curve(y, score)
        precision, recall, _ = precision_recall_curve(y, score)
        axes[0].plot(fpr, tpr, color=color, lw=1.4, label=f"{model} AUC={roc_auc_score(y, score):.3f}")
        axes[1].plot(recall, precision, color=color, lw=1.4, label=f"{model} AP={average_precision_score(y, score):.3f}")

    axes[0].plot([0, 1], [0, 1], color="#bdbdbd", lw=0.9, ls="--")
    axes[0].set_xlabel("False positive rate")
    axes[0].set_ylabel("True positive rate")
    axes[0].set_title("ROC curve", loc="left", fontsize=9)
    axes[0].legend(fontsize=6)

    baseline = y.mean()
    axes[1].axhline(baseline, color="#bdbdbd", lw=0.9, ls="--", label=f"random={baseline:.3f}")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_ylim(0, 1.02)
    axes[1].set_title("Precision-recall curve", loc="left", fontsize=9)
    axes[1].legend(fontsize=6)

    fig.suptitle("NMI-style link-prediction evaluation: cutoff 2022 -> TG links in 2023-2026", x=0.02, ha="left", fontsize=10)
    fig.savefig(WORK / "tg_nmi_style_roc_pr_curves.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_nmi_style_roc_pr_curves.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_nmi_style_roc_pr_curves.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_threshold_confusion(df):
    y = df["future_TG_edge_label"].astype(int).to_numpy()
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6), constrained_layout=True)
    matrices = []
    for _, col, _ in MODELS:
        pred = (df[f"{col}_rank01"].to_numpy() >= 0.5).astype(int)
        matrices.append(confusion_matrix(y, pred, labels=[0, 1]))
    vmax = max(m.max() for m in matrices)
    for ax, (model, _, _), cm in zip(axes, MODELS, matrices):
        im = ax.imshow(cm, cmap=mpl.colormaps["Blues"], vmin=0, vmax=vmax)
        ax.set_title(f"{model}, rank threshold=0.5", fontsize=8.2)
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred 0", "Pred 1"])
        ax.set_yticklabels(["True 0", "True 1"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=10, color="white" if cm[i, j] > vmax * 0.55 else "#1b1b1b")
        tn, fp, fn, tp = cm.ravel()
        p = tp / max(1, tp + fp)
        r = tp / max(1, tp + fn)
        ax.set_xlabel(f"P={p:.2f}, R={r:.2f}", fontsize=7)
    fig.colorbar(im, ax=axes, shrink=0.8, pad=0.02, label="Number of candidate pairs")
    fig.suptitle("NMI-style threshold panel: score rank >= 0.5 as positive", x=0.02, ha="left", fontsize=10)
    fig.savefig(WORK / "tg_nmi_style_threshold_0p5_confusion.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_nmi_style_threshold_0p5_confusion.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_nmi_style_threshold_0p5_confusion.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_precision_at_k(df):
    y = df["future_TG_edge_label"].astype(int).to_numpy()
    ks = np.arange(1, min(101, len(y) + 1))
    fig, ax = plt.subplots(figsize=(4.8, 3.2), constrained_layout=True)
    for model, col, color in MODELS:
        score = df[col].fillna(0).to_numpy()
        ranked = np.argsort(score)[::-1]
        hits = np.cumsum(y[ranked[: len(ks)]])
        precision = hits / ks
        ax.plot(ks, precision, color=color, lw=1.5, label=model)
        for k in [10, 25, 50, 100]:
            if k <= len(ks):
                ax.scatter(k, precision[k - 1], color=color, s=14, zorder=3)
    ax.axhline(y.mean(), color="#bdbdbd", lw=0.9, ls="--", label=f"random={y.mean():.3f}")
    ax.set_xlabel("k")
    ax.set_ylabel("Precision@k")
    ax.set_ylim(0, 1.02)
    ax.set_title("Top-k recommendation quality", loc="left", fontsize=9)
    ax.legend(fontsize=6)
    fig.savefig(WORK / "tg_nmi_style_precision_at_k.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_nmi_style_precision_at_k.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_nmi_style_precision_at_k.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    df = pd.read_csv(SCORED)
    df = normalize_for_threshold(df)
    write_nmi_tables(df)
    plot_roc_pr(df)
    plot_threshold_confusion(df)
    plot_precision_at_k(df)
    print("wrote NMI-style evaluation outputs to", WORK)


if __name__ == "__main__":
    main()
