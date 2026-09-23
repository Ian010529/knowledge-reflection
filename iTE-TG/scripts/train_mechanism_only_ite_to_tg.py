from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.utils.class_weight import compute_sample_weight

import minimal_clean_ite_to_tg_prediction as pipeline


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = ROOT / "minimal_clean_predictions" / "ite_to_tg" / "mechanism_only_model"
OUT.mkdir(parents=True, exist_ok=True)
FEATURES = pipeline.FEATURES
MECHANISMS = pipeline.MECHANISM_TYPES
GRAPH_WEIGHTS = np.array([0.24, 0.18, 0.12, 0.12, 0.12, 0.12, 0.10])
GRAPH_COMPONENTS = [
    "adamic_adar",
    "common_neighbors",
    "jaccard",
    "preferential_attachment",
    "shortest_path",
    "semantic_similarity",
    "recent_frequency_sum",
]


def mechanism_only(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[
        frame.u_type.isin(MECHANISMS) & frame.v_type.isin(MECHANISMS)
    ].copy()


def model(params: dict) -> CatBoostClassifier:
    return CatBoostClassifier(
        **params,
        loss_function="Logloss",
        eval_metric="PRAUC",
        verbose=False,
        allow_writing_files=False,
        random_seed=27,
    )


def fit(model_: CatBoostClassifier, x: np.ndarray, y: np.ndarray) -> None:
    model_.fit(x, y, sample_weight=compute_sample_weight("balanced", y))


def graph_score(frame: pd.DataFrame) -> np.ndarray:
    columns = []
    for component in GRAPH_COMPONENTS:
        values = frame[component].to_numpy()
        if component == "shortest_path":
            values = -values
        columns.append(pipeline.rank_pct(values))
    return np.column_stack(columns) @ GRAPH_WEIGHTS


def metrics(y: np.ndarray, score: np.ndarray, name: str) -> dict:
    row = {
        "model": name,
        "roc_auc": roc_auc_score(y, score),
        "average_precision": average_precision_score(y, score),
    }
    order = np.argsort(score)[::-1]
    for k in [10, 25, 50, 100]:
        selected = order[: min(k, len(order))]
        row[f"precision_at_{k}"] = float(y[selected].mean())
        row[f"hits_at_{k}"] = int(y[selected].sum())
    return row


def main() -> None:
    vocab, ite_mapping, tg_mapping, _ = pipeline.load_data()
    embeddings = pipeline.build_embeddings(vocab)
    training_windows = []
    window_rows = []
    for cutoff in range(2013, 2020):
        full = mechanism_only(
            pipeline.make_candidates(
                ite_mapping, tg_mapping, vocab, embeddings, cutoff, cutoff + 3
            )
        )
        sampled = pipeline.sample_training(full)
        if not sampled.empty:
            training_windows.append(sampled)
        window_rows.append(
            {
                "cutoff": cutoff,
                "candidates": len(full),
                "positives": int(full.future_edge_label.sum()),
                "sampled": len(sampled),
            }
        )
    train = pd.concat(training_windows, ignore_index=True)
    validation = mechanism_only(
        pipeline.make_candidates(
            ite_mapping, tg_mapping, vocab, embeddings, 2021, 2024
        )
    )
    test = mechanism_only(
        pipeline.make_candidates(
            ite_mapping, tg_mapping, vocab, embeddings, 2022, 2026
        )
    )
    x_train = train[FEATURES].fillna(0).to_numpy()
    y_train = train.future_edge_label.astype(int).to_numpy()
    x_validation = validation[FEATURES].fillna(0).to_numpy()
    y_validation = validation.future_edge_label.astype(int).to_numpy()

    tuning_rows = []
    best_params = None
    best_ap = -1.0
    for iterations, rate, depth, l2 in product(
        [250, 500, 800], [0.03, 0.08], [3, 5, 7], [3.0, 10.0]
    ):
        params = {
            "iterations": iterations,
            "learning_rate": rate,
            "depth": depth,
            "l2_leaf_reg": l2,
        }
        candidate = model(params)
        fit(candidate, x_train, y_train)
        score = candidate.predict_proba(x_validation)[:, 1]
        ap = average_precision_score(y_validation, score)
        tuning_rows.append(
            {
                "params": json.dumps(params),
                "validation_ap": ap,
                "validation_auc": roc_auc_score(y_validation, score),
            }
        )
        if ap > best_ap:
            best_ap = ap
            best_params = params

    validation_model = model(best_params)
    fit(validation_model, x_train, y_train)
    cat_validation = pipeline.rank_pct(
        validation_model.predict_proba(x_validation)[:, 1]
    )
    graph_validation = pipeline.rank_pct(graph_score(validation))
    weight_rows = []
    for cat_weight in np.linspace(0, 1, 101):
        score = cat_weight * cat_validation + (
            1 - cat_weight
        ) * graph_validation
        row = metrics(y_validation, score, f"weight={cat_weight:.2f}")
        row["catboost_weight"] = cat_weight
        weight_rows.append(row)
    weight_search = pd.DataFrame(weight_rows).sort_values(
        ["average_precision", "precision_at_25", "precision_at_50"],
        ascending=False,
    )
    cat_weight = float(weight_search.iloc[0].catboost_weight)

    combined = pd.concat(
        [train, pipeline.sample_training(validation)], ignore_index=True
    )
    x_combined = combined[FEATURES].fillna(0).to_numpy()
    y_combined = combined.future_edge_label.astype(int).to_numpy()
    x_test = test[FEATURES].fillna(0).to_numpy()
    y_test = test.future_edge_label.astype(int).to_numpy()
    final_model = model(best_params)
    fit(final_model, x_combined, y_combined)
    cat_probability = final_model.predict_proba(x_test)[:, 1]
    cat_rank = pipeline.rank_pct(cat_probability)
    graph_rank = pipeline.rank_pct(graph_score(test))
    hybrid = cat_weight * cat_rank + (1 - cat_weight) * graph_rank

    comparison = pd.DataFrame(
        [
            metrics(y_test, cat_probability, "Mechanism-only CatBoost"),
            metrics(y_test, graph_rank, "Mechanism-only original Graph"),
            metrics(y_test, hybrid, "Mechanism-only Hybrid"),
        ]
    )
    scored = test.copy()
    scored["catboost_probability"] = cat_probability
    scored["catboost_rank"] = cat_rank
    scored["graph_rank"] = graph_rank
    scored["hybrid_score"] = hybrid
    scored = scored.sort_values("hybrid_score", ascending=False).reset_index(drop=True)
    scored["mechanism_rank"] = np.arange(1, len(scored) + 1)

    pd.DataFrame(window_rows).to_csv(OUT / "training_windows.csv", index=False)
    pd.DataFrame(tuning_rows).sort_values(
        "validation_ap", ascending=False
    ).to_csv(OUT / "catboost_tuning.csv", index=False)
    weight_search.to_csv(OUT / "hybrid_weight_search.csv", index=False)
    comparison.to_csv(OUT / "test_comparison.csv", index=False)
    scored.to_csv(OUT / "mechanism_candidate_scores.csv", index=False)
    scored.head(100).to_csv(OUT / "mechanism_top100.csv", index=False)
    print("training", len(train), "positives", int(y_train.sum()))
    print("validation", len(validation), "positives", int(y_validation.sum()))
    print("test", len(test), "positives", int(y_test.sum()))
    print("best_params", best_params)
    print("catboost_weight", cat_weight, "graph_weight", 1 - cat_weight)
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
