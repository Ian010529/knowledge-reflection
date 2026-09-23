from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.utils.class_weight import compute_sample_weight

import minimal_clean_ite_to_tg_prediction as pipeline


ROOT = Path("/Users/ryan/Documents/iTE&TG")
DATA = ROOT / "minimal_clean_predictions" / "ite_to_tg"
OUT = DATA / "single_model_comparison"
OUT.mkdir(exist_ok=True)
FEATURES = pipeline.FEATURES
RANDOM_STATE = 27


def grids() -> dict[str, list[dict]]:
    return {
        "Logistic Regression": [
            {"C": c} for c in [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]
        ],
        "Random Forest": [
            {
                "max_depth": depth,
                "min_samples_leaf": leaf,
                "max_features": features,
            }
            for depth, leaf, features in product(
                [None, 10, 16, 24], [2, 5, 10], ["sqrt", 0.7]
            )
        ],
        "Extra Trees": [
            {
                "max_depth": depth,
                "min_samples_leaf": leaf,
                "max_features": features,
            }
            for depth, leaf, features in product(
                [None, 10, 16, 24], [2, 5, 10], ["sqrt", 0.7]
            )
        ],
        "Gradient Boosting": [
            {
                "n_estimators": n,
                "learning_rate": rate,
                "max_depth": depth,
                "min_samples_leaf": leaf,
            }
            for n, rate, depth, leaf in product(
                [100, 250], [0.03, 0.08], [2, 3], [5, 10]
            )
        ],
        "Histogram Gradient Boosting": [
            {
                "learning_rate": rate,
                "max_iter": iterations,
                "max_leaf_nodes": leaves,
                "l2_regularization": l2,
            }
            for rate, iterations, leaves, l2 in product(
                [0.03, 0.08], [150, 300], [7, 15], [0.0, 1.0]
            )
        ],
        "RBF-SVM": [
            {"C": c, "gamma": gamma}
            for c, gamma in product([0.1, 1.0, 10.0], ["scale", 0.01, 0.1])
        ],
        "MLP": [
            {
                "hidden_layer_sizes": hidden,
                "alpha": alpha,
                "learning_rate_init": rate,
            }
            for hidden, alpha, rate in product(
                [(32,), (64,), (64, 32), (128, 64, 32)],
                [0.0001, 0.01],
                [0.001, 0.003],
            )
        ],
        "XGBoost": [
            {
                "n_estimators": n,
                "learning_rate": rate,
                "max_depth": depth,
                "min_child_weight": child,
            }
            for n, rate, depth, child in product(
                [200, 500], [0.03, 0.08], [2, 4], [1, 5]
            )
        ],
        "LightGBM": [
            {
                "n_estimators": n,
                "learning_rate": rate,
                "num_leaves": leaves,
                "min_child_samples": child,
            }
            for n, rate, leaves, child in product(
                [200, 500], [0.03, 0.08], [7, 15], [10, 25]
            )
        ],
        "CatBoost": [
            {
                "iterations": n,
                "learning_rate": rate,
                "depth": depth,
                "l2_leaf_reg": l2,
            }
            for n, rate, depth, l2 in product(
                [250, 500], [0.03, 0.08], [3, 5], [3.0, 10.0]
            )
        ],
    }


def make_model(name: str, params: dict):
    if name == "Logistic Regression":
        return LogisticRegression(
            **params,
            max_iter=5000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        )
    if name == "Random Forest":
        return RandomForestClassifier(
            **params,
            n_estimators=600,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
    if name == "Extra Trees":
        return ExtraTreesClassifier(
            **params,
            n_estimators=600,
            class_weight="balanced",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
    if name == "Gradient Boosting":
        return GradientBoostingClassifier(**params, random_state=RANDOM_STATE)
    if name == "Histogram Gradient Boosting":
        return HistGradientBoostingClassifier(
            **params, max_depth=None, random_state=RANDOM_STATE
        )
    if name == "RBF-SVM":
        return SVC(
            **params,
            probability=True,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        )
    if name == "MLP":
        return MLPClassifier(
            **params,
            max_iter=1500,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=RANDOM_STATE,
        )
    if name == "XGBoost":
        return XGBClassifier(
            **params,
            objective="binary:logistic",
            eval_metric="aucpr",
            subsample=0.85,
            colsample_bytree=0.85,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
    if name == "LightGBM":
        return LGBMClassifier(
            **params,
            objective="binary",
            subsample=0.85,
            colsample_bytree=0.85,
            verbosity=-1,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
    if name == "CatBoost":
        return CatBoostClassifier(
            **params,
            loss_function="Logloss",
            eval_metric="PRAUC",
            verbose=False,
            allow_writing_files=False,
            random_seed=RANDOM_STATE,
        )
    raise ValueError(name)


def needs_scaling(name: str) -> bool:
    return name in {"Logistic Regression", "RBF-SVM", "MLP"}


def fit(model, name: str, x: np.ndarray, y: np.ndarray) -> None:
    if name in {
        "Gradient Boosting",
        "Histogram Gradient Boosting",
        "MLP",
        "XGBoost",
        "LightGBM",
        "CatBoost",
    }:
        model.fit(x, y, sample_weight=compute_sample_weight("balanced", y))
    else:
        model.fit(x, y)


def scores(model, x: np.ndarray) -> np.ndarray:
    return model.predict_proba(x)[:, 1]


def metrics(y: np.ndarray, score: np.ndarray) -> dict:
    result = {
        "roc_auc": roc_auc_score(y, score),
        "average_precision": average_precision_score(y, score),
    }
    order = np.argsort(score)[::-1]
    for k in [10, 25, 50, 100]:
        selected = order[:k]
        result[f"precision_at_{k}"] = float(y[selected].mean())
        result[f"hits_at_{k}"] = int(y[selected].sum())
    return result


def main() -> None:
    train = pd.read_csv(DATA / "ite_to_tg_train_samples_2013_2019.csv")
    validation = pd.read_csv(
        DATA / "ite_to_tg_validation_candidates_2021_to_2024.csv"
    )
    test = pd.read_csv(DATA / "ite_to_tg_test_candidates_2022_to_2026.csv")
    x_train = train[FEATURES].fillna(0).to_numpy()
    y_train = train.future_edge_label.astype(int).to_numpy()
    x_validation = validation[FEATURES].fillna(0).to_numpy()
    y_validation = validation.future_edge_label.astype(int).to_numpy()
    tuning_rows = []
    best = {}

    for name, configurations in grids().items():
        scaler = StandardScaler() if needs_scaling(name) else None
        train_x = scaler.fit_transform(x_train) if scaler else x_train
        validation_x = scaler.transform(x_validation) if scaler else x_validation
        best_ap = -1.0
        for params in configurations:
            model = make_model(name, params)
            fit(model, name, train_x, y_train)
            score = scores(model, validation_x)
            ap = average_precision_score(y_validation, score)
            tuning_rows.append(
                {
                    "model": name,
                    "params": json.dumps(params),
                    "validation_ap": ap,
                    "validation_auc": roc_auc_score(y_validation, score),
                }
            )
            if ap > best_ap:
                best_ap = ap
                best[name] = params

    combined = pd.concat(
        [train, pipeline.sample_training(validation)], ignore_index=True
    )
    x_combined = combined[FEATURES].fillna(0).to_numpy()
    y_combined = combined.future_edge_label.astype(int).to_numpy()
    x_test = test[FEATURES].fillna(0).to_numpy()
    y_test = test.future_edge_label.astype(int).to_numpy()
    result_rows = []
    scored = test[
        ["concept_u_id", "concept_v_id", "concept_u", "concept_v", "future_edge_label"]
    ].copy()
    for name, params in best.items():
        scaler = StandardScaler() if needs_scaling(name) else None
        combined_x = scaler.fit_transform(x_combined) if scaler else x_combined
        test_x = scaler.transform(x_test) if scaler else x_test
        model = make_model(name, params)
        fit(model, name, combined_x, y_combined)
        score = scores(model, test_x)
        row = {"model": name, "best_params": json.dumps(params)}
        row.update(metrics(y_test, score))
        result_rows.append(row)
        scored[name] = score

    results = pd.DataFrame(result_rows).sort_values(
        ["average_precision", "precision_at_25"], ascending=False
    )
    tuning = pd.DataFrame(tuning_rows)
    tuning.to_csv(OUT / "single_model_hyperparameter_search.csv", index=False)
    results.to_csv(OUT / "single_model_test_comparison.csv", index=False)
    scored.to_csv(OUT / "single_model_test_scores.csv", index=False)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
