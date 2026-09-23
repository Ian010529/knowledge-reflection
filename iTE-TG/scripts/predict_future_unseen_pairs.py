from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import minimal_clean_ite_to_tg_prediction as ite
import minimal_clean_tg_to_tg_prediction as tg


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = ROOT / "minimal_clean_predictions" / "future_unseen"
OUT.mkdir(parents=True, exist_ok=True)


def score_future(
    train: pd.DataFrame,
    future: pd.DataFrame,
    features: list[str],
    c_value: float,
    rf_params: dict,
    rf_weight: float,
    hybrid_ml_weight: float,
    graph_fn,
) -> pd.DataFrame:
    x_train = train[features].fillna(0).to_numpy()
    y_train = train["future_edge_label"].astype(int).to_numpy()
    x_future = future[features].fillna(0).to_numpy()

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_future_scaled = scaler.transform(x_future)
    lr = LogisticRegression(
        C=c_value,
        max_iter=4000,
        class_weight="balanced",
        random_state=27,
    ).fit(x_train_scaled, y_train)
    rf = RandomForestClassifier(
        n_estimators=1000,
        class_weight="balanced_subsample",
        random_state=27,
        n_jobs=-1,
        **rf_params,
    ).fit(x_train, y_train)

    logistic = lr.predict_proba(x_future_scaled)[:, 1]
    forest = rf.predict_proba(x_future)[:, 1]
    graph = graph_fn(future)
    ml = rf_weight * ite.rank_pct(forest) + (1 - rf_weight) * ite.rank_pct(logistic)
    hybrid = hybrid_ml_weight * ite.rank_pct(ml) + (
        1 - hybrid_ml_weight
    ) * ite.rank_pct(graph)

    scored = future.copy()
    scored["logistic_probability"] = logistic
    scored["random_forest_probability"] = forest
    scored["ml_rank_score"] = ml
    scored["graph_rank_score"] = graph
    scored["hybrid_rank_score"] = hybrid
    scored["candidate_status"] = "future_unobserved_candidate"
    return scored


def add_ranks(frame: pd.DataFrame, primary: str) -> pd.DataFrame:
    ranked = frame.sort_values(primary, ascending=False).reset_index(drop=True)
    ranked["primary_model"] = primary.replace("_rank_score", "")
    ranked["future_rank"] = np.arange(1, len(ranked) + 1)
    return ranked


def export_layers(frame: pd.DataFrame, prefix: str) -> None:
    frame.to_csv(OUT / f"{prefix}_all_unseen_pairs.csv", index=False)
    frame.head(100).to_csv(OUT / f"{prefix}_top100_all.csv", index=False)
    material = {"material_entity", "material_system"}
    mechanism = ite.MECHANISM_TYPES
    masks = {
        "material_material": frame["u_type"].isin(material)
        & frame["v_type"].isin(material),
        "material_mechanism": (
            frame["u_type"].isin(material) & frame["v_type"].isin(mechanism)
        )
        | (frame["v_type"].isin(material) & frame["u_type"].isin(mechanism)),
        "mechanism_mechanism": frame["u_type"].isin(mechanism)
        & frame["v_type"].isin(mechanism),
    }
    for name, mask in masks.items():
        frame[mask].head(100).to_csv(
            OUT / f"{prefix}_top100_{name}.csv", index=False
        )


def main() -> None:
    vocab_i, ite_mapping, tg_mapping, _ = ite.load_data()
    embeddings_i = ite.build_embeddings(vocab_i)
    ite_train = []
    for cutoff in range(2013, 2024):
        candidates = ite.make_candidates(
            ite_mapping, tg_mapping, vocab_i, embeddings_i, cutoff, cutoff + 3
        )
        if not candidates.empty and candidates["future_edge_label"].sum():
            ite_train.append(ite.sample_training(candidates))
    ite_training = pd.concat(ite_train, ignore_index=True)
    ite_future = ite.make_candidates(
        ite_mapping, tg_mapping, vocab_i, embeddings_i, 2026, 2029
    )
    ite_scored = score_future(
        ite_training,
        ite_future,
        ite.FEATURES,
        c_value=3.0,
        rf_params={
            "max_depth": None,
            "min_samples_leaf": 5,
            "max_features": "sqrt",
        },
        rf_weight=0.8,
        hybrid_ml_weight=0.9,
        graph_fn=ite.graph_score,
    )
    ite_ranked = add_ranks(ite_scored, "hybrid_rank_score")
    export_layers(ite_ranked, "ite_to_tg_future")

    vocab_t, tg_only_mapping, _ = tg.load_data()
    embeddings_t = tg.build_embeddings(vocab_t)
    tg_train = []
    for cutoff in range(2012, 2024):
        candidates = tg.make_candidates(
            tg_only_mapping, vocab_t, embeddings_t, cutoff, cutoff + 3
        )
        if not candidates.empty and candidates["future_edge_label"].sum():
            tg_train.append(tg.sample_training(candidates))
    tg_training = pd.concat(tg_train, ignore_index=True)
    tg_future = tg.make_candidates(
        tg_only_mapping, vocab_t, embeddings_t, 2026, 2029
    )
    tg_scored = score_future(
        tg_training,
        tg_future,
        tg.FEATURES,
        c_value=0.03,
        rf_params={
            "max_depth": 16,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
        },
        rf_weight=0.9,
        hybrid_ml_weight=0.75,
        graph_fn=tg.graph_score,
    )
    tg_ranked = add_ranks(tg_scored, "graph_rank_score")
    export_layers(tg_ranked, "tg_to_tg_future")

    summary = pd.DataFrame(
        [
            {
                "task": "iTE_to_TG",
                "training_samples": len(ite_training),
                "training_positives": int(ite_training.future_edge_label.sum()),
                "future_unseen_candidates": len(ite_ranked),
                "ranking_model": "Hybrid",
                "all_data_cutoff": 2026,
            },
            {
                "task": "TG_to_TG",
                "training_samples": len(tg_training),
                "training_positives": int(tg_training.future_edge_label.sum()),
                "future_unseen_candidates": len(tg_ranked),
                "ranking_model": "Graph",
                "all_data_cutoff": 2026,
            },
        ]
    )
    summary.to_csv(OUT / "future_prediction_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
