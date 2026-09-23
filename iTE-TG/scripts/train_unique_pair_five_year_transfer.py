from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.utils.class_weight import compute_sample_weight

import minimal_clean_ite_to_tg_prediction as base


ROOT = Path("/Users/ryan/Documents/iTE&TG")
DATA = ROOT / "minimal_clean_concept_layer"
FLOW = ROOT / "mechanism_transfer_workflow"
OUT = FLOW / "unique_pair_five_year_model"
OUT.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 27


def metrics(y: np.ndarray, score: np.ndarray, name: str) -> dict:
    result = {
        "model": name,
        "roc_auc": roc_auc_score(y, score),
        "average_precision": average_precision_score(y, score),
        "candidates": len(y),
        "positives": int(y.sum()),
    }
    order = np.argsort(score)[::-1]
    for k in [5, 10, 25, 50]:
        selected = order[: min(k, len(order))]
        result[f"precision_at_{k}"] = float(y[selected].mean())
        result[f"hits_at_{k}"] = int(y[selected].sum())
    return result


def model(params: dict) -> CatBoostClassifier:
    return CatBoostClassifier(
        **params,
        loss_function="Logloss",
        eval_metric="PRAUC",
        verbose=False,
        allow_writing_files=False,
        random_seed=RANDOM_STATE,
    )


def main() -> None:
    vocab = pd.read_csv(FLOW / "pure_mechanism_vocabulary.csv")
    events = pd.read_csv(FLOW / "mechanism_pair_transfer_events.csv")
    mapping = pd.read_csv(DATA / "final_paper_concept_map.csv")
    papers = pd.read_csv(DATA / "final_paper_index.csv")
    papers["year"] = pd.to_numeric(papers.year, errors="coerce")
    pure_ids = set(vocab.concept_id)
    mapping = mapping[mapping.concept_id.isin(pure_ids)].merge(
        papers[["paper_id", "year", "source_membership"]],
        on="paper_id",
        how="left",
    )
    ite_mapping = mapping[
        mapping.source_membership.str.contains("iTE", na=False)
    ].copy()
    tg_mapping = mapping[
        mapping.source_membership.str.contains("TG", na=False)
    ].copy()
    embeddings = base.build_embeddings(vocab)

    eligible_events = events[
        events.ite_first_year.notna()
        & (
            events.tg_first_year.isna()
            | (events.tg_first_year > events.ite_first_year)
        )
        & (events.ite_first_year <= 2021)
    ].copy()
    rows = []
    cache = {}
    for event in eligible_events.itertuples(index=False):
        cutoff = int(event.ite_first_year)
        if cutoff not in cache:
            candidates = base.make_candidates(
                ite_mapping,
                tg_mapping,
                vocab,
                embeddings,
                cutoff,
                cutoff + 5,
            )
            cache[cutoff] = (
                candidates.set_index(["concept_u_id", "concept_v_id"])
                if not candidates.empty
                else None
            )
        key = tuple(sorted((event.concept_u_id, event.concept_v_id)))
        candidate_table = cache[cutoff]
        if candidate_table is None:
            continue
        if key not in candidate_table.index:
            continue
        feature = candidate_table.loc[key]
        if isinstance(feature, pd.DataFrame):
            feature = feature.iloc[0]
        row = feature.to_dict()
        row["concept_u_id"], row["concept_v_id"] = key
        row["ite_first_year"] = cutoff
        row["tg_first_year"] = event.tg_first_year
        row["transfer_lag_years"] = event.transfer_lag_years
        row["label"] = int(
            pd.notna(event.tg_first_year)
            and 0 < event.tg_first_year - cutoff <= 5
        )
        rows.append(row)
    dataset = pd.DataFrame(rows)

    # The split is by iTE emergence cohort; each pair occurs exactly once.
    train = dataset[dataset.ite_first_year <= 2019].copy()
    validation = dataset[dataset.ite_first_year.eq(2020)].copy()
    test = dataset[dataset.ite_first_year.eq(2021)].copy()
    x_train = train[base.FEATURES].fillna(0).to_numpy()
    y_train = train.label.astype(int).to_numpy()
    x_validation = validation[base.FEATURES].fillna(0).to_numpy()
    y_validation = validation.label.astype(int).to_numpy()
    tuning_rows = []
    best_params = None
    best_ap = -1.0
    for iterations, rate, depth, l2 in product(
        [100, 250, 500], [0.03, 0.08], [2, 3, 5], [3.0, 10.0]
    ):
        params = {
            "iterations": iterations,
            "learning_rate": rate,
            "depth": depth,
            "l2_leaf_reg": l2,
        }
        candidate = model(params)
        candidate.fit(
            x_train,
            y_train,
            sample_weight=compute_sample_weight("balanced", y_train),
        )
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

    combined = pd.concat([train, validation], ignore_index=True)
    final = model(best_params)
    final.fit(
        combined[base.FEATURES].fillna(0).to_numpy(),
        combined.label.astype(int).to_numpy(),
        sample_weight=compute_sample_weight(
            "balanced", combined.label.astype(int).to_numpy()
        ),
    )
    test_score = final.predict_proba(
        test[base.FEATURES].fillna(0).to_numpy()
    )[:, 1]
    graph = base.graph_score(test)
    comparison = pd.DataFrame(
        [
            metrics(test.label.astype(int).to_numpy(), test_score, "CatBoost"),
            metrics(test.label.astype(int).to_numpy(), graph, "Graph"),
        ]
    )
    scored = test.copy()
    scored["catboost_probability"] = test_score
    scored["graph_score"] = graph
    scored = scored.sort_values(
        "catboost_probability", ascending=False
    ).reset_index(drop=True)
    scored["rank"] = np.arange(1, len(scored) + 1)

    dataset.to_csv(OUT / "unique_pair_dataset.csv", index=False)
    pd.DataFrame(tuning_rows).sort_values(
        "validation_ap", ascending=False
    ).to_csv(OUT / "catboost_tuning.csv", index=False)
    comparison.to_csv(OUT / "test_metrics.csv", index=False)
    scored.to_csv(OUT / "test_scores.csv", index=False)
    print(
        "dataset",
        len(dataset),
        "positive",
        int(dataset.label.sum()),
    )
    print(
        "train",
        len(train),
        int(train.label.sum()),
        "validation",
        len(validation),
        int(validation.label.sum()),
        "test",
        len(test),
        int(test.label.sum()),
    )
    print("best", best_params)
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
