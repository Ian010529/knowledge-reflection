from __future__ import annotations

import json
from itertools import combinations, product
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.utils.class_weight import compute_sample_weight

import minimal_clean_ite_to_tg_prediction as base


ROOT = Path("/Users/ryan/Documents/iTE&TG")
DATA = ROOT / "minimal_clean_concept_layer"
FLOW = ROOT / "mechanism_transfer_workflow"
OUT = FLOW / "two_stage_model"
OUT.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 27

NODE_FEATURES = [
    "ite_document_frequency",
    "ite_recent_frequency",
    "ite_previous_frequency",
    "ite_trend",
    "ite_age",
    "ite_degree",
    "ite_weighted_degree",
    "tg_neighbor_exposure",
    "tg_neighbor_fraction",
    "semantic_mean_to_tg",
    "semantic_max_to_tg",
]


def fit_cat(params: dict) -> CatBoostClassifier:
    return CatBoostClassifier(
        **params,
        loss_function="Logloss",
        eval_metric="PRAUC",
        verbose=False,
        allow_writing_files=False,
        random_seed=RANDOM_STATE,
    )


def train_model(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    features: list[str],
) -> tuple[dict, pd.DataFrame]:
    x_train = train[features].fillna(0).to_numpy()
    y_train = train.label.astype(int).to_numpy()
    x_val = validation[features].fillna(0).to_numpy()
    y_val = validation.label.astype(int).to_numpy()
    rows = []
    best_params = None
    best_ap = -1.0
    for iterations, rate, depth, l2 in product(
        [250, 500], [0.03, 0.08], [3, 5], [3.0, 10.0]
    ):
        params = {
            "iterations": iterations,
            "learning_rate": rate,
            "depth": depth,
            "l2_leaf_reg": l2,
        }
        model = fit_cat(params)
        model.fit(
            x_train,
            y_train,
            sample_weight=compute_sample_weight("balanced", y_train),
        )
        score = model.predict_proba(x_val)[:, 1]
        ap = average_precision_score(y_val, score)
        rows.append(
            {
                "params": json.dumps(params),
                "validation_ap": ap,
                "validation_auc": roc_auc_score(y_val, score),
            }
        )
        if ap > best_ap:
            best_ap = ap
            best_params = params
    return best_params, pd.DataFrame(rows).sort_values(
        "validation_ap", ascending=False
    )


def metric_row(y: np.ndarray, score: np.ndarray, name: str) -> dict:
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


def first_years(mapping: pd.DataFrame) -> dict[str, int]:
    return (
        mapping.groupby("concept_id").year.min().astype(int).to_dict()
    )


def node_frame(
    cutoff: int,
    vocab: pd.DataFrame,
    ite_mapping: pd.DataFrame,
    tg_mapping: pd.DataFrame,
    embeddings: dict[str, np.ndarray],
) -> pd.DataFrame:
    ite_history = ite_mapping[ite_mapping.year <= cutoff]
    tg_history = tg_mapping[tg_mapping.year <= cutoff]
    ite_counts = ite_history.groupby("concept_id").paper_id.nunique().to_dict()
    recent = (
        ite_history[ite_history.year.between(cutoff - 2, cutoff)]
        .groupby("concept_id").paper_id.nunique().to_dict()
    )
    previous = (
        ite_history[ite_history.year.between(cutoff - 5, cutoff - 3)]
        .groupby("concept_id").paper_id.nunique().to_dict()
    )
    ite_first = first_years(ite_mapping)
    tg_first = first_years(tg_mapping)
    paper_sets = base.paper_concept_sets(ite_history)
    edge_counts: dict[tuple[str, str], int] = {}
    for concepts in paper_sets.values():
        for edge in combinations(sorted(concepts), 2):
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    graph = nx.Graph()
    for (u, v), weight in edge_counts.items():
        graph.add_edge(u, v, weight=weight)
    tg_active = {
        concept for concept, year in tg_first.items() if year <= cutoff
    }
    tg_vectors = (
        np.vstack([embeddings[node] for node in tg_active])
        if tg_active
        else np.empty((0, next(iter(embeddings.values())).shape[0]))
    )
    labels = vocab.set_index("concept_id").canonical_concept.to_dict()
    types = vocab.set_index("concept_id").concept_type.to_dict()
    rows = []
    for node, count in ite_counts.items():
        if count < 2:
            continue
        if node in tg_first and tg_first[node] <= cutoff:
            continue
        neighbors = set(graph.neighbors(node)) if node in graph else set()
        exposed = neighbors & tg_active
        similarities = (
            tg_vectors @ embeddings[node] if len(tg_vectors) else np.array([0.0])
        )
        rows.append(
            {
                "concept_id": node,
                "concept": labels[node],
                "concept_type": types[node],
                "cutoff_year": cutoff,
                "ite_document_frequency": count,
                "ite_recent_frequency": recent.get(node, 0),
                "ite_previous_frequency": previous.get(node, 0),
                "ite_trend": (recent.get(node, 0) - previous.get(node, 0)) / 3,
                "ite_age": cutoff - ite_first[node],
                "ite_degree": len(neighbors),
                "ite_weighted_degree": sum(
                    graph[node][neighbor]["weight"] for neighbor in neighbors
                ),
                "tg_neighbor_exposure": len(exposed),
                "tg_neighbor_fraction": len(exposed) / max(1, len(neighbors)),
                "semantic_mean_to_tg": float(similarities.mean()),
                "semantic_max_to_tg": float(similarities.max()),
                "label": int(tg_first.get(node) == cutoff + 1),
            }
        )
    return pd.DataFrame(rows)


def pair_frame(
    cutoff: int,
    vocab: pd.DataFrame,
    ite_mapping: pd.DataFrame,
    tg_mapping: pd.DataFrame,
    embeddings: dict[str, np.ndarray],
) -> pd.DataFrame:
    frame = base.make_candidates(
        ite_mapping,
        tg_mapping,
        vocab,
        embeddings,
        cutoff,
        cutoff + 1,
    )
    if frame.empty:
        return frame
    return frame.rename(columns={"future_edge_label": "label"})


def annual_frames(
    years: range,
    builder,
    vocab,
    ite_mapping,
    tg_mapping,
    embeddings,
) -> pd.DataFrame:
    frames = []
    for cutoff in years:
        frame = builder(
            cutoff, vocab, ite_mapping, tg_mapping, embeddings
        )
        if not frame.empty:
            frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def sample_pair_years(frame: pd.DataFrame, ratio: int = 15) -> pd.DataFrame:
    sampled = []
    for cutoff, group in frame.groupby("cutoff_year"):
        positives = group[group.label.eq(1)]
        negatives = group[group.label.eq(0)]
        if positives.empty:
            continue
        n = min(len(negatives), ratio * len(positives))
        hard = negatives.assign(_score=base.graph_score(negatives)).nlargest(
            n // 2, "_score"
        )
        remaining = negatives.drop(hard.index)
        random = remaining.sample(
            n=n - len(hard), random_state=RANDOM_STATE + int(cutoff)
        )
        sampled.append(
            pd.concat([positives, hard.drop(columns="_score"), random])
        )
    return pd.concat(sampled, ignore_index=True)


def main() -> None:
    pure_vocab = pd.read_csv(FLOW / "pure_mechanism_vocabulary.csv")
    pure_ids = set(pure_vocab.concept_id)
    mapping = pd.read_csv(DATA / "final_paper_concept_map.csv")
    papers = pd.read_csv(DATA / "final_paper_index.csv")
    papers["year"] = pd.to_numeric(papers.year, errors="coerce")
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
    embeddings = base.build_embeddings(pure_vocab)

    node_all = annual_frames(
        range(2013, 2026),
        node_frame,
        pure_vocab,
        ite_mapping,
        tg_mapping,
        embeddings,
    )
    node_train = node_all[node_all.cutoff_year <= 2023]
    node_validation = node_all[node_all.cutoff_year.eq(2024)]
    node_test = node_all[node_all.cutoff_year.eq(2025)]
    node_params, node_tuning = train_model(
        node_train, node_validation, NODE_FEATURES
    )
    node_combined = pd.concat([node_train, node_validation], ignore_index=True)
    node_model = fit_cat(node_params)
    node_model.fit(
        node_combined[NODE_FEATURES].fillna(0).to_numpy(),
        node_combined.label.astype(int).to_numpy(),
        sample_weight=compute_sample_weight(
            "balanced", node_combined.label.astype(int).to_numpy()
        ),
    )
    node_test_score = node_model.predict_proba(
        node_test[NODE_FEATURES].fillna(0).to_numpy()
    )[:, 1]
    node_metrics = pd.DataFrame(
        [
            metric_row(
                node_test.label.astype(int).to_numpy(),
                node_test_score,
                "single-mechanism annual adoption",
            )
        ]
    )

    pair_all = annual_frames(
        range(2013, 2026),
        pair_frame,
        pure_vocab,
        ite_mapping,
        tg_mapping,
        embeddings,
    )
    pair_train = sample_pair_years(pair_all[pair_all.cutoff_year <= 2023])
    pair_validation = pair_all[pair_all.cutoff_year.eq(2024)].copy()
    pair_test = pair_all[pair_all.cutoff_year.eq(2025)].copy()
    pair_params, pair_tuning = train_model(
        pair_train, pair_validation, base.FEATURES
    )
    pair_combined = pd.concat(
        [pair_train, sample_pair_years(pair_validation)], ignore_index=True
    )
    pair_model = fit_cat(pair_params)
    pair_model.fit(
        pair_combined[base.FEATURES].fillna(0).to_numpy(),
        pair_combined.label.astype(int).to_numpy(),
        sample_weight=compute_sample_weight(
            "balanced", pair_combined.label.astype(int).to_numpy()
        ),
    )
    pair_probability = pair_model.predict_proba(
        pair_test[base.FEATURES].fillna(0).to_numpy()
    )[:, 1]
    pair_rank = base.rank_pct(pair_probability)

    node_score_lookup = dict(zip(node_test.concept_id, node_test_score))
    tg_first = first_years(tg_mapping)
    adoption = []
    for row in pair_test.itertuples(index=False):
        values = []
        for concept in [row.concept_u_id, row.concept_v_id]:
            values.append(
                1.0
                if tg_first.get(concept, 9999) <= 2025
                else node_score_lookup.get(concept, 0.0)
            )
        adoption.append(float(np.sqrt(values[0] * values[1])))
    adoption_rank = base.rank_pct(np.asarray(adoption))

    val_pair_probability = fit_cat(pair_params)
    val_pair_probability.fit(
        pair_train[base.FEATURES].fillna(0).to_numpy(),
        pair_train.label.astype(int).to_numpy(),
        sample_weight=compute_sample_weight(
            "balanced", pair_train.label.astype(int).to_numpy()
        ),
    )
    val_pair_rank = base.rank_pct(
        val_pair_probability.predict_proba(
            pair_validation[base.FEATURES].fillna(0).to_numpy()
        )[:, 1]
    )
    validation_node_model = fit_cat(node_params)
    validation_node_model.fit(
        node_train[NODE_FEATURES].fillna(0).to_numpy(),
        node_train.label.astype(int).to_numpy(),
        sample_weight=compute_sample_weight(
            "balanced", node_train.label.astype(int).to_numpy()
        ),
    )
    validation_nodes = node_validation.copy()
    validation_nodes["score"] = validation_node_model.predict_proba(
        validation_nodes[NODE_FEATURES].fillna(0).to_numpy()
    )[:, 1]
    validation_node_lookup = dict(
        zip(validation_nodes.concept_id, validation_nodes.score)
    )
    val_adoption = []
    for row in pair_validation.itertuples(index=False):
        values = []
        for concept in [row.concept_u_id, row.concept_v_id]:
            values.append(
                1.0
                if tg_first.get(concept, 9999) <= 2024
                else validation_node_lookup.get(concept, 0.0)
            )
        val_adoption.append(float(np.sqrt(values[0] * values[1])))
    val_adoption_rank = base.rank_pct(np.asarray(val_adoption))
    y_val = pair_validation.label.astype(int).to_numpy()
    blend_rows = []
    for pair_weight in np.linspace(0, 1, 101):
        score = pair_weight * val_pair_rank + (
            1 - pair_weight
        ) * val_adoption_rank
        row = metric_row(y_val, score, f"pair_weight={pair_weight:.2f}")
        row["pair_weight"] = pair_weight
        blend_rows.append(row)
    blend = pd.DataFrame(blend_rows).sort_values(
        ["average_precision", "precision_at_10"], ascending=False
    )
    pair_weight = float(blend.iloc[0].pair_weight)
    two_stage_score = pair_weight * pair_rank + (
        1 - pair_weight
    ) * adoption_rank
    y_test = pair_test.label.astype(int).to_numpy()
    pair_metrics = pd.DataFrame(
        [
            metric_row(y_test, pair_probability, "direct annual pair hazard"),
            metric_row(y_test, adoption_rank, "node-adoption compatibility"),
            metric_row(y_test, two_stage_score, "two-stage mechanism transfer"),
        ]
    )
    pair_scored = pair_test.copy()
    pair_scored["pair_probability"] = pair_probability
    pair_scored["node_adoption_compatibility"] = adoption
    pair_scored["two_stage_score"] = two_stage_score
    pair_scored = pair_scored.sort_values(
        "two_stage_score", ascending=False
    ).reset_index(drop=True)
    pair_scored["rank"] = np.arange(1, len(pair_scored) + 1)

    # Refit through 2025 and score the 2026 risk set for deployment.
    node_final = fit_cat(node_params)
    node_final.fit(
        node_all[NODE_FEATURES].fillna(0).to_numpy(),
        node_all.label.astype(int).to_numpy(),
        sample_weight=compute_sample_weight(
            "balanced", node_all.label.astype(int).to_numpy()
        ),
    )
    node_2026 = node_frame(
        2026, pure_vocab, ite_mapping, tg_mapping, embeddings
    )
    node_2026["adoption_probability"] = node_final.predict_proba(
        node_2026[NODE_FEATURES].fillna(0).to_numpy()
    )[:, 1]
    pair_final_train = sample_pair_years(pair_all)
    pair_final = fit_cat(pair_params)
    pair_final.fit(
        pair_final_train[base.FEATURES].fillna(0).to_numpy(),
        pair_final_train.label.astype(int).to_numpy(),
        sample_weight=compute_sample_weight(
            "balanced", pair_final_train.label.astype(int).to_numpy()
        ),
    )
    pair_2026 = pair_frame(
        2026, pure_vocab, ite_mapping, tg_mapping, embeddings
    )
    pair_2026_probability = pair_final.predict_proba(
        pair_2026[base.FEATURES].fillna(0).to_numpy()
    )[:, 1]
    pair_2026_rank = base.rank_pct(pair_2026_probability)
    node_2026_lookup = dict(
        zip(node_2026.concept_id, node_2026.adoption_probability)
    )
    adoption_2026 = []
    for row in pair_2026.itertuples(index=False):
        values = [
            1.0
            if tg_first.get(concept, 9999) <= 2026
            else node_2026_lookup.get(concept, 0.0)
            for concept in [row.concept_u_id, row.concept_v_id]
        ]
        adoption_2026.append(float(np.sqrt(values[0] * values[1])))
    pair_2026["pair_probability"] = pair_2026_probability
    pair_2026["node_adoption_compatibility"] = adoption_2026
    pair_2026["two_stage_score"] = (
        pair_weight * pair_2026_rank
        + (1 - pair_weight) * base.rank_pct(np.asarray(adoption_2026))
    )
    pair_2026 = pair_2026.sort_values(
        "two_stage_score", ascending=False
    ).reset_index(drop=True)
    pair_2026["future_rank"] = np.arange(1, len(pair_2026) + 1)

    node_all.to_csv(OUT / "node_annual_risk_rows.csv", index=False)
    pair_all.to_csv(OUT / "pair_annual_risk_rows.csv", index=False)
    node_tuning.to_csv(OUT / "node_model_tuning.csv", index=False)
    pair_tuning.to_csv(OUT / "pair_model_tuning.csv", index=False)
    blend.to_csv(OUT / "two_stage_weight_search.csv", index=False)
    node_metrics.to_csv(OUT / "node_test_metrics.csv", index=False)
    pair_metrics.to_csv(OUT / "pair_test_metrics.csv", index=False)
    pair_scored.to_csv(OUT / "pair_test_scores_2025_to_2026.csv", index=False)
    node_2026.sort_values(
        "adoption_probability", ascending=False
    ).to_csv(OUT / "future_single_mechanism_adoption.csv", index=False)
    pair_2026.to_csv(OUT / "future_two_stage_pair_predictions.csv", index=False)
    pair_2026.head(100).to_csv(
        OUT / "future_two_stage_pair_top100.csv", index=False
    )

    print("node params", node_params)
    print(node_metrics.to_string(index=False))
    print("\npair params", pair_params)
    print("pair weight", pair_weight, "node weight", 1 - pair_weight)
    print(pair_metrics.to_string(index=False))
    print("\nfuture top 15")
    print(
        pair_2026.head(15)[
            ["future_rank", "concept_u", "concept_v", "two_stage_score"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
