"""Apply a transparent post-hoc sentence review to the clean-room focus paths.

This stage never changes extraction, automated G grades, candidate IDs, known-case
status, or cross-paper compatibility.  It only asks whether each machine strict-
syntax source--predicate--target triple is directly entailed by its original
sentence.  The adjudication file is separate, exhaustive for the focus A/B
relations, and remains pending human confirmation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cleanroom_abstract_pair_layer"


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def split_ids(value: object) -> list[str]:
    return [part.strip() for part in clean(value).split(";") if part.strip()]


def json_default(value: object) -> object:
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def side_review(ids: list[str], verdict_lookup: dict[str, str]) -> tuple[int, str]:
    if not ids:
        return 1, "cooccurrence_only"
    verdicts = [verdict_lookup.get(relation_id, "pending") for relation_id in ids]
    if "accepted" in verdicts:
        return 2, "direct_sentence_relation_accepted"
    if all(verdict == "rejected" for verdict in verdicts):
        return 1, "machine_relation_rejected_retain_cooccurrence_only"
    return 2, "strict_syntax_pending_semantic_review"


def reviewed_grade(ite_level: int, tg_level: int) -> tuple[str, int]:
    floor = min(ite_level, tg_level)
    ceiling = max(ite_level, tg_level)
    if floor >= 2:
        return "R2_dual_direct_sentence_relations", 1
    if ceiling >= 2:
        return "R1_single_direct_sentence_relation", 2
    return "R0_cooccurrence_only_or_rejected", 3


def main() -> None:
    candidates = pd.read_csv(
        OUT / "tiered_shared_node_pair_candidates_focus.csv", low_memory=False
    )
    nodes = pd.read_csv(OUT / "shared_node_evidence_summary.csv", low_memory=False)
    incidence_queue = pd.read_csv(
        OUT / "relation_incident_review_queue.csv", low_memory=False
    )
    adjudication = pd.read_csv(
        OUT / "relation_semantic_adjudication.csv", low_memory=False
    )
    verdict_lookup = adjudication.set_index("relation_id")[
        "semantic_verdict"
    ].to_dict()

    ite_levels: list[int] = []
    tg_levels: list[int] = []
    ite_statuses: list[str] = []
    tg_statuses: list[str] = []
    reviewed_grades: list[str] = []
    reviewed_grade_orders: list[int] = []
    reviewed_floors: list[int] = []
    reviewed_ceilings: list[int] = []
    for row in candidates.itertuples(index=False):
        ite_level, ite_status = side_review(
            split_ids(row.ite_strict_relation_ids), verdict_lookup
        )
        tg_level, tg_status = side_review(
            split_ids(row.tg_strict_relation_ids), verdict_lookup
        )
        grade, grade_order = reviewed_grade(ite_level, tg_level)
        ite_levels.append(ite_level)
        tg_levels.append(tg_level)
        ite_statuses.append(ite_status)
        tg_statuses.append(tg_status)
        reviewed_grades.append(grade)
        reviewed_grade_orders.append(grade_order)
        reviewed_floors.append(min(ite_level, tg_level))
        reviewed_ceilings.append(max(ite_level, tg_level))

    reviewed = candidates.copy()
    reviewed.insert(2, "review_adjusted_evidence_grade", reviewed_grades)
    reviewed.insert(3, "review_adjusted_evidence_grade_order", reviewed_grade_orders)
    reviewed.insert(4, "review_adjusted_ite_side_level", ite_levels)
    reviewed.insert(5, "review_adjusted_tg_side_level", tg_levels)
    reviewed.insert(6, "review_adjusted_evidence_floor", reviewed_floors)
    reviewed.insert(7, "review_adjusted_evidence_ceiling", reviewed_ceilings)
    reviewed.insert(8, "ite_semantic_relation_review_status", ite_statuses)
    reviewed.insert(9, "tg_semantic_relation_review_status", tg_statuses)
    reviewed.insert(10, "semantic_review_scope", "incident_relation_sentence_only")
    reviewed.insert(11, "semantic_reviewer_type", "independent_AI_sentence_audit")
    reviewed.insert(12, "human_confirmation_status", "pending")
    reviewed["cross_endpoint_evaluation_status"] = "not_tested"
    reviewed["scientific_claim_status"] = "retrieval_candidate_only"

    support_columns = [
        "shared_global_concept_id",
        "review_adjusted_evidence_floor",
        "review_adjusted_evidence_ceiling",
        "minimum_relation_support",
        "total_relation_support",
        "minimum_pair_paper_count",
        "sum_pair_paper_count",
        "minimum_pair_sentence_count",
        "sum_pair_sentence_count",
        "ite_pair_id",
        "tg_pair_id",
    ]
    support_sorted = reviewed.sort_values(
        support_columns,
        ascending=[
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            True,
        ],
    )
    within_rank = support_sorted.groupby("shared_global_concept_id").cumcount() + 1
    reviewed["review_adjusted_within_shared_node_rank"] = within_rank.reindex(
        reviewed.index
    ).astype(int)
    reviewed = reviewed.sort_values(
        [
            "review_adjusted_evidence_grade_order",
            "shared_global_concept_id",
            "ite_pair_id",
            "tg_pair_id",
        ]
    ).reset_index(drop=True)
    reviewed.insert(0, "semantic_audit_order", range(1, len(reviewed) + 1))

    reviewed_groups = {
        key: group for key, group in reviewed.groupby("shared_global_concept_id")
    }
    reviewed_node_rows: list[dict[str, object]] = []
    for node in nodes.itertuples(index=False):
        group = reviewed_groups.get(node.shared_global_concept_id)
        if group is None or group.empty:
            best_grade = "Q_endpoint_quarantine_or_no_path"
            best_grade_order = 4
            best_candidate_id = ""
            counts: dict[str, int] = {}
        else:
            best_grade_order = int(
                group["review_adjusted_evidence_grade_order"].min()
            )
            best_row = group.sort_values(
                ["review_adjusted_within_shared_node_rank", "candidate_id"]
            ).iloc[0]
            best_grade = best_row["review_adjusted_evidence_grade"]
            best_candidate_id = best_row["candidate_id"]
            counts = group["review_adjusted_evidence_grade"].value_counts().to_dict()
        row = node._asdict()
        row.update(
            {
                "review_adjusted_best_evidence_grade": best_grade,
                "review_adjusted_best_evidence_grade_order": best_grade_order,
                "review_adjusted_best_candidate_id": best_candidate_id,
                "review_adjusted_R2_path_count": counts.get(
                    "R2_dual_direct_sentence_relations", 0
                ),
                "review_adjusted_R1_path_count": counts.get(
                    "R1_single_direct_sentence_relation", 0
                ),
                "review_adjusted_R0_path_count": counts.get(
                    "R0_cooccurrence_only_or_rejected", 0
                ),
                "human_confirmation_status": "pending",
                "cross_endpoint_evaluation_status": "not_tested",
            }
        )
        reviewed_node_rows.append(row)
    reviewed_nodes = pd.DataFrame(reviewed_node_rows).sort_values(
        "shared_global_concept_id"
    )

    incidence_adjudication = incidence_queue.merge(
        adjudication,
        on=["relation_id", "paper_id"],
        how="left",
        validate="many_to_one",
    )

    baseline_grade_counts = reviewed["review_adjusted_evidence_grade"].value_counts()
    paper_relation_ids = (
        adjudication.groupby("paper_id")["relation_id"]
        .agg(lambda values: set(values))
        .to_dict()
    )
    sensitivity_rows: list[dict[str, object]] = []
    for removed_paper_id in sorted(paper_relation_ids):
        removed_relation_ids = paper_relation_ids[removed_paper_id]
        counterfactual_grades: list[str] = []
        counterfactual_r2_ids: list[str] = []
        for row in candidates.itertuples(index=False):
            ite_ids = [
                relation_id
                for relation_id in split_ids(row.ite_strict_relation_ids)
                if relation_id not in removed_relation_ids
            ]
            tg_ids = [
                relation_id
                for relation_id in split_ids(row.tg_strict_relation_ids)
                if relation_id not in removed_relation_ids
            ]
            ite_level, _ = side_review(ite_ids, verdict_lookup)
            tg_level, _ = side_review(tg_ids, verdict_lookup)
            grade, _ = reviewed_grade(ite_level, tg_level)
            counterfactual_grades.append(grade)
            if grade == "R2_dual_direct_sentence_relations":
                counterfactual_r2_ids.append(row.candidate_id)
        counterfactual_counts = pd.Series(counterfactual_grades).value_counts()
        sensitivity_rows.append(
            {
                "removed_paper_id": removed_paper_id,
                "removed_relation_ids": "; ".join(sorted(removed_relation_ids)),
                "baseline_R2_path_count": int(
                    baseline_grade_counts.get(
                        "R2_dual_direct_sentence_relations", 0
                    )
                ),
                "after_removal_R2_path_count": int(
                    counterfactual_counts.get(
                        "R2_dual_direct_sentence_relations", 0
                    )
                ),
                "baseline_R1_path_count": int(
                    baseline_grade_counts.get(
                        "R1_single_direct_sentence_relation", 0
                    )
                ),
                "after_removal_R1_path_count": int(
                    counterfactual_counts.get(
                        "R1_single_direct_sentence_relation", 0
                    )
                ),
                "baseline_R0_path_count": int(
                    baseline_grade_counts.get(
                        "R0_cooccurrence_only_or_rejected", 0
                    )
                ),
                "after_removal_R0_path_count": int(
                    counterfactual_counts.get(
                        "R0_cooccurrence_only_or_rejected", 0
                    )
                ),
                "remaining_R2_candidate_ids": "; ".join(
                    sorted(counterfactual_r2_ids)
                ),
                "sensitivity_scope": "remove_this_papers_accepted_relation_evidence_only_pairs_remain_as_cooccurrence",
                "identity_used_for_baseline_grade_or_rank": False,
            }
        )
    sensitivity = pd.DataFrame(sensitivity_rows)

    used_relation_ids = set()
    for column in ["ite_strict_relation_ids", "tg_strict_relation_ids"]:
        for value in candidates[column]:
            used_relation_ids.update(split_ids(value))
    adjudicated_ids = set(adjudication["relation_id"])
    incidence_relation_ids = set(incidence_queue["relation_id"])
    grade_logic_failures = 0
    for row in reviewed.itertuples(index=False):
        expected_grade, _ = reviewed_grade(
            int(row.review_adjusted_ite_side_level),
            int(row.review_adjusted_tg_side_level),
        )
        if row.review_adjusted_evidence_grade != expected_grade:
            grade_logic_failures += 1
    qa_checks = {
        "adjudication_relation_ids_are_unique": adjudication["relation_id"].is_unique,
        "all_focus_strict_relation_ids_are_adjudicated": used_relation_ids
        <= adjudicated_ids,
        "adjudication_contains_no_unreferenced_relation_ids": adjudicated_ids
        <= incidence_relation_ids,
        "all_verdicts_are_accepted_or_rejected": adjudication[
            "semantic_verdict"
        ].isin(["accepted", "rejected"]).all(),
        "identity_was_not_used_in_any_verdict": (~adjudication[
            "identity_used_in_verdict"
        ].astype(bool)).all(),
        "no_AI_adjudication_is_promoted_to_production_graph": (~adjudication[
            "production_graph_eligible"
        ].astype(bool)).all(),
        "human_confirmation_remains_pending": adjudication[
            "human_confirmation_status"
        ].eq("pending").all(),
        "candidate_population_is_unchanged": len(reviewed) == len(candidates)
        and set(reviewed["candidate_id"]) == set(candidates["candidate_id"]),
        "review_adjusted_grade_logic_is_reproducible": grade_logic_failures == 0,
        "cross_endpoint_evaluation_remains_not_tested": reviewed[
            "cross_endpoint_evaluation_status"
        ].eq("not_tested").all(),
        "leave_one_source_out_covers_every_adjudicated_paper": len(sensitivity)
        == adjudication["paper_id"].nunique(),
    }
    qa = {
        "contract": "posthoc_sentence_semantics_only_not_human_confirmation_or_cross_paper_compatibility",
        "all_checks_pass": all(bool(value) for value in qa_checks.values()),
        "checks": qa_checks,
        "failure_counts": {
            "missing_adjudication_relation_ids": sorted(
                used_relation_ids - adjudicated_ids
            ),
            "unreferenced_adjudication_relation_ids": sorted(
                adjudicated_ids - incidence_relation_ids
            ),
            "duplicate_adjudication_relation_ids": int(
                adjudication["relation_id"].duplicated().sum()
            ),
            "grade_logic_failures": grade_logic_failures,
        },
        "counts": {
            "adjudicated_unique_relations": len(adjudication),
            "accepted_unique_relations": int(
                adjudication["semantic_verdict"].eq("accepted").sum()
            ),
            "rejected_unique_relations": int(
                adjudication["semantic_verdict"].eq("rejected").sum()
            ),
            "reviewed_focus_paths": len(reviewed),
            "R2_dual_direct_sentence_relation_paths": int(
                reviewed["review_adjusted_evidence_grade"]
                .eq("R2_dual_direct_sentence_relations")
                .sum()
            ),
            "R1_single_direct_sentence_relation_paths": int(
                reviewed["review_adjusted_evidence_grade"]
                .eq("R1_single_direct_sentence_relation")
                .sum()
            ),
            "R0_cooccurrence_or_rejected_paths": int(
                reviewed["review_adjusted_evidence_grade"]
                .eq("R0_cooccurrence_only_or_rejected")
                .sum()
            ),
        },
    }

    reviewed.to_csv(OUT / "semantic_reviewed_focus_candidates.csv", index=False)
    reviewed_nodes.to_csv(
        OUT / "semantic_reviewed_shared_node_summary.csv", index=False
    )
    incidence_adjudication.to_csv(
        OUT / "relation_incident_semantic_review.csv", index=False
    )
    sensitivity.to_csv(
        OUT / "semantic_relation_source_leave_one_out.csv", index=False
    )
    (OUT / "semantic_review_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )
    if not qa["all_checks_pass"]:
        raise AssertionError("Semantic adjudication QA failed")
    print(json.dumps(qa["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
