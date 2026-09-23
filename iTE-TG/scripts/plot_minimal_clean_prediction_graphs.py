from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import numpy as np
import pandas as pd


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = ROOT / "minimal_clean_predictions" / "prediction_graphs"
OUT.mkdir(exist_ok=True)

MATERIAL_TYPES = {"material_entity", "material_system"}
COLORS = {
    "material": "#5B8E7D",
    "mechanism": "#E0A458",
    "observed": "#C94C5C",
    "candidate": "#3E6FA3",
    "neutral": "#D9DEE3",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def save_pub(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def short_label(value: str, length: int = 22) -> str:
    return value if len(value) <= length else value[:length] + "..."


def select_subgraph(
    frame: pd.DataFrame, score_column: str, edge_limit: int = 55, node_limit: int = 30
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranked = frame.sort_values(score_column, ascending=False).head(edge_limit * 3)
    weighted_degree: dict[str, float] = {}
    label_lookup: dict[str, str] = {}
    type_lookup: dict[str, str] = {}
    for row in ranked.itertuples(index=False):
        weighted_degree[row.concept_u_id] = (
            weighted_degree.get(row.concept_u_id, 0) + getattr(row, score_column)
        )
        weighted_degree[row.concept_v_id] = (
            weighted_degree.get(row.concept_v_id, 0) + getattr(row, score_column)
        )
        label_lookup[row.concept_u_id] = row.concept_u
        label_lookup[row.concept_v_id] = row.concept_v
        type_lookup[row.concept_u_id] = row.u_type
        type_lookup[row.concept_v_id] = row.v_type
    selected_nodes = {
        node
        for node, _ in sorted(
            weighted_degree.items(), key=lambda item: item[1], reverse=True
        )[:node_limit]
    }
    edges = ranked[
        ranked["concept_u_id"].isin(selected_nodes)
        & ranked["concept_v_id"].isin(selected_nodes)
    ].head(edge_limit).copy()
    used_nodes = set(edges["concept_u_id"]) | set(edges["concept_v_id"])
    nodes = pd.DataFrame(
        [
            {
                "concept_id": node,
                "concept": label_lookup[node],
                "concept_type": type_lookup[node],
                "display_layer": (
                    "material" if type_lookup[node] in MATERIAL_TYPES else "mechanism"
                ),
                "selected_weighted_degree": weighted_degree[node],
            }
            for node in used_nodes
        ]
    ).sort_values("selected_weighted_degree", ascending=False)
    return edges, nodes


def draw_network(
    frame: pd.DataFrame,
    score_column: str,
    title: str,
    subtitle: str,
    stem: str,
    edge_limit: int = 55,
    node_limit: int = 30,
    label_limit: int = 12,
) -> None:
    edges, nodes = select_subgraph(
        frame, score_column, edge_limit=edge_limit, node_limit=node_limit
    )
    graph = nx.Graph()
    for row in nodes.itertuples(index=False):
        graph.add_node(
            row.concept_id,
            label=row.concept,
            layer=row.display_layer,
            weight=row.selected_weighted_degree,
        )
    for row in edges.itertuples(index=False):
        graph.add_edge(
            row.concept_u_id,
            row.concept_v_id,
            score=getattr(row, score_column),
            observed=int(row.future_edge_label),
        )

    position = nx.spring_layout(
        graph,
        seed=27,
        weight="score",
        k=1.15 / np.sqrt(max(1, graph.number_of_nodes())),
        iterations=500,
    )
    fig, ax = plt.subplots(figsize=(7.2, 5.0), constrained_layout=True)
    ax.set_axis_off()

    for observed, style, color in [
        (0, (0, (3, 2)), COLORS["candidate"]),
        (1, "solid", COLORS["observed"]),
    ]:
        selected = [
            (u, v)
            for u, v, data in graph.edges(data=True)
            if data["observed"] == observed
        ]
        widths = [
            0.5 + 2.2 * graph.edges[edge]["score"] for edge in selected
        ]
        nx.draw_networkx_edges(
            graph,
            position,
            edgelist=selected,
            width=widths,
            edge_color=color,
            style=style,
            alpha=0.72,
            ax=ax,
        )

    node_weights = np.array(
        [graph.nodes[node]["weight"] for node in graph.nodes], dtype=float
    )
    node_sizes = 55 + 180 * (
        node_weights - node_weights.min()
    ) / max(1e-9, node_weights.max() - node_weights.min())
    node_colors = [
        COLORS[graph.nodes[node]["layer"]] for node in graph.nodes
    ]
    nx.draw_networkx_nodes(
        graph,
        position,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="white",
        linewidths=0.7,
        ax=ax,
    )

    label_nodes = nodes.head(label_limit)["concept_id"].tolist()
    labels = {
        node: short_label(graph.nodes[node]["label"]) for node in label_nodes
    }
    nx.draw_networkx_labels(
        graph,
        position,
        labels=labels,
        font_size=5.2,
        font_color="#20252A",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.76, "pad": 0.25},
        ax=ax,
    )

    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["material"], markeredgecolor="white", markersize=7, label="Material"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["mechanism"], markeredgecolor="white", markersize=7, label="Mechanism"),
        Line2D([0], [0], color=COLORS["observed"], lw=2, label="Observed in 2023-2026"),
        Line2D([0], [0], color=COLORS["candidate"], lw=2, linestyle=(0, (3, 2)), label="Not observed in mapped corpus"),
    ]
    ax.legend(
        handles=legend,
        loc="lower left",
        ncol=2,
        fontsize=6,
        frameon=False,
    )
    fig.suptitle(title, x=0.02, y=0.995, ha="left", fontsize=10)
    fig.text(
        0.02,
        0.955,
        subtitle,
        ha="left",
        va="top",
        fontsize=6.5,
        color="#555555",
    )
    save_pub(fig, OUT / stem)
    plt.close(fig)

    edges.to_csv(OUT / f"{stem}_edges.csv", index=False)
    nodes.to_csv(OUT / f"{stem}_nodes.csv", index=False)


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
    draw_network(
        transfer,
        "hybrid_score",
        "iTE-to-TG knowledge-transfer network",
        "Focused subgraph of high-ranked iTE-known links absent from TG through 2022",
        "ite_to_tg_transfer_network",
    )
    draw_network(
        transfer,
        "hybrid_score",
        "iTE-to-TG knowledge-transfer network",
        "Extended view: 80 high-connectivity concepts from ranked transfer candidates",
        "ite_to_tg_transfer_network_extended",
        edge_limit=220,
        node_limit=80,
        label_limit=12,
    )
    draw_network(
        transfer,
        "hybrid_score",
        "iTE-to-TG full candidate network",
        "All 186 eligible concepts; edges show the complete 963-pair candidate universe",
        "ite_to_tg_transfer_network_full",
        edge_limit=963,
        node_limit=186,
        label_limit=10,
    )
    draw_network(
        tg_self,
        "graph_score",
        "TG internal-evolution network",
        "Focused subgraph of high-ranked concept links absent from TG through 2022",
        "tg_to_tg_evolution_network",
    )
    draw_network(
        tg_self,
        "graph_score",
        "TG internal-evolution network",
        "Extended view: all 76 eligible TG concepts and up to 500 ranked links",
        "tg_to_tg_evolution_network_extended",
        edge_limit=500,
        node_limit=76,
        label_limit=12,
    )


if __name__ == "__main__":
    main()
