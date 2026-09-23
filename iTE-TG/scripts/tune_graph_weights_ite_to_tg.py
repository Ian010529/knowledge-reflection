from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

import minimal_clean_ite_to_tg_prediction as pipeline


ROOT = Path("/Users/ryan/Documents/iTE&TG")
BASE = ROOT / "minimal_clean_predictions" / "ite_to_tg"
OUT = BASE / "graph_weight_tuning"
OUT.mkdir(exist_ok=True)
RANDOM_STATE = 27

COMPONENTS = [
    "adamic_adar",
    "common_neighbors",
    "jaccard",
    "preferential_attachment",
    "shortest_path",
    "semantic_similarity",
    "recent_frequency_sum",
]
BASELINE = np.array([0.24, 0.18, 0.12, 0.12, 0.12, 0.12, 0.10])


def rank_matrix(frame: pd.DataFrame) -> np.ndarray:
    columns = []
    for component in COMPONENTS:
        values = frame[component].to_numpy()
        if component == "shortest_path":
            values = -values
        columns.append(pipeline.rank_pct(values))
    return np.column_stack(columns)


def precision_at(y: np.ndarray, score: np.ndarray, k: int) -> float:
    order = np.argsort(score)[::-1][: min(k, len(score))]
    return float(y[order].mean())


def fold_metrics(y: np.ndarray, score: np.ndarray) -> dict:
    return {
        "ap": average_precision_score(y, score),
        "auc": roc_auc_score(y, score),
        "p10": precision_at(y, score, 10),
        "p25": precision_at(y, score, 25),
        "p50": precision_at(y, score, 50),
    }


def objective(metrics: list[dict]) -> tuple[float, float]:
    fold_scores = np.array(
        [
            0.40 * row["ap"]
            + 0.20 * row["p10"]
            + 0.20 * row["p25"]
            + 0.20 * row["p50"]
            for row in metrics
        ]
    )
    robust_score = float(fold_scores.mean() - 0.10 * fold_scores.std())
    return robust_score, float(fold_scores.mean())


def main() -> None:
    vocab, ite_mapping, tg_mapping, _ = pipeline.load_data()
    embeddings = pipeline.build_embeddings(vocab)
    folds = {
        cutoff: pipeline.make_candidates(
            ite_mapping, tg_mapping, vocab, embeddings, cutoff, cutoff + 3
        )
        for cutoff in [2019, 2020, 2021]
    }
    fold_data = {
        cutoff: (
            rank_matrix(frame),
            frame.future_edge_label.astype(int).to_numpy(),
        )
        for cutoff, frame in folds.items()
    }

    rng = np.random.default_rng(RANDOM_STATE)
    candidates = [BASELINE, np.repeat(1 / len(COMPONENTS), len(COMPONENTS))]
    candidates.extend(np.eye(len(COMPONENTS)))
    for alpha in [0.25, 0.5, 1.0, 2.0, 5.0]:
        candidates.extend(
            rng.dirichlet(np.repeat(alpha, len(COMPONENTS)), size=2500)
        )

    search_rows = []
    best_weights = None
    best_score = -np.inf
    for index, weights in enumerate(candidates):
        per_fold = []
        for matrix, y in fold_data.values():
            per_fold.append(fold_metrics(y, matrix @ weights))
        robust, mean_score = objective(per_fold)
        if robust > best_score:
            best_score = robust
            best_weights = weights.copy()
        search_rows.append(
            {
                "candidate": index,
                **dict(zip(COMPONENTS, weights)),
                "robust_validation_objective": robust,
                "mean_validation_objective": mean_score,
                **{
                    f"mean_{metric}": float(
                        np.mean([row[metric] for row in per_fold])
                    )
                    for metric in ["ap", "auc", "p10", "p25", "p50"]
                },
            }
        )

    test = pd.read_csv(BASE / "ite_to_tg_test_candidates_2022_to_2026.csv")
    x_test = rank_matrix(test)
    y_test = test.future_edge_label.astype(int).to_numpy()
    comparisons = []
    scored = test[
        ["concept_u_id", "concept_v_id", "concept_u", "concept_v", "future_edge_label"]
    ].copy()
    for name, weights in [
        ("Baseline Graph", BASELINE),
        ("Tuned Graph", best_weights),
    ]:
        score = x_test @ weights
        row = {"model": name, **fold_metrics(y_test, score)}
        comparisons.append(row)
        scored[name] = score

    search = pd.DataFrame(search_rows).sort_values(
        "robust_validation_objective", ascending=False
    )
    weights = pd.DataFrame(
        {
            "component": COMPONENTS,
            "baseline_weight": BASELINE,
            "tuned_weight": best_weights,
        }
    )
    search.head(1000).to_csv(OUT / "top1000_graph_weight_search.csv", index=False)
    weights.to_csv(OUT / "selected_graph_weights.csv", index=False)
    pd.DataFrame(comparisons).to_csv(
        OUT / "graph_test_comparison.csv", index=False
    )
    scored.to_csv(OUT / "graph_test_candidate_scores.csv", index=False)
    print(weights.to_string(index=False))
    print()
    print(pd.DataFrame(comparisons).to_string(index=False))


if __name__ == "__main__":
    main()
