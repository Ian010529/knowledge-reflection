from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.utils.class_weight import compute_sample_weight

import minimal_clean_ite_to_tg_prediction as pipeline


ROOT = Path("/Users/ryan/Documents/iTE&TG")
BASE = ROOT / "minimal_clean_predictions" / "ite_to_tg"
OUT = BASE / "catboost_graph_hybrid"
OUT.mkdir(exist_ok=True)
FEATURES = pipeline.FEATURES
GRAPH_COMPONENTS = [
    "adamic_adar",
    "common_neighbors",
    "jaccard",
    "preferential_attachment",
    "shortest_path",
    "semantic_similarity",
    "recent_frequency_sum",
]


def graph_rank_matrix(frame: pd.DataFrame) -> np.ndarray:
    columns = []
    for component in GRAPH_COMPONENTS:
        values = frame[component].to_numpy()
        if component == "shortest_path":
            values = -values
        columns.append(pipeline.rank_pct(values))
    return np.column_stack(columns)


def metric_row(y: np.ndarray, score: np.ndarray, model: str) -> dict:
    row = {
        "model": model,
        "roc_auc": roc_auc_score(y, score),
        "average_precision": average_precision_score(y, score),
    }
    order = np.argsort(score)[::-1]
    for k in [10, 25, 50, 100]:
        selected = order[:k]
        row[f"precision_at_{k}"] = float(y[selected].mean())
        row[f"hits_at_{k}"] = int(y[selected].sum())
    return row


def catboost_model() -> CatBoostClassifier:
    return CatBoostClassifier(
        iterations=500,
        learning_rate=0.08,
        depth=5,
        l2_leaf_reg=3.0,
        loss_function="Logloss",
        eval_metric="PRAUC",
        verbose=False,
        allow_writing_files=False,
        random_seed=27,
    )


def main() -> None:
    train = pd.read_csv(BASE / "ite_to_tg_train_samples_2013_2019.csv")
    validation = pd.read_csv(
        BASE / "ite_to_tg_validation_candidates_2021_to_2024.csv"
    )
    test = pd.read_csv(BASE / "ite_to_tg_test_candidates_2022_to_2026.csv")
    weights = pd.read_csv(
        BASE / "graph_weight_tuning" / "selected_graph_weights.csv"
    ).set_index("component")["tuned_weight"].reindex(GRAPH_COMPONENTS).to_numpy()

    x_train = train[FEATURES].fillna(0).to_numpy()
    y_train = train.future_edge_label.astype(int).to_numpy()
    x_validation = validation[FEATURES].fillna(0).to_numpy()
    y_validation = validation.future_edge_label.astype(int).to_numpy()
    validation_model = catboost_model()
    validation_model.fit(
        x_train,
        y_train,
        sample_weight=compute_sample_weight("balanced", y_train),
    )
    cat_validation = validation_model.predict_proba(x_validation)[:, 1]
    graph_validation = graph_rank_matrix(validation) @ weights
    cat_validation_rank = pipeline.rank_pct(cat_validation)
    graph_validation_rank = pipeline.rank_pct(graph_validation)

    search_rows = []
    for cat_weight in np.linspace(0, 1, 101):
        hybrid = cat_weight * cat_validation_rank + (
            1 - cat_weight
        ) * graph_validation_rank
        row = metric_row(
            y_validation, hybrid, f"CatBoost weight={cat_weight:.2f}"
        )
        row["catboost_weight"] = cat_weight
        row["graph_weight"] = 1 - cat_weight
        search_rows.append(row)
    search = pd.DataFrame(search_rows).sort_values(
        ["average_precision", "precision_at_25", "precision_at_50"],
        ascending=False,
    )
    best_cat_weight = float(search.iloc[0].catboost_weight)

    combined = pd.concat(
        [train, pipeline.sample_training(validation)], ignore_index=True
    )
    x_combined = combined[FEATURES].fillna(0).to_numpy()
    y_combined = combined.future_edge_label.astype(int).to_numpy()
    x_test = test[FEATURES].fillna(0).to_numpy()
    final_model = catboost_model()
    final_model.fit(
        x_combined,
        y_combined,
        sample_weight=compute_sample_weight("balanced", y_combined),
    )
    cat_test = final_model.predict_proba(x_test)[:, 1]
    graph_test = graph_rank_matrix(test) @ weights
    cat_test_rank = pipeline.rank_pct(cat_test)
    graph_test_rank = pipeline.rank_pct(graph_test)
    hybrid_test = best_cat_weight * cat_test_rank + (
        1 - best_cat_weight
    ) * graph_test_rank
    y_test = test.future_edge_label.astype(int).to_numpy()

    comparison = pd.DataFrame(
        [
            metric_row(y_test, cat_test, "CatBoost"),
            metric_row(y_test, graph_test, "Tuned Graph"),
            metric_row(y_test, hybrid_test, "CatBoost + Tuned Graph"),
        ]
    )
    scored = test[
        ["concept_u_id", "concept_v_id", "concept_u", "concept_v", "future_edge_label"]
    ].copy()
    scored["catboost_probability"] = cat_test
    scored["catboost_rank_score"] = cat_test_rank
    scored["tuned_graph_rank_score"] = graph_test_rank
    scored["hybrid_score"] = hybrid_test
    scored = scored.sort_values("hybrid_score", ascending=False).reset_index(drop=True)
    scored["hybrid_rank"] = np.arange(1, len(scored) + 1)

    search.to_csv(OUT / "hybrid_weight_validation_search.csv", index=False)
    comparison.to_csv(OUT / "hybrid_test_comparison.csv", index=False)
    scored.to_csv(OUT / "hybrid_test_candidate_scores.csv", index=False)
    scored.head(100).to_csv(OUT / "hybrid_top100.csv", index=False)
    print(
        f"Selected CatBoost weight={best_cat_weight:.2f}, "
        f"Graph weight={1-best_cat_weight:.2f}"
    )
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
