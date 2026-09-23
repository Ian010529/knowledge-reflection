from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = ROOT / "minimal_clean_predictions" / "layered_analysis"
OUT.mkdir(exist_ok=True)

MATERIAL_TYPES = {"material_entity", "material_system"}
MECHANISM_TYPES = {
    "transport_mechanism",
    "solvation_entropy",
    "gel_microstructure",
    "phase_or_species_transition",
    "electrode_interface",
    "redox_chemistry",
    "solid_state_mechanism",
    "device_mechanism",
}
LAYERS = ["M-M", "M-X", "X-X"]
LAYER_NAMES = {
    "M-M": "material-material",
    "M-X": "material-mechanism",
    "X-X": "mechanism-mechanism",
}


def pair_layer(row: pd.Series) -> str:
    u_material = row["u_type"] in MATERIAL_TYPES
    v_material = row["v_type"] in MATERIAL_TYPES
    if u_material and v_material:
        return "M-M"
    if u_material or v_material:
        return "M-X"
    return "X-X"


def precision_at(y: np.ndarray, score: np.ndarray, k: int) -> float:
    selected = np.argsort(score)[::-1][: min(k, len(score))]
    return float(y[selected].mean())


def analyze(
    task: str, source: Path, folder: str, primary_score: str, top_k: int = 25
) -> pd.DataFrame:
    frame = pd.read_csv(source)
    frame["pair_layer"] = frame.apply(pair_layer, axis=1)
    frame["pair_layer_name"] = frame["pair_layer"].map(LAYER_NAMES)
    task_out = OUT / folder
    task_out.mkdir(exist_ok=True)
    frame.to_csv(task_out / "all_candidates_three_layers.csv", index=False)

    metric_rows = []
    top_rows = []
    unobserved_rows = []
    for layer in LAYERS:
        subset = frame[frame["pair_layer"] == layer]
        y = subset["future_edge_label"].astype(int).to_numpy()
        for model, score_column in [
            ("ML", "ml_score"),
            ("Graph", "graph_score"),
            ("Hybrid", "hybrid_score"),
        ]:
            score = subset[score_column].to_numpy()
            metric_rows.append(
                {
                    "task": task,
                    "pair_layer": layer,
                    "pair_layer_name": LAYER_NAMES[layer],
                    "model": model,
                    "candidates": len(subset),
                    "positives": int(y.sum()),
                    "positive_rate": float(y.mean()),
                    "roc_auc": roc_auc_score(y, score),
                    "average_precision": average_precision_score(y, score),
                    "precision_at_10": precision_at(y, score, 10),
                    "precision_at_25": precision_at(y, score, 25),
                    "precision_at_50": precision_at(y, score, 50),
                }
            )

        ranked = subset.sort_values(primary_score, ascending=False)
        top = ranked.head(top_k).copy()
        top.insert(0, "layer_rank", range(1, len(top) + 1))
        top.to_csv(task_out / f"top{top_k}_{layer}.csv", index=False)
        top_rows.append(top)

        unobserved = ranked[ranked["future_edge_label"] == 0].head(top_k).copy()
        unobserved.insert(
            0, "layer_recommendation_rank", range(1, len(unobserved) + 1)
        )
        unobserved.to_csv(
            task_out / f"top{top_k}_unobserved_{layer}.csv", index=False
        )
        unobserved_rows.append(unobserved)

    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(task_out / "three_layer_metrics_all_models.csv", index=False)
    pd.concat(top_rows, ignore_index=True).to_csv(
        task_out / f"top{top_k}_all_three_layers.csv", index=False
    )
    pd.concat(unobserved_rows, ignore_index=True).to_csv(
        task_out / f"top{top_k}_unobserved_all_three_layers.csv", index=False
    )
    return metrics


def main() -> None:
    ite = analyze(
        "iTE-to-TG",
        ROOT
        / "minimal_clean_predictions"
        / "ite_to_tg"
        / "ite_to_tg_scored_candidates_2022_to_2026.csv",
        "ite_to_tg",
        "hybrid_score",
    )
    tg = analyze(
        "TG-to-TG",
        ROOT
        / "minimal_clean_predictions"
        / "tg_to_tg"
        / "tg_self_scored_candidates_2022_to_2026.csv",
        "tg_to_tg",
        "graph_score",
    )
    pd.concat([ite, tg], ignore_index=True).to_csv(
        OUT / "all_three_layer_metrics.csv", index=False
    )


if __name__ == "__main__":
    main()
