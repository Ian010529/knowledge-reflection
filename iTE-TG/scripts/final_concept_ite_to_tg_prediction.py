from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from itertools import combinations, product
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import StandardScaler


ROOT = Path("/Users/ryan/Documents/iTE&TG")
DATA = ROOT / "final_concept_layer"
OUT = ROOT / "ite_to_tg_prediction"
OUT.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 27
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

FEATURES = [
    "semantic_similarity",
    "degree_u",
    "degree_v",
    "degree_min",
    "degree_max",
    "document_frequency_u",
    "document_frequency_v",
    "frequency_min",
    "frequency_max",
    "frequency_balance",
    "recent_frequency_u",
    "recent_frequency_v",
    "recent_frequency_sum",
    "trend_u",
    "trend_v",
    "age_u",
    "age_v",
    "common_neighbors",
    "jaccard",
    "adamic_adar",
    "preferential_attachment",
    "shortest_path",
    "same_component",
    "same_type",
    "material_material_pair",
    "material_mechanism_pair",
    "mechanism_mechanism_pair",
    "tg_history_frequency_u",
    "tg_history_frequency_v",
    "tg_history_frequency_sum",
    "tg_both_concepts_seen",
]

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


def save_pub(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    vocab = pd.read_csv(DATA / "final_concept_vocabulary.csv")
    mapping = pd.read_csv(DATA / "final_paper_concept_map.csv")
    papers = pd.read_csv(DATA / "final_paper_index.csv")

    vocab = vocab[vocab["graph_role"] == "prediction_core"].copy()
    papers["year"] = pd.to_numeric(papers["year"], errors="coerce")
    papers = papers[papers["year"].between(1990, 2026)].copy()
    ite_papers = papers[papers["source_membership"].str.contains("iTE", na=False)].copy()
    tg_papers = papers[papers["source_membership"].str.contains("TG", na=False)].copy()
    mapping = mapping[
        mapping["paper_id"].isin(papers["paper_id"])
        & mapping["concept_id"].isin(vocab["concept_id"])
    ].copy()
    mapping = mapping.merge(
        papers[["paper_id", "year", "title"]], on="paper_id", how="left"
    )
    mapping = mapping.merge(
        vocab[
            [
                "concept_id",
                "canonical_concept",
                "concept_type",
                "concept_subtype",
            ]
        ],
        on=["concept_id", "canonical_concept", "concept_type", "concept_subtype"],
        how="left",
    )
    ite_mapping = mapping[mapping["paper_id"].isin(ite_papers["paper_id"])].copy()
    tg_mapping = mapping[mapping["paper_id"].isin(tg_papers["paper_id"])].copy()
    return vocab, ite_mapping, tg_mapping, papers


def build_embeddings(vocab: pd.DataFrame) -> dict[str, np.ndarray]:
    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2", local_files_only=True
    )
    labels = (
        vocab["canonical_concept"]
        + " | "
        + vocab["concept_type"].str.replace("_", " ")
        + " | "
        + vocab["concept_subtype"].fillna("")
    ).tolist()
    vectors = model.encode(
        labels, normalize_embeddings=True, show_progress_bar=False
    )
    return dict(zip(vocab["concept_id"], vectors))


def paper_concept_sets(
    mapping: pd.DataFrame, start: int | None = None, end: int | None = None
) -> dict[str, set[str]]:
    subset = mapping
    if start is not None:
        subset = subset[subset["year"] >= start]
    if end is not None:
        subset = subset[subset["year"] <= end]
    return (
        subset.groupby("paper_id")["concept_id"]
        .agg(lambda values: set(values))
        .to_dict()
    )


def edge_set_from_papers(paper_sets: dict[str, set[str]]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for concepts in paper_sets.values():
        edges.update(tuple(sorted(pair)) for pair in combinations(sorted(concepts), 2))
    return edges


def graph_state(
    mapping: pd.DataFrame, cutoff: int, vocab: pd.DataFrame
) -> dict:
    history = mapping[mapping["year"] <= cutoff].copy()
    counts = history.groupby("concept_id")["paper_id"].nunique().to_dict()
    first_year = history.groupby("concept_id")["year"].min().to_dict()
    recent = (
        history[history["year"].between(cutoff - 2, cutoff)]
        .groupby("concept_id")["paper_id"]
        .nunique()
        .to_dict()
    )
    previous = (
        history[history["year"].between(cutoff - 5, cutoff - 3)]
        .groupby("concept_id")["paper_id"]
        .nunique()
        .to_dict()
    )
    eligible = sorted(concept for concept, count in counts.items() if count >= 2)

    history_sets = paper_concept_sets(history)
    edges = edge_set_from_papers(history_sets)
    graph = nx.Graph()
    graph.add_nodes_from(eligible)
    graph.add_edges_from(
        (u, v) for u, v in edges if u in counts and v in counts
    )
    component = {}
    for component_id, nodes in enumerate(nx.connected_components(graph)):
        for node in nodes:
            component[node] = component_id
    distances = {
        node: dict(lengths)
        for node, lengths in nx.all_pairs_shortest_path_length(graph, cutoff=8)
    }
    neighbors = {node: set(graph.neighbors(node)) for node in graph.nodes}
    types = vocab.set_index("concept_id")["concept_type"].to_dict()
    labels = vocab.set_index("concept_id")["canonical_concept"].to_dict()
    return {
        "history": history,
        "counts": counts,
        "first_year": first_year,
        "recent": recent,
        "previous": previous,
        "eligible": eligible,
        "edges": edges,
        "graph": graph,
        "component": component,
        "distances": distances,
        "neighbors": neighbors,
        "types": types,
        "labels": labels,
    }


def pair_features(
    u: str,
    v: str,
    cutoff: int,
    state: dict,
    embeddings: dict[str, np.ndarray],
) -> dict:
    neighbors_u = state["neighbors"].get(u, set())
    neighbors_v = state["neighbors"].get(v, set())
    common = neighbors_u & neighbors_v
    union = neighbors_u | neighbors_v
    degree_u = len(neighbors_u)
    degree_v = len(neighbors_v)
    count_u = state["counts"].get(u, 0)
    count_v = state["counts"].get(v, 0)
    recent_u = state["recent"].get(u, 0)
    recent_v = state["recent"].get(v, 0)
    previous_u = state["previous"].get(u, 0)
    previous_v = state["previous"].get(v, 0)
    type_u = state["types"].get(u, "")
    type_v = state["types"].get(v, "")
    u_material = type_u in MATERIAL_TYPES
    v_material = type_v in MATERIAL_TYPES
    u_mechanism = type_u in MECHANISM_TYPES
    v_mechanism = type_v in MECHANISM_TYPES
    distance = state["distances"].get(u, {}).get(v, 9)
    adamic = sum(
        1.0 / math.log(max(2, len(state["neighbors"].get(node, set()))))
        for node in common
    )
    return {
        "concept_u_id": u,
        "concept_v_id": v,
        "concept_u": state["labels"].get(u, u),
        "concept_v": state["labels"].get(v, v),
        "u_type": type_u,
        "v_type": type_v,
        "semantic_similarity": float(np.dot(embeddings[u], embeddings[v])),
        "degree_u": degree_u,
        "degree_v": degree_v,
        "degree_min": min(degree_u, degree_v),
        "degree_max": max(degree_u, degree_v),
        "document_frequency_u": count_u,
        "document_frequency_v": count_v,
        "frequency_min": min(count_u, count_v),
        "frequency_max": max(count_u, count_v),
        "frequency_balance": min(count_u, count_v) / max(1, max(count_u, count_v)),
        "recent_frequency_u": recent_u,
        "recent_frequency_v": recent_v,
        "recent_frequency_sum": recent_u + recent_v,
        "trend_u": (recent_u - previous_u) / 3.0,
        "trend_v": (recent_v - previous_v) / 3.0,
        "age_u": cutoff - state["first_year"].get(u, cutoff),
        "age_v": cutoff - state["first_year"].get(v, cutoff),
        "common_neighbors": len(common),
        "jaccard": len(common) / max(1, len(union)),
        "adamic_adar": adamic,
        "preferential_attachment": degree_u * degree_v,
        "shortest_path": distance,
        "same_component": int(
            state["component"].get(u, -1) == state["component"].get(v, -2)
        ),
        "same_type": int(type_u == type_v),
        "material_material_pair": int(u_material and v_material),
        "material_mechanism_pair": int(
            (u_material and v_mechanism) or (v_material and u_mechanism)
        ),
        "mechanism_mechanism_pair": int(u_mechanism and v_mechanism),
    }


def make_candidates(
    ite_mapping: pd.DataFrame,
    tg_mapping: pd.DataFrame,
    vocab: pd.DataFrame,
    embeddings: dict[str, np.ndarray],
    cutoff: int,
    horizon_end: int,
) -> pd.DataFrame:
    state = graph_state(ite_mapping, cutoff, vocab)
    tg_history = tg_mapping[tg_mapping["year"] <= cutoff]
    tg_future = tg_mapping[tg_mapping["year"].between(cutoff + 1, horizon_end)]
    tg_history_edges = edge_set_from_papers(paper_concept_sets(tg_history))
    tg_future_edges = edge_set_from_papers(paper_concept_sets(tg_future))
    tg_counts = tg_history.groupby("concept_id")["paper_id"].nunique().to_dict()
    rows = []
    for u, v in sorted(state["edges"]):
        pair = tuple(sorted((u, v)))
        if u not in state["eligible"] or v not in state["eligible"]:
            continue
        if pair in tg_history_edges:
            continue
        features = pair_features(u, v, cutoff, state, embeddings)
        features["tg_history_frequency_u"] = tg_counts.get(u, 0)
        features["tg_history_frequency_v"] = tg_counts.get(v, 0)
        features["tg_history_frequency_sum"] = (
            tg_counts.get(u, 0) + tg_counts.get(v, 0)
        )
        features["tg_both_concepts_seen"] = int(
            tg_counts.get(u, 0) > 0 and tg_counts.get(v, 0) > 0
        )
        features["cutoff_year"] = cutoff
        features["future_window"] = f"{cutoff + 1}-{horizon_end}"
        features["future_edge_label"] = int(pair in tg_future_edges)
        rows.append(features)
    return pd.DataFrame(rows)


def rank_pct(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(pct=True, method="average").to_numpy()


def graph_score(frame: pd.DataFrame) -> np.ndarray:
    return (
        0.24 * rank_pct(frame["adamic_adar"].to_numpy())
        + 0.18 * rank_pct(frame["common_neighbors"].to_numpy())
        + 0.12 * rank_pct(frame["jaccard"].to_numpy())
        + 0.12 * rank_pct(frame["preferential_attachment"].to_numpy())
        + 0.12 * rank_pct(-frame["shortest_path"].to_numpy())
        + 0.12 * rank_pct(frame["semantic_similarity"].to_numpy())
        + 0.10 * rank_pct(frame["recent_frequency_sum"].to_numpy())
    )


def sample_training(frame: pd.DataFrame, negative_ratio: int = 15) -> pd.DataFrame:
    positives = frame[frame["future_edge_label"] == 1]
    negatives = frame[frame["future_edge_label"] == 0].copy()
    if positives.empty:
        return frame.iloc[0:0]
    n_negative = min(len(negatives), negative_ratio * len(positives))
    hard_n = n_negative // 2
    negatives["_hard"] = graph_score(negatives)
    hard = negatives.nlargest(hard_n, "_hard")
    remaining = negatives.drop(index=hard.index)
    random = remaining.sample(
        n=n_negative - len(hard),
        random_state=RANDOM_STATE,
        replace=False,
    )
    return (
        pd.concat([positives, hard, random], ignore_index=True)
        .drop(columns="_hard", errors="ignore")
        .sample(frac=1, random_state=RANDOM_STATE)
        .reset_index(drop=True)
    )


def metric_row(y: np.ndarray, score: np.ndarray, model: str) -> dict:
    row = {
        "model": model,
        "roc_auc": roc_auc_score(y, score),
        "average_precision": average_precision_score(y, score),
        "positive_rate": float(y.mean()),
    }
    order = np.argsort(score)[::-1]
    for k in [10, 25, 50, 100, 250]:
        selected = order[: min(k, len(order))]
        row[f"precision_at_{k}"] = float(y[selected].mean())
        row[f"hits_at_{k}"] = int(y[selected].sum())
    return row


def choose_f1_threshold(y: np.ndarray, score: np.ndarray) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(y, score)
    if len(thresholds) == 0:
        return 0.5, 0.0
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(
        precision[:-1] + recall[:-1], 1e-12
    )
    index = int(np.nanargmax(f1))
    return float(thresholds[index]), float(f1[index])


def fit_models(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    rolling_validations: dict[int, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    x_train = train[FEATURES].fillna(0).to_numpy()
    y_train = train["future_edge_label"].astype(int).to_numpy()
    x_val = validation[FEATURES].fillna(0).to_numpy()
    y_val = validation["future_edge_label"].astype(int).to_numpy()
    x_test = test[FEATURES].fillna(0).to_numpy()
    y_test = test["future_edge_label"].astype(int).to_numpy()

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    tuning_rows = []

    best_lr = None
    best_lr_score = -np.inf
    best_lr_params = {}
    for c_value in [0.03, 0.1, 0.3, 1.0, 3.0]:
        model = LogisticRegression(
            C=c_value,
            max_iter=4000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        )
        model.fit(x_train_scaled, y_train)
        score = model.predict_proba(x_val_scaled)[:, 1]
        ap = average_precision_score(y_val, score)
        tuning_rows.append(
            {"family": "logistic", "params": f"C={c_value}", "validation_ap": ap}
        )
        if ap > best_lr_score:
            best_lr_score = ap
            best_lr = model
            best_lr_params = {"C": c_value}
    lr_val = best_lr.predict_proba(x_val_scaled)[:, 1]

    rf_grid = [
        {"max_depth": None, "min_samples_leaf": 2, "max_features": "sqrt"},
        {"max_depth": None, "min_samples_leaf": 5, "max_features": "sqrt"},
        {"max_depth": 16, "min_samples_leaf": 2, "max_features": "sqrt"},
        {"max_depth": 16, "min_samples_leaf": 5, "max_features": 0.7},
        {"max_depth": 10, "min_samples_leaf": 5, "max_features": "sqrt"},
        {"max_depth": 10, "min_samples_leaf": 10, "max_features": 0.7},
    ]
    best_rf = None
    best_rf_score = -np.inf
    best_rf_params = {}
    for params in rf_grid:
        model = RandomForestClassifier(
            n_estimators=500,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
            **params,
        )
        model.fit(x_train, y_train)
        score = model.predict_proba(x_val)[:, 1]
        ap = average_precision_score(y_val, score)
        tuning_rows.append(
            {
                "family": "random_forest",
                "params": json.dumps(params),
                "validation_ap": ap,
            }
        )
        if ap > best_rf_score:
            best_rf_score = ap
            best_rf = model
            best_rf_params = params
    rf_val = best_rf.predict_proba(x_val)[:, 1]
    graph_val = graph_score(validation)

    best_blend = None
    best_blend_ap = -np.inf
    for rf_weight in np.linspace(0, 1, 11):
        ml_score = rf_weight * rank_pct(rf_val) + (1 - rf_weight) * rank_pct(lr_val)
        ap = average_precision_score(y_val, ml_score)
        tuning_rows.append(
            {
                "family": "ml_blend",
                "params": f"rf_weight={rf_weight:.1f}",
                "validation_ap": ap,
            }
        )
        if ap > best_blend_ap:
            best_blend_ap = ap
            best_blend = float(rf_weight)

    ml_val = best_blend * rank_pct(rf_val) + (1 - best_blend) * rank_pct(lr_val)
    rolling_scores = []
    for fold_cutoff, fold_validation in rolling_validations.items():
        fold_train = train[train["cutoff_year"] <= fold_cutoff - 3]
        fold_x = fold_train[FEATURES].fillna(0).to_numpy()
        fold_y = fold_train["future_edge_label"].astype(int).to_numpy()
        fold_val_x = fold_validation[FEATURES].fillna(0).to_numpy()
        fold_val_y = fold_validation["future_edge_label"].astype(int).to_numpy()
        fold_scaler = StandardScaler()
        fold_x_scaled = fold_scaler.fit_transform(fold_x)
        fold_val_x_scaled = fold_scaler.transform(fold_val_x)
        fold_lr = LogisticRegression(
            C=best_lr_params["C"],
            max_iter=4000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        )
        fold_lr.fit(fold_x_scaled, fold_y)
        fold_rf = RandomForestClassifier(
            n_estimators=500,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
            **best_rf_params,
        )
        fold_rf.fit(fold_x, fold_y)
        fold_lr_score = fold_lr.predict_proba(fold_val_x_scaled)[:, 1]
        fold_rf_score = fold_rf.predict_proba(fold_val_x)[:, 1]
        fold_ml = best_blend * rank_pct(fold_rf_score) + (
            1 - best_blend
        ) * rank_pct(fold_lr_score)
        fold_graph = graph_score(fold_validation)
        rolling_scores.append(
            {
                "cutoff": fold_cutoff,
                "y": fold_val_y,
                "ml": fold_ml,
                "graph": fold_graph,
            }
        )

    rolling_weight_rows = []
    for ml_weight in np.linspace(0, 1, 21):
        fold_aps = []
        fold_aucs = []
        for fold in rolling_scores:
            hybrid = ml_weight * rank_pct(fold["ml"]) + (
                1 - ml_weight
            ) * rank_pct(fold["graph"])
            fold_aps.append(average_precision_score(fold["y"], hybrid))
            fold_aucs.append(roc_auc_score(fold["y"], hybrid))
            tuning_rows.append(
                {
                    "family": "rolling_hybrid_fold",
                    "params": f"cutoff={fold['cutoff']};ml_weight={ml_weight:.2f}",
                    "validation_ap": fold_aps[-1],
                }
            )
        rolling_weight_rows.append(
            {
                "ml_weight": float(ml_weight),
                "mean_ap": float(np.mean(fold_aps)),
                "minimum_ap": float(np.min(fold_aps)),
                "mean_auc": float(np.mean(fold_aucs)),
            }
        )
    rolling_weight_frame = pd.DataFrame(rolling_weight_rows).sort_values(
        ["mean_ap", "minimum_ap"], ascending=False
    )
    best_hybrid_weight = float(rolling_weight_frame.iloc[0]["ml_weight"])
    tuning_rows.extend(
        {
            "family": "rolling_hybrid_summary",
            "params": f"ml_weight={row.ml_weight:.2f};min_ap={row.minimum_ap:.6f};mean_auc={row.mean_auc:.6f}",
            "validation_ap": row.mean_ap,
        }
        for row in rolling_weight_frame.itertuples(index=False)
    )

    combined = pd.concat([train, sample_training(validation)], ignore_index=True)
    x_combined = combined[FEATURES].fillna(0).to_numpy()
    y_combined = combined["future_edge_label"].astype(int).to_numpy()
    final_scaler = StandardScaler()
    x_combined_scaled = final_scaler.fit_transform(x_combined)
    x_test_scaled = final_scaler.transform(x_test)

    final_lr = LogisticRegression(
        C=best_lr_params["C"],
        max_iter=4000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
    final_lr.fit(x_combined_scaled, y_combined)
    lr_test = final_lr.predict_proba(x_test_scaled)[:, 1]

    final_rf = RandomForestClassifier(
        n_estimators=800,
        class_weight="balanced_subsample",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        **best_rf_params,
    )
    final_rf.fit(x_combined, y_combined)
    rf_test = final_rf.predict_proba(x_test)[:, 1]
    graph_test = graph_score(test)
    ml_test = best_blend * rank_pct(rf_test) + (1 - best_blend) * rank_pct(lr_test)
    hybrid_test = best_hybrid_weight * rank_pct(ml_test) + (
        1 - best_hybrid_weight
    ) * rank_pct(graph_test)

    pooled_y = []
    pooled_score = []
    for fold in rolling_scores:
        pooled_y.append(fold["y"])
        pooled_score.append(
            best_hybrid_weight * rank_pct(fold["ml"])
            + (1 - best_hybrid_weight) * rank_pct(fold["graph"])
        )
    threshold, validation_f1 = choose_f1_threshold(
        np.concatenate(pooled_y), np.concatenate(pooled_score)
    )

    scored = test.copy()
    scored["logistic_score"] = lr_test
    scored["random_forest_score"] = rf_test
    scored["ml_score"] = ml_test
    scored["graph_score"] = graph_test
    scored["hybrid_score"] = hybrid_test
    scored["predicted_class"] = (hybrid_test >= threshold).astype(int)
    scored = scored.sort_values("hybrid_score", ascending=False).reset_index(drop=True)
    scored["hybrid_rank"] = np.arange(1, len(scored) + 1)

    metric_rows = [
        metric_row(y_test, ml_test, "ML"),
        metric_row(y_test, graph_test, "Graph"),
        metric_row(y_test, hybrid_test, "Hybrid"),
    ]
    pred = (hybrid_test >= threshold).astype(int)
    classification = {
        "threshold_selected_on_rolling_validation": threshold,
        "rolling_validation_f1_at_threshold": validation_f1,
        "test_precision": precision_score(y_test, pred, zero_division=0),
        "test_recall": recall_score(y_test, pred, zero_division=0),
        "test_f1": f1_score(y_test, pred, zero_division=0),
        "predicted_positive": int(pred.sum()),
        "actual_positive": int(y_test.sum()),
        "true_negative": int(confusion_matrix(y_test, pred, labels=[0, 1])[0, 0]),
        "false_positive": int(confusion_matrix(y_test, pred, labels=[0, 1])[0, 1]),
        "false_negative": int(confusion_matrix(y_test, pred, labels=[0, 1])[1, 0]),
        "true_positive": int(confusion_matrix(y_test, pred, labels=[0, 1])[1, 1]),
        "best_logistic_params": json.dumps(best_lr_params),
        "best_random_forest_params": json.dumps(best_rf_params),
        "rf_weight_in_ml": best_blend,
        "ml_weight_in_hybrid": best_hybrid_weight,
    }
    return (
        scored,
        pd.DataFrame(metric_rows),
        pd.DataFrame(tuning_rows),
        classification,
    )


def plot_performance(scored: pd.DataFrame, metrics: pd.DataFrame) -> None:
    y = scored["future_edge_label"].astype(int).to_numpy()
    model_specs = [
        ("ML", "ml_score", "#2B6CB0"),
        ("Graph", "graph_score", "#B7791F"),
        ("Hybrid", "hybrid_score", "#237A57"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), constrained_layout=True)
    for name, column, color in model_specs:
        score = scored[column].to_numpy()
        fpr, tpr, _ = roc_curve(y, score)
        precision, recall, _ = precision_recall_curve(y, score)
        auc = roc_auc_score(y, score)
        ap = average_precision_score(y, score)
        axes[0].plot(fpr, tpr, lw=1.5, color=color, label=f"{name} ({auc:.3f})")
        axes[1].plot(recall, precision, lw=1.5, color=color, label=f"{name} ({ap:.3f})")
    axes[0].plot([0, 1], [0, 1], ls="--", lw=0.8, color="#A0AEC0")
    axes[1].axhline(y.mean(), ls="--", lw=0.8, color="#A0AEC0")
    axes[0].set(
        xlabel="False-positive rate",
        ylabel="True-positive rate",
        title="a  ROC: new concept-pair classification",
    )
    axes[1].set(
        xlabel="Recall",
        ylabel="Precision",
        title=f"b  Precision-recall (baseline = {y.mean():.3f})",
        ylim=(0, 1.02),
    )
    axes[0].legend(title="ROC AUC", fontsize=6, title_fontsize=6)
    axes[1].legend(title="Average precision", fontsize=6, title_fontsize=6)
    fig.suptitle(
        "iTE to TG transfer backtest: iTE-known links adopted by TG in 2023-2026",
        x=0.01,
        ha="left",
        fontsize=9,
    )
    save_pub(fig, OUT / "ite_to_tg_roc_pr")
    plt.close(fig)


def plot_confusion_matrix(scored: pd.DataFrame, classification: dict) -> None:
    y = scored["future_edge_label"].astype(int).to_numpy()
    pred = scored["predicted_class"].astype(int).to_numpy()
    cm = confusion_matrix(y, pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(3.3, 2.9), constrained_layout=True)
    image = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1], ["Predicted 0", "Predicted 1"])
    ax.set_yticks([0, 1], ["Observed 0", "Observed 1"])
    maximum = cm.max()
    for row in range(2):
        for column in range(2):
            ax.text(
                column,
                row,
                f"{cm[row, column]:,}",
                ha="center",
                va="center",
                fontsize=11,
                color="white" if cm[row, column] > maximum * 0.52 else "#1A202C",
            )
    ax.set_title(
        "Hybrid confusion matrix\n"
        f"rolling-validation threshold={classification['threshold_selected_on_rolling_validation']:.3f}; "
        f"P={classification['test_precision']:.3f}, "
        f"R={classification['test_recall']:.3f}, "
        f"F1={classification['test_f1']:.3f}",
        fontsize=7.5,
    )
    save_pub(fig, OUT / "ite_to_tg_confusion_matrix")
    plt.close(fig)


def plot_prediction_matrix(scored: pd.DataFrame, top_pairs: int = 120) -> None:
    top = scored.head(top_pairs)
    concept_counts = Counter(top["concept_u_id"].tolist() + top["concept_v_id"].tolist())
    selected = [concept for concept, _ in concept_counts.most_common(18)]
    label_lookup = pd.concat(
        [
            scored[["concept_u_id", "concept_u"]].rename(
                columns={"concept_u_id": "id", "concept_u": "label"}
            ),
            scored[["concept_v_id", "concept_v"]].rename(
                columns={"concept_v_id": "id", "concept_v": "label"}
            ),
        ]
    ).drop_duplicates("id").set_index("id")["label"].to_dict()
    index = {concept: idx for idx, concept in enumerate(selected)}
    predicted = np.full((len(selected), len(selected)), np.nan)
    observed = np.full((len(selected), len(selected)), np.nan)
    for row in scored.itertuples(index=False):
        if row.concept_u_id not in index or row.concept_v_id not in index:
            continue
        i = index[row.concept_u_id]
        j = index[row.concept_v_id]
        predicted[i, j] = predicted[j, i] = row.hybrid_score
        observed[i, j] = observed[j, i] = row.future_edge_label
    np.fill_diagonal(predicted, np.nan)
    np.fill_diagonal(observed, np.nan)
    labels = [
        label_lookup.get(concept, concept)[:22]
        + ("..." if len(label_lookup.get(concept, concept)) > 22 else "")
        for concept in selected
    ]

    fig, axes = plt.subplots(
        1, 2, figsize=(7.2, 4.2), constrained_layout=True
    )
    im0 = axes[0].imshow(predicted, cmap="YlGnBu", vmin=0, vmax=1)
    im1 = axes[1].imshow(observed, cmap=mpl.colors.ListedColormap(["#F4F6F7", "#D1495B"]), vmin=0, vmax=1)
    for ax, title in zip(
        axes,
        [
            "a  Predicted probability/rank score",
            "b  Observed TG adoption, 2023-2026",
        ],
    ):
        ax.set_xticks(
            range(len(labels)),
            [str(i + 1) for i in range(len(labels))],
            rotation=0,
            fontsize=5.0,
        )
        ax.set_yticks(range(len(labels)), labels, fontsize=5.0)
        ax.set_xlabel("Concept index (same order as rows)", fontsize=6)
        ax.set_title(title, loc="left", fontsize=8)
        ax.tick_params(length=0)
    fig.colorbar(im0, ax=axes[0], fraction=0.035, pad=0.02, label="Hybrid score")
    fig.colorbar(im1, ax=axes[1], fraction=0.035, pad=0.02, ticks=[0, 1], label="Observed class")
    fig.suptitle(
        "Predicted versus observed iTE-to-TG knowledge transfer",
        x=0.01,
        ha="left",
        fontsize=9,
    )
    save_pub(fig, OUT / "ite_to_tg_prediction_matrix")
    plt.close(fig)

    predicted_frame = pd.DataFrame(predicted, index=labels, columns=labels)
    observed_frame = pd.DataFrame(observed, index=labels, columns=labels)
    predicted_frame.to_csv(OUT / "ite_to_tg_prediction_matrix_top_concepts.csv")
    observed_frame.to_csv(OUT / "ite_to_tg_observed_matrix_top_concepts.csv")


def plot_typed_prediction_matrices(
    scored: pd.DataFrame, top_pairs: int = 250
) -> None:
    top = scored.head(top_pairs).copy()

    def typed_rows(left_types: set[str], right_types: set[str]) -> pd.DataFrame:
        rows = []
        for row in scored.itertuples(index=False):
            if row.u_type in left_types and row.v_type in right_types:
                left_id, left_label = row.concept_u_id, row.concept_u
                right_id, right_label = row.concept_v_id, row.concept_v
            elif row.v_type in left_types and row.u_type in right_types:
                left_id, left_label = row.concept_v_id, row.concept_v
                right_id, right_label = row.concept_u_id, row.concept_u
            else:
                continue
            rows.append(
                {
                    "left_id": left_id,
                    "left_label": left_label,
                    "right_id": right_id,
                    "right_label": right_label,
                    "score": row.hybrid_score,
                    "observed": row.future_edge_label,
                    "rank": row.hybrid_rank,
                }
            )
        return pd.DataFrame(rows)

    def shorten(value: str, length: int = 25) -> str:
        return value if len(value) <= length else value[:length] + "..."

    material_mechanism = typed_rows(MATERIAL_TYPES, MECHANISM_TYPES)
    top_mm = material_mechanism[material_mechanism["rank"] <= top_pairs]
    material_order = (
        top_mm["left_id"].value_counts().head(14).index.tolist()
    )
    mechanism_order = (
        top_mm["right_id"].value_counts().head(14).index.tolist()
    )
    material_labels = (
        material_mechanism.drop_duplicates("left_id")
        .set_index("left_id")["left_label"]
        .to_dict()
    )
    mechanism_labels = (
        material_mechanism.drop_duplicates("right_id")
        .set_index("right_id")["right_label"]
        .to_dict()
    )
    material_index = {value: i for i, value in enumerate(material_order)}
    mechanism_index = {value: i for i, value in enumerate(mechanism_order)}
    predicted = np.full((len(material_order), len(mechanism_order)), np.nan)
    observed = np.full_like(predicted, np.nan)
    for row in material_mechanism.itertuples(index=False):
        if row.left_id in material_index and row.right_id in mechanism_index:
            i = material_index[row.left_id]
            j = mechanism_index[row.right_id]
            predicted[i, j] = row.score
            observed[i, j] = row.observed
    y_labels = [shorten(material_labels[value]) for value in material_order]
    x_labels = [shorten(mechanism_labels[value], 20) for value in mechanism_order]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.5), constrained_layout=True)
    images = [
        axes[0].imshow(predicted, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto"),
        axes[1].imshow(
            observed,
            cmap=mpl.colors.ListedColormap(["#F4F6F7", "#D1495B"]),
            vmin=0,
            vmax=1,
            aspect="auto",
        ),
    ]
    for ax, title in zip(
        axes,
        ["a  Predicted transfer score", "b  Observed TG adoption"],
    ):
        ax.set_xticks(
            range(len(x_labels)),
            x_labels,
            rotation=58,
            ha="right",
            rotation_mode="anchor",
            fontsize=5,
        )
        ax.set_yticks(range(len(y_labels)), y_labels, fontsize=5)
        ax.tick_params(length=0)
        ax.set_xlabel("Mechanism concept", fontsize=6)
        ax.set_ylabel("Material concept", fontsize=6)
        ax.set_title(title, loc="left", fontsize=8)
    fig.colorbar(images[0], ax=axes[0], fraction=0.035, pad=0.02, label="Hybrid score")
    fig.colorbar(images[1], ax=axes[1], fraction=0.035, pad=0.02, ticks=[0, 1], label="Observed class")
    fig.suptitle("iTE-to-TG transfer: material x mechanism", x=0.01, ha="left", fontsize=9)
    save_pub(fig, OUT / "ite_to_tg_material_mechanism_matrix")
    plt.close(fig)
    pd.DataFrame(predicted, index=y_labels, columns=x_labels).to_csv(
        OUT / "ite_to_tg_material_mechanism_predicted.csv"
    )
    pd.DataFrame(observed, index=y_labels, columns=x_labels).to_csv(
        OUT / "ite_to_tg_material_mechanism_observed.csv"
    )

    mechanism_pairs = typed_rows(MECHANISM_TYPES, MECHANISM_TYPES)
    top_mechanism_pairs = mechanism_pairs[mechanism_pairs["rank"] <= top_pairs]
    counts = Counter(
        top_mechanism_pairs["left_id"].tolist()
        + top_mechanism_pairs["right_id"].tolist()
    )
    mechanism_nodes = [value for value, _ in counts.most_common(18)]
    all_mechanism_labels = pd.concat(
        [
            mechanism_pairs[["left_id", "left_label"]].rename(
                columns={"left_id": "id", "left_label": "label"}
            ),
            mechanism_pairs[["right_id", "right_label"]].rename(
                columns={"right_id": "id", "right_label": "label"}
            ),
        ]
    ).drop_duplicates("id").set_index("id")["label"].to_dict()
    node_index = {value: i for i, value in enumerate(mechanism_nodes)}
    predicted = np.full((len(mechanism_nodes), len(mechanism_nodes)), np.nan)
    observed = np.full_like(predicted, np.nan)
    for row in mechanism_pairs.itertuples(index=False):
        if row.left_id in node_index and row.right_id in node_index:
            i = node_index[row.left_id]
            j = node_index[row.right_id]
            predicted[i, j] = predicted[j, i] = row.score
            observed[i, j] = observed[j, i] = row.observed
    np.fill_diagonal(predicted, np.nan)
    np.fill_diagonal(observed, np.nan)
    labels = [shorten(all_mechanism_labels[value], 25) for value in mechanism_nodes]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2), constrained_layout=True)
    images = [
        axes[0].imshow(predicted, cmap="YlGnBu", vmin=0, vmax=1),
        axes[1].imshow(
            observed,
            cmap=mpl.colors.ListedColormap(["#F4F6F7", "#D1495B"]),
            vmin=0,
            vmax=1,
        ),
    ]
    for ax, title in zip(
        axes,
        ["a  Predicted transfer score", "b  Observed TG adoption"],
    ):
        ax.set_xticks(
            range(len(labels)),
            [str(i + 1) for i in range(len(labels))],
            fontsize=5,
        )
        ax.set_yticks(range(len(labels)), labels, fontsize=5)
        ax.set_xlabel("Mechanism index (same order as rows)", fontsize=6)
        ax.set_title(title, loc="left", fontsize=8)
        ax.tick_params(length=0)
    fig.colorbar(images[0], ax=axes[0], fraction=0.035, pad=0.02, label="Hybrid score")
    fig.colorbar(images[1], ax=axes[1], fraction=0.035, pad=0.02, ticks=[0, 1], label="Observed class")
    fig.suptitle("iTE-to-TG transfer: mechanism x mechanism", x=0.01, ha="left", fontsize=9)
    save_pub(fig, OUT / "ite_to_tg_mechanism_mechanism_matrix")
    plt.close(fig)
    pd.DataFrame(predicted, index=labels, columns=labels).to_csv(
        OUT / "ite_to_tg_mechanism_mechanism_predicted.csv"
    )
    pd.DataFrame(observed, index=labels, columns=labels).to_csv(
        OUT / "ite_to_tg_mechanism_mechanism_observed.csv"
    )


def main() -> None:
    vocab, ite_mapping, tg_mapping, papers = load_data()
    embeddings = build_embeddings(vocab)

    train_windows = []
    window_summary = []
    for cutoff in range(2013, 2020):
        frame = make_candidates(
            ite_mapping, tg_mapping, vocab, embeddings, cutoff, cutoff + 3
        )
        if frame.empty:
            continue
        sampled = sample_training(frame)
        train_windows.append(sampled)
        window_summary.append(
            {
                "cutoff_year": cutoff,
                "future_window": f"{cutoff + 1}-{cutoff + 3}",
                "all_candidates": len(frame),
                "all_positives": int(frame["future_edge_label"].sum()),
                "sampled_train_candidates": len(sampled),
                "sampled_train_positives": int(sampled["future_edge_label"].sum()),
            }
        )
    train = pd.concat(train_windows, ignore_index=True)
    rolling_validations = {
        2019: make_candidates(ite_mapping, tg_mapping, vocab, embeddings, 2019, 2022),
        2020: make_candidates(ite_mapping, tg_mapping, vocab, embeddings, 2020, 2023),
        2021: make_candidates(ite_mapping, tg_mapping, vocab, embeddings, 2021, 2024),
    }
    validation = rolling_validations[2021]
    test = make_candidates(
        ite_mapping, tg_mapping, vocab, embeddings, 2022, 2026
    )

    scored, metrics, tuning, classification = fit_models(
        train, validation, test, rolling_validations
    )
    metrics["n_candidates"] = len(test)
    metrics["n_positive"] = int(test["future_edge_label"].sum())

    train.to_csv(OUT / "ite_to_tg_train_samples_2013_2019.csv", index=False)
    validation.to_csv(OUT / "ite_to_tg_validation_candidates_2021_to_2024.csv", index=False)
    test.to_csv(OUT / "ite_to_tg_test_candidates_2022_to_2026.csv", index=False)
    scored.to_csv(OUT / "ite_to_tg_scored_candidates_2022_to_2026.csv", index=False)
    scored.head(100).to_csv(OUT / "ite_to_tg_top100_predictions.csv", index=False)
    metrics.to_csv(OUT / "ite_to_tg_backtest_metrics.csv", index=False)
    tuning.to_csv(OUT / "ite_to_tg_hyperparameter_tuning.csv", index=False)
    pd.DataFrame(window_summary).to_csv(OUT / "ite_to_tg_training_window_summary.csv", index=False)
    pd.DataFrame([classification]).to_csv(
        OUT / "ite_to_tg_classification_metrics.csv", index=False
    )

    feature_importance = pd.DataFrame(
        {
            "feature": FEATURES,
            "note": [
                "semantic embedding cosine similarity",
                *["historical graph/node feature"] * (len(FEATURES) - 1),
            ],
        }
    )
    feature_importance.to_csv(OUT / "ite_to_tg_model_feature_dictionary.csv", index=False)

    plot_performance(scored, metrics)
    plot_confusion_matrix(scored, classification)
    plot_prediction_matrix(scored)
    plot_typed_prediction_matrices(scored)

    summary = {
        "input_unique_iTE_papers": int(
            papers["source_membership"].str.contains("iTE", na=False).sum()
        ),
        "input_unique_TG_papers": int(
            papers["source_membership"].str.contains("TG", na=False).sum()
        ),
        "input_prediction_core_concepts": int(len(vocab)),
        "concepts_seen_at_2022": int(
            ite_mapping[ite_mapping["year"] <= 2022]["concept_id"].nunique()
        ),
        "training_samples": int(len(train)),
        "training_positives": int(train["future_edge_label"].sum()),
        "validation_candidates": int(len(validation)),
        "validation_positives": int(validation["future_edge_label"].sum()),
        "test_candidates": int(len(test)),
        "test_positives": int(test["future_edge_label"].sum()),
        "test_positive_rate": float(test["future_edge_label"].mean()),
        "metrics": metrics.set_index("model").to_dict(orient="index"),
        "classification": classification,
    }
    (OUT / "ite_to_tg_prediction_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
