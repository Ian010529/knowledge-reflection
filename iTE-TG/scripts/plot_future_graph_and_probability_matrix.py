from __future__ import annotations

from itertools import combinations
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

import minimal_clean_ite_to_tg_prediction as graph_pipeline


ROOT = Path("/Users/ryan/Documents/iTE&TG")
FLOW = ROOT / "mechanism_transfer_workflow"
MODEL = FLOW / "two_stage_model"
FIG = FLOW / "figures"
FIG.mkdir(exist_ok=True)

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

TYPE_COLORS = {
    "transport_mechanism": "#267A8A",
    "solvation_entropy": "#D95D39",
    "gel_microstructure": "#5B8E55",
    "phase_or_species_transition": "#C89A3D",
    "electrode_interface": "#4F67A3",
    "device_mechanism": "#7A7F83",
}
TYPE_LABELS = {
    "transport_mechanism": "Transport",
    "solvation_entropy": "Solvation/entropy",
    "gel_microstructure": "Gel structure",
    "phase_or_species_transition": "Phase/species",
    "electrode_interface": "Electrode interface",
    "device_mechanism": "Device mechanism",
}


def save(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def annual_graph_scores(frame: pd.DataFrame) -> pd.DataFrame:
    scored = []
    for _, group in frame.groupby("cutoff_year"):
        group = group.copy()
        group["annual_graph_score"] = graph_pipeline.graph_score(group)
        scored.append(group)
    return pd.concat(scored, ignore_index=True)


def calibration_and_future() -> tuple[pd.DataFrame, pd.DataFrame]:
    annual = annual_graph_scores(
        pd.read_csv(MODEL / "pair_annual_risk_rows.csv")
    )
    calibration_train = annual[
        annual.cutoff_year.between(2020, 2024)
    ].copy()
    calibration_test = annual[annual.cutoff_year.eq(2025)].copy()
    calibration = LogisticRegression(C=1.0, max_iter=2000, random_state=27)
    calibration.fit(
        calibration_train[["annual_graph_score"]],
        calibration_train.label.astype(int),
    )
    test_probability = calibration.predict_proba(
        calibration_test[["annual_graph_score"]]
    )[:, 1]
    audit = pd.DataFrame(
        [
            {
                "calibration_train_years": "2020-2024",
                "test_year": "2025->2026",
                "test_candidates": len(calibration_test),
                "test_positives": int(calibration_test.label.sum()),
                "test_auc": roc_auc_score(
                    calibration_test.label, test_probability
                ),
                "test_ap": average_precision_score(
                    calibration_test.label, test_probability
                ),
                "test_brier": brier_score_loss(
                    calibration_test.label, test_probability
                ),
            }
        ]
    )

    final_train = annual[annual.cutoff_year.between(2020, 2025)].copy()
    final_calibration = LogisticRegression(
        C=1.0, max_iter=2000, random_state=27
    )
    final_calibration.fit(
        final_train[["annual_graph_score"]],
        final_train.label.astype(int),
    )
    future = pd.read_csv(MODEL / "future_2027_graph_ranking.csv")
    future["calibrated_annual_probability"] = final_calibration.predict_proba(
        future[["annual_graph_score"]]
    )[:, 1]
    future["probability_note"] = (
        "Exploratory one-year probability calibrated from 2020-2026 annual events"
    )
    audit["final_calibration_intercept"] = final_calibration.intercept_[0]
    audit["final_calibration_coefficient"] = final_calibration.coef_[0, 0]
    audit.to_csv(MODEL / "graph_probability_calibration_audit.csv", index=False)
    future.to_csv(MODEL / "future_2027_graph_with_probability.csv", index=False)
    return annual, future


def shorten(label: str, n: int = 27) -> str:
    return label if len(label) <= n else label[: n - 3] + "..."


def plot_network(future: pd.DataFrame, vocab: pd.DataFrame) -> None:
    top = future.head(35).copy()
    graph = nx.Graph()
    for row in top.itertuples(index=False):
        graph.add_edge(
            row.concept_u_id,
            row.concept_v_id,
            score=row.annual_graph_score,
            probability=row.calibrated_annual_probability,
        )
    vocab_index = vocab.set_index("concept_id")
    frequency = vocab_index.document_frequency.to_dict()
    node_type = vocab_index.concept_type.to_dict()
    labels = vocab_index.canonical_concept.to_dict()
    position = nx.spring_layout(
        graph,
        seed=27,
        k=1.45 / np.sqrt(max(1, len(graph.nodes))),
        iterations=400,
        weight="score",
    )
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    fig.subplots_adjust(left=0.04, right=0.98, top=0.92, bottom=0.12)
    edge_scores = np.array(
        [graph[u][v]["score"] for u, v in graph.edges]
    )
    widths = 0.7 + 3.0 * (
        (edge_scores - edge_scores.min())
        / max(1e-9, edge_scores.max() - edge_scores.min())
    )
    nx.draw_networkx_edges(
        graph,
        position,
        ax=ax,
        width=widths,
        edge_color=edge_scores,
        edge_cmap=mpl.colormaps["YlGnBu"],
        edge_vmin=edge_scores.min(),
        edge_vmax=edge_scores.max(),
        alpha=0.72,
    )
    for mechanism_type, color in TYPE_COLORS.items():
        nodes = [
            node for node in graph.nodes if node_type.get(node) == mechanism_type
        ]
        if not nodes:
            continue
        nx.draw_networkx_nodes(
            graph,
            position,
            nodelist=nodes,
            node_color=color,
            node_size=[
                52 + 7.5 * np.sqrt(max(1, frequency.get(node, 1)))
                for node in nodes
            ],
            edgecolors="white",
            linewidths=0.8,
            label=TYPE_LABELS[mechanism_type],
            ax=ax,
        )
    degree = dict(graph.degree)
    label_nodes = sorted(
        graph.nodes,
        key=lambda node: (degree[node], frequency.get(node, 0)),
        reverse=True,
    )[:18]
    for index, node in enumerate(label_nodes):
        x, y = position[node]
        radial = np.array([x, y])
        norm = np.linalg.norm(radial)
        direction = radial / norm if norm else np.array([1.0, 0.0])
        offset = direction * (0.035 + 0.007 * (index % 3))
        ax.annotate(
            shorten(labels[node]),
            xy=(x, y),
            xytext=(x + offset[0], y + offset[1]),
            fontsize=5.5,
            ha="left" if offset[0] >= 0 else "right",
            va="center",
            arrowprops={
                "arrowstyle": "-",
                "color": "#879096",
                "lw": 0.45,
            },
        )
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.03),
        ncol=3,
        fontsize=6,
        handletextpad=0.4,
        columnspacing=1.0,
    )
    ax.set_title(
        "2027 mechanism-pair transfer candidates",
        loc="left",
        fontsize=9,
        fontweight="bold",
        pad=8,
    )
    ax.axis("off")
    save(fig, FIG / "future_2027_mechanism_graph")
    plt.close(fig)
    nx.to_pandas_edgelist(graph).to_csv(
        MODEL / "future_2027_graph_figure_edges.csv", index=False
    )


def tg_edge_set() -> set[tuple[str, str]]:
    mapping = pd.read_csv(FLOW / "pure_mechanism_paper_map.csv")
    papers = pd.read_csv(DATA / "final_paper_index.csv")
    tg_ids = set(
        papers[papers.source_membership.str.contains("TG", na=False)].paper_id
    )
    mapping = mapping[mapping.paper_id.isin(tg_ids)]
    edges = set()
    for _, group in mapping.groupby("paper_id"):
        edges.update(combinations(sorted(group.concept_id.unique()), 2))
    return edges


DATA = ROOT / "minimal_clean_concept_layer"


def plot_matrix(future: pd.DataFrame, vocab: pd.DataFrame) -> None:
    top = future.head(100)
    weighted = pd.concat(
        [
            top[["concept_u_id", "annual_graph_score"]].rename(
                columns={"concept_u_id": "concept_id"}
            ),
            top[["concept_v_id", "annual_graph_score"]].rename(
                columns={"concept_v_id": "concept_id"}
            ),
        ]
    ).groupby("concept_id").annual_graph_score.sum().sort_values(ascending=False)
    selected = weighted.head(15).index.tolist()
    index = {concept: idx for idx, concept in enumerate(selected)}
    score = np.full((len(selected), len(selected)), np.nan)
    probability = np.full_like(score, np.nan)
    for row in future.itertuples(index=False):
        if row.concept_u_id in index and row.concept_v_id in index:
            i, j = index[row.concept_u_id], index[row.concept_v_id]
            score[i, j] = score[j, i] = row.annual_graph_score
            probability[i, j] = probability[j, i] = (
                row.calibrated_annual_probability
            )
    known = tg_edge_set()
    known_mask = np.zeros_like(score, dtype=bool)
    for u, v in known:
        if u in index and v in index:
            i, j = index[u], index[v]
            known_mask[i, j] = known_mask[j, i] = True
    np.fill_diagonal(score, np.nan)
    np.fill_diagonal(probability, np.nan)
    labels_lookup = vocab.set_index("concept_id").canonical_concept.to_dict()
    labels = [shorten(labels_lookup[node], 24) for node in selected]

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 7.6))
    fig.subplots_adjust(left=0.34, right=0.91, top=0.93, bottom=0.07, hspace=0.34)
    cmap = mpl.colormaps["YlGnBu"].copy()
    cmap.set_bad("#F2F4F5")
    images = [
        axes[0].imshow(score, cmap=cmap, vmin=0, vmax=1),
        axes[1].imshow(
            probability,
            cmap=cmap,
            vmin=0,
            vmax=max(0.2, np.nanmax(probability)),
        ),
    ]
    titles = [
        "a  Graph transfer-risk rank",
        "b  Calibrated one-year probability",
    ]
    for ax, title in zip(axes, titles):
        ax.set_xticks(range(len(labels)), range(1, len(labels) + 1), fontsize=5)
        ax.set_yticks(range(len(labels)), labels, fontsize=5)
        ax.tick_params(length=0)
        ax.set_xlabel("Mechanism index (same order as rows)", fontsize=6)
        ax.set_title(title, loc="left", fontsize=8)
        y, x = np.where(known_mask)
        ax.scatter(
            x,
            y,
            marker="x",
            s=6,
            linewidths=0.45,
            color="#6E7477",
        )
    fig.colorbar(
        images[0],
        ax=axes[0],
        fraction=0.035,
        pad=0.02,
        label="Graph score",
    )
    fig.colorbar(
        images[1],
        ax=axes[1],
        fraction=0.035,
        pad=0.02,
        label="Exploratory probability",
    )
    fig.suptitle(
        "Mechanism-pair candidates after the 2026 cutoff",
        x=0.04,
        ha="left",
        fontsize=9,
        fontweight="bold",
    )
    save(fig, FIG / "future_2027_graph_probability_matrix")
    plt.close(fig)
    pd.DataFrame(score, index=labels, columns=labels).to_csv(
        MODEL / "future_2027_graph_score_matrix.csv"
    )
    pd.DataFrame(probability, index=labels, columns=labels).to_csv(
        MODEL / "future_2027_probability_matrix.csv"
    )


def main() -> None:
    _, future = calibration_and_future()
    vocab = pd.read_csv(FLOW / "pure_mechanism_vocabulary.csv")
    plot_network(future, vocab)
    plot_matrix(future, vocab)
    print(
        future.head(15)[
            [
                "graph_rank_2027",
                "concept_u",
                "concept_v",
                "annual_graph_score",
                "calibrated_annual_probability",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
