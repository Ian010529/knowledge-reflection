from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
WORK = ROOT / "work" / "tg_adoption_iter"
CANDIDATES = WORK / "tg_post2026_candidate_directions.csv"


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
        "xtick.major.size": 2.0,
        "ytick.major.size": 2.0,
    }
)


TYPE_ORDER = [
    "solvation_entropy",
    "transport_mechanism",
    "gel_microstructure",
    "electrode_interface",
    "redox_chemistry",
    "phase_or_species_transition",
    "material_system",
    "device_function",
]

TYPE_LABELS = {
    "solvation_entropy": "Solvation/\nentropy",
    "transport_mechanism": "Transport\nmechanism",
    "gel_microstructure": "Gel\nmicrostructure",
    "electrode_interface": "Electrode/\ninterface",
    "redox_chemistry": "Redox\nchemistry",
    "phase_or_species_transition": "Phase/species\ntransition",
    "material_system": "Material\nsystem",
    "device_function": "Device\nfunction",
}


def shorten(label, max_len=34):
    if len(label) <= max_len:
        return label
    pieces = label.replace("/", "/ ").split()
    lines = []
    line = ""
    for piece in pieces:
        token = piece.replace("/ ", "/")
        if len(line) + len(token) + 1 <= max_len:
            line = f"{line} {token}".strip()
        else:
            if line:
                lines.append(line)
            line = token
    if line:
        lines.append(line)
    return "\n".join(lines[:2])


def ordered_items(df, name_col, type_col, top_n):
    summary = (
        df.groupby([name_col, type_col], as_index=False)
        .agg(max_score=("final_score", "max"), mean_score=("final_score", "mean"), count=("final_score", "size"))
        .sort_values(["max_score", "mean_score", "count"], ascending=[False, False, False])
    )
    selected = summary.head(top_n)
    return selected[name_col].tolist()


def plot_concept_matrix(df):
    donors = ordered_items(df, "concept_i_ite_donor", "i_type", 18)
    anchors = ordered_items(df, "concept_j_tg_anchor", "j_type", 14)
    sub = df[df["concept_i_ite_donor"].isin(donors) & df["concept_j_tg_anchor"].isin(anchors)].copy()
    matrix = sub.pivot_table(
        index="concept_i_ite_donor",
        columns="concept_j_tg_anchor",
        values="final_score",
        aggfunc="max",
    ).reindex(index=donors, columns=anchors)
    bridges = sub.pivot_table(
        index="concept_i_ite_donor",
        columns="concept_j_tg_anchor",
        values="common_neighbors",
        aggfunc="max",
    ).reindex(index=donors, columns=anchors)

    values = matrix.to_numpy(dtype=float)
    masked = np.ma.masked_invalid(values)
    cmap = mpl.colormaps["YlGnBu"].copy()
    cmap.set_bad("#f2f2f2")

    fig_w = 9.3
    fig_h = 7.8
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(masked, cmap=cmap, vmin=np.nanpercentile(values, 5), vmax=np.nanmax(values), aspect="auto")

    ax.set_xticks(np.arange(len(anchors)))
    ax.set_yticks(np.arange(len(donors)))
    ax.set_xticklabels([shorten(x, 24) for x in anchors], rotation=50, ha="right", rotation_mode="anchor")
    ax.set_yticklabels([shorten(x, 33) for x in donors])
    ax.set_xlabel("TG anchor concept already present in the field")
    ax.set_ylabel("iTE/TD donor concept proposed for transfer into TG")
    ax.set_title(
        "Predicted post-2026 TG research directions\n"
        "Numbers show prediction score; parentheses show bridge-count in the historical concept graph",
        fontsize=10,
        loc="left",
        pad=8,
    )

    for i in range(len(donors)):
        for j in range(len(anchors)):
            if np.isfinite(values[i, j]):
                score = values[i, j]
                bridge = bridges.iloc[i, j]
                color = "white" if score > 1.82 else "#1b1b1b"
                ax.text(j, i, f"{score:.2f}\n({int(bridge)})", ha="center", va="center", fontsize=5.3, color=color)

    ax.set_xticks(np.arange(-0.5, len(anchors), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(donors), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    cbar = fig.colorbar(im, ax=ax, shrink=0.72, pad=0.015)
    cbar.set_label("Prediction score (actionability-adjusted)")

    fig.subplots_adjust(left=0.29, right=0.90, bottom=0.32, top=0.88)
    fig.savefig(WORK / "tg_post2026_concept_prediction_matrix.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_concept_prediction_matrix.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_concept_prediction_matrix.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_concept_prediction_matrix.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_score_decomposition_matrix(df):
    donors = ordered_items(df, "concept_i_ite_donor", "i_type", 12)
    anchors = ordered_items(df, "concept_j_tg_anchor", "j_type", 10)
    sub = df[df["concept_i_ite_donor"].isin(donors) & df["concept_j_tg_anchor"].isin(anchors)].copy()
    panels = [
        ("ML score\n(trained on rolling historical adoption)", "ml_score", "Blues", "probability-like"),
        ("Graph score\n(structural link-prediction score)", "graph_adoption_score", "YlGnBu", "ranked graph proximity"),
        ("Final score\n(hybrid + actionability prior)", "final_score", "PuBuGn", "direction ranking"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 6.4), sharey=True)
    for ax, (title, value_col, cmap_name, cbar_label) in zip(axes, panels):
        matrix = sub.pivot_table(
            index="concept_i_ite_donor",
            columns="concept_j_tg_anchor",
            values=value_col,
            aggfunc="max",
        ).reindex(index=donors, columns=anchors)
        values = matrix.to_numpy(dtype=float)
        masked = np.ma.masked_invalid(values)
        cmap = mpl.colormaps[cmap_name].copy()
        cmap.set_bad("#f2f2f2")
        im = ax.imshow(masked, cmap=cmap, aspect="auto")
        ax.set_title(title, fontsize=8.5, loc="left", pad=6)
        ax.set_xticks(np.arange(len(anchors)))
        ax.set_xticklabels([shorten(x, 20) for x in anchors], rotation=50, ha="right", rotation_mode="anchor", fontsize=6)
        ax.set_xticks(np.arange(-0.5, len(anchors), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(donors), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.8)
        ax.tick_params(which="minor", bottom=False, left=False)
        cbar = fig.colorbar(im, ax=ax, shrink=0.56, pad=0.012)
        cbar.ax.tick_params(labelsize=6)
        cbar.set_label(cbar_label, fontsize=6.5)
        for i in range(len(donors)):
            for j in range(len(anchors)):
                if np.isfinite(values[i, j]):
                    v = values[i, j]
                    color = "white" if v > np.nanpercentile(values, 75) else "#1b1b1b"
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=5.6, color=color)

    axes[0].set_yticks(np.arange(len(donors)))
    axes[0].set_yticklabels([shorten(x, 28) for x in donors], fontsize=7)
    axes[0].set_ylabel("iTE/TD donor concept")
    for ax in axes[1:]:
        ax.tick_params(labelleft=False)
    fig.suptitle("What is being predicted: future TG adoption of donor-anchor concept pairs", fontsize=11, x=0.03, ha="left")
    fig.text(0.5, 0.03, "TG anchor concept", ha="center", fontsize=8)
    fig.subplots_adjust(left=0.21, right=0.985, bottom=0.31, top=0.86, wspace=0.18)
    fig.savefig(WORK / "tg_post2026_prediction_score_decomposition_matrix.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_prediction_score_decomposition_matrix.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_prediction_score_decomposition_matrix.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_prediction_score_decomposition_matrix.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_type_matrix(df):
    grouped = (
        df.groupby(["i_type", "j_type"], as_index=False)
        .agg(
            max_score=("final_score", "max"),
            mean_score=("final_score", "mean"),
            n_pairs=("final_score", "size"),
        )
    )
    max_mat = grouped.pivot(index="i_type", columns="j_type", values="max_score").reindex(index=TYPE_ORDER, columns=TYPE_ORDER)
    n_mat = grouped.pivot(index="i_type", columns="j_type", values="n_pairs").reindex(index=TYPE_ORDER, columns=TYPE_ORDER)
    values = max_mat.to_numpy(dtype=float)
    masked = np.ma.masked_invalid(values)
    cmap = mpl.colormaps["PuBuGn"].copy()
    cmap.set_bad("#f2f2f2")

    fig, ax = plt.subplots(figsize=(6.9, 5.6), constrained_layout=True)
    im = ax.imshow(masked, cmap=cmap, vmin=np.nanpercentile(values, 5), vmax=np.nanmax(values), aspect="equal")
    ax.set_xticks(np.arange(len(TYPE_ORDER)))
    ax.set_yticks(np.arange(len(TYPE_ORDER)))
    ax.set_xticklabels([TYPE_LABELS[t] for t in TYPE_ORDER], rotation=35, ha="right", rotation_mode="anchor")
    ax.set_yticklabels([TYPE_LABELS[t] for t in TYPE_ORDER])
    ax.set_xlabel("TG anchor type")
    ax.set_ylabel("iTE/TD donor type")
    ax.set_title("Predicted knowledge transfer by concept type", fontsize=10, loc="left", pad=8)

    for i in range(len(TYPE_ORDER)):
        for j in range(len(TYPE_ORDER)):
            if np.isfinite(values[i, j]):
                score = values[i, j]
                n = int(n_mat.iloc[i, j])
                color = "white" if score > 1.78 else "#1b1b1b"
                ax.text(j, i, f"{score:.2f}\nn={n}", ha="center", va="center", fontsize=6, color=color)

    ax.set_xticks(np.arange(-0.5, len(TYPE_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(TYPE_ORDER), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.9)
    ax.tick_params(which="minor", bottom=False, left=False)

    cbar = fig.colorbar(im, ax=ax, shrink=0.78, pad=0.02)
    cbar.set_label("Best prediction score in type block")

    fig.savefig(WORK / "tg_post2026_type_prediction_matrix.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_type_prediction_matrix.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_type_prediction_matrix.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_post2026_type_prediction_matrix.pdf", bbox_inches="tight")
    plt.close(fig)


def write_preview_table(df):
    top = df.sort_values("final_score", ascending=False).head(30).copy()
    top["rank"] = np.arange(1, len(top) + 1)
    cols = [
        "rank",
        "concept_i_ite_donor",
        "concept_j_tg_anchor",
        "i_type",
        "j_type",
        "actionability_score",
        "ml_score",
        "graph_adoption_score",
        "hybrid_adoption_score",
        "hybrid_actionability_score",
        "common_neighbors",
        "shortest_path",
    ]
    top[cols].to_csv(WORK / "tg_post2026_prediction_matrix_top30.csv", index=False)


def main():
    df = pd.read_csv(CANDIDATES)
    df["final_score"] = df.get("hybrid_actionability_score", df.get("actionability_score"))
    df = df[np.isfinite(df["final_score"])].copy()
    plot_concept_matrix(df)
    plot_score_decomposition_matrix(df)
    plot_type_matrix(df)
    write_preview_table(df)
    print("wrote matrix previews to", WORK)


if __name__ == "__main__":
    main()
