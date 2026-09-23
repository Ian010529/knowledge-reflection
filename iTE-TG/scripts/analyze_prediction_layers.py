from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = ROOT / "layered_prediction_analysis"
OUT.mkdir(exist_ok=True)

MATERIAL_TYPES = {"material_entity", "material_system"}
PHYSICOCHEMICAL_TYPES = {
    "transport_mechanism",
    "solvation_entropy",
    "phase_or_species_transition",
    "redox_chemistry",
    "solid_state_mechanism",
}

STRUCTURE_CONCEPTS = {
    "carbon-electrode redox interface",
    "hexacyanoferrate redox electrode",
    "porous-electrode area enhancement",
    "hierarchical porous electrode interface",
    "biomass-derived porous carbon electrode",
    "carbon electrode",
    "metal-oxide nanostructured electrode",
    "porous/pin-electrode thermal-gradient architecture",
    "anti-freezing organohydrogel design",
    "cellulose nanofiber scaffold",
    "dynamic crosslinked gel network",
    "double/interpenetrating network",
    "salting-out confined ion gel",
    "double-network hydrogel",
    "double-network hydrogel mechanics",
    "interpenetrating-network thermogalvanic hydrogel",
    "dynamic crosslinking",
    "oriented ion-transport channels",
    "water-state regulated MXene hydrogel",
}

LAYER_ORDER = ["M-M", "M-S", "M-P", "S-S", "S-P", "P-P", "other"]
LAYER_NAMES = {
    "M-M": "material-material",
    "M-S": "material-structure",
    "M-P": "material-physicochemical mechanism",
    "S-S": "structure-structure",
    "S-P": "structure-physicochemical mechanism",
    "P-P": "physicochemical mechanism-physicochemical mechanism",
    "other": "device/other",
}


def node_layer(label: str, concept_type: str) -> str:
    if concept_type in MATERIAL_TYPES:
        return "M"
    if label in STRUCTURE_CONCEPTS:
        return "S"
    if concept_type in PHYSICOCHEMICAL_TYPES:
        return "P"
    if concept_type == "electrode_interface":
        return "P"
    if concept_type == "gel_microstructure":
        return "P"
    return "O"


def pair_layer(row: pd.Series) -> str:
    left = node_layer(row["concept_u"], row["u_type"])
    right = node_layer(row["concept_v"], row["v_type"])
    order = {"M": 0, "S": 1, "P": 2, "O": 3}
    pair = "-".join(sorted((left, right), key=order.get))
    return pair if pair in LAYER_ORDER else "other"


def precision_at(y: np.ndarray, score: np.ndarray, k: int) -> float:
    selected = np.argsort(score)[::-1][: min(k, len(score))]
    return float(y[selected].mean()) if len(selected) else np.nan


def metric_rows(frame: pd.DataFrame, task: str) -> list[dict]:
    rows = []
    for layer in LAYER_ORDER:
        subset = frame[frame["pair_layer"] == layer]
        if subset.empty:
            continue
        y = subset["future_edge_label"].astype(int).to_numpy()
        for model, column in [
            ("ML", "ml_score"),
            ("Graph", "graph_score"),
            ("Hybrid", "hybrid_score"),
        ]:
            score = subset[column].to_numpy()
            rows.append(
                {
                    "task": task,
                    "pair_layer": layer,
                    "pair_layer_name": LAYER_NAMES[layer],
                    "model": model,
                    "candidates": len(subset),
                    "positives": int(y.sum()),
                    "positive_rate": float(y.mean()),
                    "roc_auc": (
                        roc_auc_score(y, score)
                        if len(np.unique(y)) == 2
                        else np.nan
                    ),
                    "average_precision": (
                        average_precision_score(y, score)
                        if y.sum() > 0
                        else np.nan
                    ),
                    "precision_at_10": precision_at(y, score, 10),
                    "precision_at_25": precision_at(y, score, 25),
                    "precision_at_50": precision_at(y, score, 50),
                }
            )
    return rows


def export_task(
    task: str,
    source: Path,
    output_name: str,
    primary_score: str,
    top_k: int = 25,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_csv(source)
    frame["concept_u_layer"] = [
        node_layer(label, kind)
        for label, kind in zip(frame["concept_u"], frame["u_type"])
    ]
    frame["concept_v_layer"] = [
        node_layer(label, kind)
        for label, kind in zip(frame["concept_v"], frame["v_type"])
    ]
    frame["pair_layer"] = frame.apply(pair_layer, axis=1)
    frame["pair_layer_name"] = frame["pair_layer"].map(LAYER_NAMES)
    task_out = OUT / output_name
    task_out.mkdir(exist_ok=True)
    frame.to_csv(task_out / "all_candidates_with_layers.csv", index=False)

    top_frames = []
    recommendation_frames = []
    for layer in LAYER_ORDER:
        subset = frame[frame["pair_layer"] == layer].sort_values(
            primary_score, ascending=False
        )
        if subset.empty:
            continue
        top = subset.head(top_k).copy()
        top.insert(0, "layer_rank", range(1, len(top) + 1))
        top.to_csv(task_out / f"top{top_k}_{layer}.csv", index=False)
        top_frames.append(top.assign(task=task))

        recommendations = subset[subset["future_edge_label"] == 0].head(top_k).copy()
        recommendations.insert(
            0, "layer_recommendation_rank", range(1, len(recommendations) + 1)
        )
        recommendations.to_csv(
            task_out / f"top{top_k}_unobserved_{layer}.csv", index=False
        )
        recommendation_frames.append(recommendations.assign(task=task))

    metrics = pd.DataFrame(metric_rows(frame, task))
    metrics.to_csv(task_out / "layer_metrics_all_models.csv", index=False)
    pd.concat(top_frames, ignore_index=True).to_csv(
        task_out / f"top{top_k}_all_layers.csv", index=False
    )
    pd.concat(recommendation_frames, ignore_index=True).to_csv(
        task_out / f"top{top_k}_unobserved_all_layers.csv", index=False
    )
    return metrics, frame


def main() -> None:
    ite_metrics, ite_frame = export_task(
        "iTE-to-TG",
        ROOT
        / "ite_to_tg_prediction"
        / "ite_to_tg_scored_candidates_2022_to_2026.csv",
        "ite_to_tg",
        "hybrid_score",
    )
    tg_metrics, tg_frame = export_task(
        "TG-to-TG",
        ROOT / "tg_self_prediction" / "tg_self_scored_candidates_2022_to_2026.csv",
        "tg_to_tg",
        "graph_score",
    )
    metrics = pd.concat([ite_metrics, tg_metrics], ignore_index=True)
    metrics.to_csv(OUT / "all_layer_metrics.csv", index=False)

    node_rows = []
    for task, frame in [("iTE-to-TG", ite_frame), ("TG-to-TG", tg_frame)]:
        for side in ["u", "v"]:
            part = frame[
                [f"concept_{side}", f"{side}_type", f"concept_{side}_layer"]
            ].drop_duplicates()
            part.columns = ["concept", "concept_type", "analysis_layer"]
            part["task"] = task
            node_rows.append(part)
    pd.concat(node_rows, ignore_index=True).drop_duplicates().sort_values(
        ["task", "analysis_layer", "concept"]
    ).to_csv(OUT / "concept_layer_audit.csv", index=False)

    print(
        metrics[
            [
                "task",
                "pair_layer",
                "model",
                "candidates",
                "positives",
                "average_precision",
                "precision_at_10",
                "precision_at_25",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
