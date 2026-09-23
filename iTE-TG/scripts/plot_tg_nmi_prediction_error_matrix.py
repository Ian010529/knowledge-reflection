from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from sklearn.metrics import confusion_matrix


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


COLORS = {
    "missing": "#f3f3f3",
    "TN": "#d9d9d9",
    "FP": "#fdd49e",
    "FN": "#fdae6b",
    "TP": "#2ca25f",
}


def shorten(label, max_len=30):
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


def add_prediction_labels(df, score_col="hybrid_adoption_score", k=25):
    out = df.copy()
    out["y_true"] = out["future_TG_edge_label"].astype(int)
    out["y_pred_topk"] = 0
    idx = out.sort_values(score_col, ascending=False).head(k).index
    out.loc[idx, "y_pred_topk"] = 1
    conditions = {
        (0, 0): "TN",
        (1, 0): "FN",
        (0, 1): "FP",
        (1, 1): "TP",
    }
    out["error_class"] = [
        conditions[(yt, yp)] for yt, yp in zip(out["y_true"], out["y_pred_topk"])
    ]
    return out


def ordered_axes(df):
    donor_order = (
        df.groupby("concept_i_ite_donor")
        .agg(
            positives=("y_true", "sum"),
            predicted=("y_pred_topk", "sum"),
            max_score=("hybrid_adoption_score", "max"),
            n=("y_true", "size"),
        )
        .sort_values(["predicted", "positives", "max_score", "n"], ascending=False)
        .index.tolist()
    )
    anchor_order = (
        df.groupby("concept_j_tg_anchor")
        .agg(
            positives=("y_true", "sum"),
            predicted=("y_pred_topk", "sum"),
            max_score=("hybrid_adoption_score", "max"),
            n=("y_true", "size"),
        )
        .sort_values(["predicted", "positives", "max_score", "n"], ascending=False)
        .index.tolist()
    )
    return donor_order, anchor_order


def plot_error_matrix(df, k=25):
    donors, anchors = ordered_axes(df)
    class_to_code = {"TN": 1, "FP": 2, "FN": 3, "TP": 4}
    code = np.zeros((len(donors), len(anchors)), dtype=float)
    score = np.full_like(code, np.nan)
    bridge = np.full_like(code, np.nan)
    for row in df.itertuples():
        i = donors.index(row.concept_i_ite_donor)
        j = anchors.index(row.concept_j_tg_anchor)
        code[i, j] = class_to_code[row.error_class]
        score[i, j] = row.hybrid_adoption_score
        bridge[i, j] = row.common_neighbors

    cmap = ListedColormap([COLORS["missing"], COLORS["TN"], COLORS["FP"], COLORS["FN"], COLORS["TP"]])
    fig, ax = plt.subplots(figsize=(10.2, 7.2))
    ax.imshow(code, cmap=cmap, vmin=0, vmax=4, aspect="auto")
    ax.set_xticks(np.arange(len(anchors)))
    ax.set_yticks(np.arange(len(donors)))
    ax.set_xticklabels([shorten(x, 24) for x in anchors], rotation=50, ha="right", rotation_mode="anchor")
    ax.set_yticklabels([shorten(x, 31) for x in donors])
    ax.set_xlabel("TG anchor concept")
    ax.set_ylabel("iTE/TD donor concept")
    ax.set_title(
        f"NMI-style prediction/error matrix, top-{k} as predicted positive\n"
        "Cell class compares 2022 prediction with realized TG links in 2023-2026; number = hybrid score, parentheses = bridge count",
        loc="left",
        fontsize=10,
        pad=8,
    )
    ax.set_xticks(np.arange(-0.5, len(anchors), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(donors), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    for i in range(len(donors)):
        for j in range(len(anchors)):
            if code[i, j] == 0:
                continue
            klass = [k for k, v in class_to_code.items() if v == code[i, j]][0]
            txt_color = "white" if klass == "TP" else "#1b1b1b"
            if klass in {"TP", "FP", "FN"}:
                ax.text(
                    j,
                    i,
                    f"{klass}\n{score[i, j]:.2f}\n({int(bridge[i, j])})",
                    ha="center",
                    va="center",
                    fontsize=5.5,
                    color=txt_color,
                )
            elif score[i, j] >= np.nanpercentile(score, 75):
                ax.text(j, i, f"{score[i, j]:.2f}", ha="center", va="center", fontsize=5.2, color=txt_color)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=COLORS[name], ec="none")
        for name in ["TP", "FP", "FN", "TN", "missing"]
    ]
    labels = [
        "TP: predicted and realized",
        "FP: predicted only",
        "FN: missed but realized",
        "TN: neither",
        "not a candidate pair",
    ]
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(1.005, 1.0), fontsize=6.4, frameon=False)
    fig.subplots_adjust(left=0.27, right=0.78, bottom=0.32, top=0.86)
    stem = WORK / f"tg_nmi_style_prediction_error_matrix_top{k}"
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def plot_threshold_matrix(df):
    out = df.copy()
    out["rank_score"] = out["hybrid_adoption_score"].rank(pct=True)
    out["y_pred_topk"] = (out["rank_score"] >= 0.5).astype(int)
    conditions = {
        (0, 0): "TN",
        (1, 0): "FN",
        (0, 1): "FP",
        (1, 1): "TP",
    }
    out["error_class"] = [
        conditions[(yt, yp)] for yt, yp in zip(out["y_true"], out["y_pred_topk"])
    ]
    plot_error_matrix(out, k=143)
    src = WORK / "tg_nmi_style_prediction_error_matrix_top143.png"
    if src.exists():
        src.rename(WORK / "tg_nmi_style_prediction_error_matrix_threshold_rank0p5.png")
    for ext in ["svg", "pdf"]:
        src2 = WORK / f"tg_nmi_style_prediction_error_matrix_top143.{ext}"
        if src2.exists():
            src2.rename(WORK / f"tg_nmi_style_prediction_error_matrix_threshold_rank0p5.{ext}")


def write_matrix_source(df, k=25):
    cols = [
        "concept_i_ite_donor",
        "concept_j_tg_anchor",
        "i_type",
        "j_type",
        "y_true",
        "y_pred_topk",
        "error_class",
        "ml_score",
        "graph_adoption_score",
        "hybrid_adoption_score",
        "common_neighbors",
        "shortest_path",
        "future_example_title",
    ]
    out = df[cols].sort_values(["error_class", "hybrid_adoption_score"], ascending=[True, False])
    out.to_csv(WORK / f"tg_nmi_style_prediction_error_matrix_top{k}_source.csv", index=False)
    cm = confusion_matrix(df["y_true"], df["y_pred_topk"], labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    pd.DataFrame(
        [
            {
                "top_k": k,
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn,
                "true_positive": tp,
                "precision": tp / max(1, tp + fp),
                "recall": tp / max(1, tp + fn),
            }
        ]
    ).to_csv(WORK / f"tg_nmi_style_prediction_error_matrix_top{k}_summary.csv", index=False)


def main():
    raw = pd.read_csv(SCORED)
    for k in [10, 25, 50]:
        df = add_prediction_labels(raw, k=k)
        plot_error_matrix(df, k=k)
        write_matrix_source(df, k=k)
    df25 = add_prediction_labels(raw, k=25)
    plot_threshold_matrix(df25)
    print("wrote NMI-style prediction/error matrices to", WORK)


if __name__ == "__main__":
    main()
