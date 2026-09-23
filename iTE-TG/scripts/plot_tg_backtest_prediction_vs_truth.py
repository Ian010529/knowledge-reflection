from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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
    }
)


def shorten(label, max_len=31):
    if len(label) <= max_len:
        return label
    words = label.replace("/", "/ ").split()
    lines, line = [], ""
    for word in words:
        token = word.replace("/ ", "/")
        if len(line) + len(token) + 1 <= max_len:
            line = f"{line} {token}".strip()
        else:
            if line:
                lines.append(line)
            line = token
    if line:
        lines.append(line)
    return "\n".join(lines[:2])


def confusion_at_k(df, score_col, k):
    ranked = df.sort_values(score_col, ascending=False).copy()
    ranked["predicted_positive"] = 0
    ranked.iloc[: min(k, len(ranked)), ranked.columns.get_loc("predicted_positive")] = 1
    y = ranked["future_TG_edge_label"].astype(int)
    p = ranked["predicted_positive"].astype(int)
    tn = int(((p == 0) & (y == 0)).sum())
    fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum())
    tp = int(((p == 1) & (y == 1)).sum())
    return np.array([[tn, fp], [fn, tp]])


def plot_confusion_matrices(df, k=25):
    panels = [
        ("ML", "ml_score"),
        ("Graph", "graph_adoption_score"),
        ("Hybrid", "hybrid_adoption_score"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6), constrained_layout=True)
    vmax = max(confusion_at_k(df, c, k).max() for _, c in panels)
    for ax, (name, col) in zip(axes, panels):
        cm = confusion_at_k(df, col, k)
        im = ax.imshow(cm, cmap=mpl.colormaps["Blues"], vmin=0, vmax=vmax)
        ax.set_title(f"{name} top-{k}", fontsize=8.5)
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred 0", "Pred 1"])
        ax.set_yticklabels(["True 0", "True 1"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=10, color="white" if cm[i, j] > vmax * 0.55 else "#1b1b1b")
        tp = cm[1, 1]
        fp = cm[0, 1]
        fn = cm[1, 0]
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        ax.set_xlabel(f"P={precision:.2f}, R={recall:.2f}", fontsize=7)
    fig.colorbar(im, ax=axes, shrink=0.8, pad=0.02, label="Number of candidate pairs")
    fig.suptitle("Backtest prediction vs. realized TG adoption, cutoff 2022 -> 2023-2026", x=0.02, ha="left", fontsize=10)
    fig.savefig(WORK / "tg_backtest_prediction_vs_truth_confusion_top25.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_backtest_prediction_vs_truth_confusion_top25.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_backtest_prediction_vs_truth_confusion_top25.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_backtest_prediction_vs_truth_confusion_top25.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_score_truth_matrix(df):
    donors = (
        df.groupby("concept_i_ite_donor")["hybrid_adoption_score"]
        .max()
        .sort_values(ascending=False)
        .head(16)
        .index.tolist()
    )
    anchors = (
        df.groupby("concept_j_tg_anchor")["hybrid_adoption_score"]
        .max()
        .sort_values(ascending=False)
        .head(12)
        .index.tolist()
    )
    sub = df[df["concept_i_ite_donor"].isin(donors) & df["concept_j_tg_anchor"].isin(anchors)].copy()
    score = sub.pivot_table(
        index="concept_i_ite_donor",
        columns="concept_j_tg_anchor",
        values="hybrid_adoption_score",
        aggfunc="max",
    ).reindex(index=donors, columns=anchors)
    truth = sub.pivot_table(
        index="concept_i_ite_donor",
        columns="concept_j_tg_anchor",
        values="future_TG_edge_label",
        aggfunc="max",
    ).reindex(index=donors, columns=anchors)
    values = score.to_numpy(dtype=float)
    labels = truth.to_numpy(dtype=float)
    masked = np.ma.masked_invalid(values)
    cmap = mpl.colormaps["YlGnBu"].copy()
    cmap.set_bad("#f2f2f2")

    top25_pairs = set(
        tuple(x)
        for x in df.sort_values("hybrid_adoption_score", ascending=False)
        .head(25)[["concept_i_ite_donor", "concept_j_tg_anchor"]]
        .to_numpy()
    )

    fig, ax = plt.subplots(figsize=(8.8, 7.2))
    im = ax.imshow(masked, cmap=cmap, aspect="auto")
    ax.set_title(
        "Backtest score matrix with realized future TG links\n"
        "Color = predicted hybrid score; star = actually appeared in TG papers during 2023-2026; red outline = top-25 prediction",
        loc="left",
        fontsize=10,
        pad=8,
    )
    ax.set_xticks(np.arange(len(anchors)))
    ax.set_yticks(np.arange(len(donors)))
    ax.set_xticklabels([shorten(x, 23) for x in anchors], rotation=50, ha="right", rotation_mode="anchor")
    ax.set_yticklabels([shorten(x, 31) for x in donors])
    ax.set_xlabel("TG anchor concept")
    ax.set_ylabel("iTE/TD donor concept")
    ax.set_xticks(np.arange(-0.5, len(anchors), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(donors), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    for i, donor in enumerate(donors):
        for j, anchor in enumerate(anchors):
            if not np.isfinite(values[i, j]):
                continue
            is_hit = labels[i, j] == 1
            is_top25 = (donor, anchor) in top25_pairs
            ax.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", fontsize=5.8, color="#111")
            if is_hit:
                ax.scatter(j, i + 0.24, marker="*", s=32, color="#d7301f", edgecolor="white", linewidth=0.4, zorder=5)
            if is_top25:
                rect = plt.Rectangle((j - 0.49, i - 0.49), 0.98, 0.98, fill=False, edgecolor="#d7301f", linewidth=1.2)
                ax.add_patch(rect)
    cbar = fig.colorbar(im, ax=ax, shrink=0.72, pad=0.015)
    cbar.set_label("Hybrid prediction score")
    fig.subplots_adjust(left=0.28, right=0.90, bottom=0.32, top=0.86)
    fig.savefig(WORK / "tg_backtest_score_truth_concept_matrix.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_backtest_score_truth_concept_matrix.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_backtest_score_truth_concept_matrix.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_backtest_score_truth_concept_matrix.pdf", bbox_inches="tight")
    plt.close(fig)


def write_confusion_summary(df):
    rows = []
    for score_col, name in [
        ("ml_score", "ML"),
        ("graph_adoption_score", "Graph"),
        ("hybrid_adoption_score", "Hybrid"),
    ]:
        for k in [10, 25, 50, 100]:
            cm = confusion_at_k(df, score_col, k)
            tn, fp, fn, tp = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
            rows.append(
                {
                    "model": name,
                    "top_k_as_predicted_positive": k,
                    "true_negative": tn,
                    "false_positive": fp,
                    "false_negative": fn,
                    "true_positive": tp,
                    "precision": tp / max(1, tp + fp),
                    "recall": tp / max(1, tp + fn),
                }
            )
    pd.DataFrame(rows).to_csv(WORK / "tg_backtest_prediction_vs_truth_confusion_summary.csv", index=False)


def main():
    df = pd.read_csv(SCORED)
    plot_confusion_matrices(df, k=25)
    plot_score_truth_matrix(df)
    write_confusion_summary(df)
    print("wrote backtest prediction-vs-truth matrices to", WORK)


if __name__ == "__main__":
    main()
