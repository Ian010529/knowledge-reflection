from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.utils.class_weight import compute_sample_weight

import minimal_clean_ite_to_tg_prediction as pipeline
import train_mechanism_only_ite_to_tg as mechanism


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = (
    ROOT
    / "minimal_clean_predictions"
    / "ite_to_tg"
    / "mechanism_only_5year_final"
)
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    vocab, ite_mapping, tg_mapping, _ = pipeline.load_data()
    embeddings = pipeline.build_embeddings(vocab)
    windows = []
    summary_rows = []
    for cutoff in range(2013, 2022):
        candidates = mechanism.mechanism_only(
            pipeline.make_candidates(
                ite_mapping,
                tg_mapping,
                vocab,
                embeddings,
                cutoff,
                cutoff + 5,
            )
        )
        sampled = pipeline.sample_training(candidates)
        if not sampled.empty:
            windows.append(sampled)
        summary_rows.append(
            {
                "cutoff_year": cutoff,
                "label_window": f"{cutoff + 1}-{cutoff + 5}",
                "all_candidates": len(candidates),
                "positive_transfers": int(candidates.future_edge_label.sum()),
                "sampled_training_rows": len(sampled),
            }
        )
    train = pd.concat(windows, ignore_index=True)
    x_train = train[pipeline.FEATURES].fillna(0).to_numpy()
    y_train = train.future_edge_label.astype(int).to_numpy()
    params = {
        "iterations": 500,
        "learning_rate": 0.03,
        "depth": 5,
        "l2_leaf_reg": 3.0,
    }
    model = mechanism.model(params)
    model.fit(
        x_train,
        y_train,
        sample_weight=compute_sample_weight("balanced", y_train),
    )

    future = mechanism.mechanism_only(
        pipeline.make_candidates(
            ite_mapping, tg_mapping, vocab, embeddings, 2026, 2031
        )
    )
    x_future = future[pipeline.FEATURES].fillna(0).to_numpy()
    cat_probability = model.predict_proba(x_future)[:, 1]
    cat_rank = pipeline.rank_pct(cat_probability)
    graph_rank = pipeline.rank_pct(mechanism.graph_score(future))
    future["catboost_probability"] = cat_probability
    future["catboost_rank"] = cat_rank
    future["original_graph_rank"] = graph_rank
    future["final_score"] = 0.98 * cat_rank + 0.02 * graph_rank
    future["candidate_status"] = "not_observed_in_TG_through_2026"
    future = future.sort_values("final_score", ascending=False).reset_index(drop=True)
    future["future_rank"] = np.arange(1, len(future) + 1)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "five_year_training_windows.csv", index=False)
    train.to_csv(OUT / "five_year_training_samples.csv", index=False)
    future.to_csv(OUT / "future_mechanism_candidates.csv", index=False)
    future.head(100).to_csv(OUT / "future_mechanism_top100.csv", index=False)
    print(summary.to_string(index=False))
    print(
        "\ntraining rows",
        len(train),
        "positives",
        int(y_train.sum()),
        "future candidates",
        len(future),
    )
    print(
        future.head(15)[
            ["future_rank", "concept_u", "concept_v", "final_score"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
