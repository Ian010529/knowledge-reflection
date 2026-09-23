from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/ryan/Documents/iTE&TG")
OUT = ROOT / "minimal_clean_predictions" / "comparison"
OUT.mkdir(exist_ok=True)


def normalize_old(frame: pd.DataFrame, merge: pd.DataFrame) -> pd.DataFrame:
    lookup = merge.set_index("source_concept_id")[
        ["target_concept_id", "target_concept"]
    ].to_dict(orient="index")
    result = frame.copy()
    for side in ["u", "v"]:
        ids = []
        labels = []
        for concept_id, label in zip(
            result[f"concept_{side}_id"], result[f"concept_{side}"]
        ):
            target = lookup.get(concept_id)
            ids.append(target["target_concept_id"] if target else concept_id)
            labels.append(target["target_concept"] if target else label)
        result[f"concept_{side}_id"] = ids
        result[f"concept_{side}"] = labels
    return result[result["concept_u_id"] != result["concept_v_id"]]


def add_key(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["pair_key"] = [
        "|".join(sorted((left, right)))
        for left, right in zip(result["concept_u_id"], result["concept_v_id"])
    ]
    return result.sort_values("hybrid_score", ascending=False).drop_duplicates(
        "pair_key"
    )


def compare_task(
    task: str,
    old_path: Path,
    new_path: Path,
    merge: pd.DataFrame,
    primary_score: str,
) -> dict:
    old = add_key(normalize_old(pd.read_csv(old_path), merge))
    new = add_key(pd.read_csv(new_path))
    joined = old[
        ["pair_key", "future_edge_label", primary_score, "concept_u", "concept_v"]
    ].merge(
        new[
            ["pair_key", "future_edge_label", primary_score, "concept_u", "concept_v"]
        ],
        on="pair_key",
        how="outer",
        suffixes=("_old", "_clean"),
        indicator=True,
    )
    joined["label_changed"] = (
        joined["_merge"].eq("both")
        & joined["future_edge_label_old"].ne(joined["future_edge_label_clean"])
    )
    joined.to_csv(OUT / f"{task}_candidate_label_comparison.csv", index=False)

    rows = []
    for k in [10, 25, 50, 100]:
        old_top = set(old.nlargest(k, primary_score)["pair_key"])
        new_top = set(new.nlargest(k, primary_score)["pair_key"])
        rows.append(
            {
                "task": task,
                "k": k,
                "overlap_count": len(old_top & new_top),
                "overlap_fraction": len(old_top & new_top) / k,
            }
        )
    pd.DataFrame(rows).to_csv(OUT / f"{task}_topk_stability.csv", index=False)
    return {
        "task": task,
        "old_candidates_after_family_normalization": int(len(old)),
        "clean_candidates": int(len(new)),
        "shared_candidates": int((joined["_merge"] == "both").sum()),
        "removed_candidates": int((joined["_merge"] == "left_only").sum()),
        "new_candidates": int((joined["_merge"] == "right_only").sum()),
        "changed_labels_among_shared": int(joined["label_changed"].sum()),
        "top25_overlap": rows[1]["overlap_count"],
        "top25_overlap_fraction": rows[1]["overlap_fraction"],
    }


def main() -> None:
    merge = pd.read_csv(
        ROOT / "minimal_clean_concept_layer" / "prediction_family_merge_map.csv"
    )
    summaries = [
        compare_task(
            "ite_to_tg",
            ROOT
            / "ite_to_tg_prediction"
            / "ite_to_tg_scored_candidates_2022_to_2026.csv",
            ROOT
            / "minimal_clean_predictions"
            / "ite_to_tg"
            / "ite_to_tg_scored_candidates_2022_to_2026.csv",
            merge,
            "hybrid_score",
        ),
        compare_task(
            "tg_to_tg",
            ROOT
            / "tg_self_prediction"
            / "tg_self_scored_candidates_2022_to_2026.csv",
            ROOT
            / "minimal_clean_predictions"
            / "tg_to_tg"
            / "tg_self_scored_candidates_2022_to_2026.csv",
            merge,
            "graph_score",
        ),
    ]
    pd.DataFrame(summaries).to_csv(OUT / "cleaning_stability_summary.csv", index=False)
    (OUT / "cleaning_stability_summary.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
