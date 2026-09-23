from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from collections import defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import average_precision_score, roc_auc_score


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "minimal_clean_concept_layer"
FLOW = ROOT / "mechanism_transfer_workflow"
DEFAULT_OUT = FLOW / "strict_analysis"
RANDOM_STATE = 27
SCRIPT_VERSION = "1.0.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a stricter, descriptive mechanism co-occurrence diffusion "
            "analysis with explicit residual-limitations reporting."
        )
    )
    parser.add_argument(
        "--complete-through",
        type=int,
        default=2025,
        help="Last year treated as a complete observation year (default: 2025).",
    )
    parser.add_argument(
        "--support-papers",
        type=int,
        default=2,
        help="Independent source papers required before a pair is supported.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory. Existing legacy outputs are never overwritten.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    vocab = pd.read_csv(FLOW / "pure_mechanism_vocabulary.csv")
    mapping = pd.read_csv(DATA / "final_paper_concept_map.csv")
    papers = pd.read_csv(DATA / "final_paper_index.csv")
    papers["year"] = pd.to_numeric(papers["year"], errors="coerce")
    pure_ids = set(vocab["concept_id"])
    mapping = mapping[mapping["concept_id"].isin(pure_ids)].merge(
        papers[["paper_id", "year", "source_membership", "title"]],
        on="paper_id",
        how="left",
    )
    mapping = mapping[mapping["year"].notna()].copy()
    mapping["year"] = mapping["year"].astype(int)
    return vocab, mapping, papers


def pair_evidence(mapping: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for paper_id, group in mapping.groupby("paper_id", sort=True):
        concepts = sorted(group["concept_id"].dropna().unique())
        if len(concepts) < 2:
            continue
        year = int(group["year"].iloc[0])
        title = str(group["title"].iloc[0])
        membership = str(group["source_membership"].iloc[0])
        for u, v in combinations(concepts, 2):
            rows.append(
                {
                    "concept_u_id": u,
                    "concept_v_id": v,
                    "year": year,
                    "paper_id": paper_id,
                    "title": title,
                    "source_membership": membership,
                }
            )
    return pd.DataFrame(rows)


def evidence_summary(evidence: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if evidence.empty:
        return pd.DataFrame(
            columns=[
                "concept_u_id",
                "concept_v_id",
                f"{prefix}_first_year",
                f"{prefix}_last_year",
                f"{prefix}_evidence_papers",
                f"{prefix}_first_evidence_paper",
            ]
        )
    ordered = evidence.sort_values(
        ["concept_u_id", "concept_v_id", "year", "paper_id"]
    )
    return (
        ordered.groupby(["concept_u_id", "concept_v_id"], as_index=False)
        .agg(
            **{
                f"{prefix}_first_year": ("year", "min"),
                f"{prefix}_last_year": ("year", "max"),
                f"{prefix}_evidence_papers": ("paper_id", "nunique"),
                f"{prefix}_first_evidence_paper": ("paper_id", "first"),
            }
        )
        .sort_values(["concept_u_id", "concept_v_id"])
    )


def support_years(evidence: pd.DataFrame, threshold: int) -> pd.DataFrame:
    if evidence.empty:
        return pd.DataFrame(
            columns=["concept_u_id", "concept_v_id", "source_support_year"]
        )
    ordered = evidence.sort_values(
        ["concept_u_id", "concept_v_id", "year", "paper_id"]
    ).drop_duplicates(["concept_u_id", "concept_v_id", "paper_id"])
    ordered["evidence_order"] = (
        ordered.groupby(["concept_u_id", "concept_v_id"]).cumcount() + 1
    )
    return ordered[ordered["evidence_order"].eq(threshold)][
        ["concept_u_id", "concept_v_id", "year"]
    ].rename(columns={"year": "source_support_year"})


def build_event_table(
    source_evidence: pd.DataFrame,
    target_evidence: pd.DataFrame,
    vocab: pd.DataFrame,
    support_threshold: int,
) -> pd.DataFrame:
    source = evidence_summary(source_evidence, "source")
    target = evidence_summary(target_evidence, "target")
    support = support_years(source_evidence, support_threshold)
    events = source.merge(
        target, on=["concept_u_id", "concept_v_id"], how="outer"
    ).merge(support, on=["concept_u_id", "concept_v_id"], how="left")

    labels = vocab.set_index("concept_id")["canonical_concept"].to_dict()
    types = vocab.set_index("concept_id")["concept_type"].to_dict()
    events["concept_u"] = events["concept_u_id"].map(labels)
    events["concept_v"] = events["concept_v_id"].map(labels)
    events["u_type"] = events["concept_u_id"].map(types)
    events["v_type"] = events["concept_v_id"].map(types)
    events["type_pair"] = events.apply(
        lambda row: " + ".join(sorted([str(row["u_type"]), str(row["v_type"])])),
        axis=1,
    )

    source_year = events["source_support_year"]
    target_year = events["target_first_year"]
    conditions = [
        source_year.isna(),
        target_year.isna(),
        target_year < source_year,
        target_year == source_year,
        target_year > source_year,
    ]
    choices = [
        "target_only_or_insufficient_source_support",
        "source_supported_not_in_target",
        "target_before_source_support",
        "same_year_as_source_support",
        "source_supported_then_target",
    ]
    events["diffusion_status"] = np.select(
        conditions, choices, default="unclassified"
    )
    events["lag_years"] = np.where(
        events["diffusion_status"].eq("source_supported_then_target"),
        target_year - source_year,
        np.nan,
    )
    events["source_support_threshold"] = support_threshold
    return events.sort_values(
        ["diffusion_status", "source_support_year", "target_first_year"]
    ).reset_index(drop=True)


def km_curve(
    durations: np.ndarray, observed: np.ndarray, support_threshold: int, scenario: str
) -> pd.DataFrame:
    rows = [
        {
            "scenario": scenario,
            "source_support_threshold": support_threshold,
            "years_since_source_support": 0,
            "at_risk": int(len(durations)),
            "events": 0,
            "censored": int(((durations == 0) & (~observed)).sum()),
            "survival_without_target_cooccurrence": 1.0,
            "cumulative_target_cooccurrence": 0.0,
        }
    ]
    survival = 1.0
    for time in sorted(set(int(value) for value in durations if value > 0)):
        at_risk = int((durations >= time).sum())
        events = int(((durations == time) & observed).sum())
        censored = int(((durations == time) & (~observed)).sum())
        if at_risk and events:
            survival *= 1.0 - events / at_risk
        rows.append(
            {
                "scenario": scenario,
                "source_support_threshold": support_threshold,
                "years_since_source_support": time,
                "at_risk": at_risk,
                "events": events,
                "censored": censored,
                "survival_without_target_cooccurrence": survival,
                "cumulative_target_cooccurrence": 1.0 - survival,
            }
        )
    return pd.DataFrame(rows)


def value_at_horizon(curve: pd.DataFrame, horizon: int) -> float:
    eligible = curve[curve["years_since_source_support"] <= horizon]
    if eligible.empty:
        return 0.0
    return float(eligible.iloc[-1]["cumulative_target_cooccurrence"])


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return (np.nan, np.nan)
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    half = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total + z * z / (4 * total * total)
        )
        / denominator
    )
    return max(0.0, centre - half), min(1.0, centre + half)


def survival_outputs(
    source_evidence: pd.DataFrame,
    target_evidence: pd.DataFrame,
    vocab: pd.DataFrame,
    cutoff: int,
    scenario: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[int, pd.DataFrame]]:
    curves = []
    summaries = []
    fixed_horizon_rows = []
    event_tables: dict[int, pd.DataFrame] = {}
    for threshold in [1, 2, 3]:
        events = build_event_table(
            source_evidence, target_evidence, vocab, threshold
        )
        event_tables[threshold] = events
        at_risk = events[
            events["diffusion_status"].isin(
                [
                    "source_supported_not_in_target",
                    "source_supported_then_target",
                ]
            )
        ].copy()
        observed = at_risk["diffusion_status"].eq(
            "source_supported_then_target"
        ).to_numpy()
        durations = np.where(
            observed,
            at_risk["target_first_year"] - at_risk["source_support_year"],
            cutoff - at_risk["source_support_year"],
        ).astype(int)
        curve = km_curve(durations, observed, threshold, scenario)
        curves.append(curve)
        lags = at_risk.loc[observed, "lag_years"].dropna()
        summaries.append(
            {
                "scenario": scenario,
                "source_support_threshold": threshold,
                "source_supported_pairs_at_risk": len(at_risk),
                "observed_later_target_cooccurrences": int(observed.sum()),
                "right_censored_pairs": int((~observed).sum()),
                "naive_observed_fraction": float(observed.mean())
                if len(observed)
                else np.nan,
                "km_cumulative_at_1_year": value_at_horizon(curve, 1),
                "km_cumulative_at_3_years": value_at_horizon(curve, 3),
                "km_cumulative_at_5_years": value_at_horizon(curve, 5),
                "observed_event_median_lag": float(lags.median())
                if len(lags)
                else np.nan,
            }
        )

        complete = at_risk[
            at_risk["source_support_year"] <= cutoff - 5
        ].copy()
        complete["target_within_5y"] = (
            complete["target_first_year"].notna()
            & (complete["target_first_year"] > complete["source_support_year"])
            & (
                complete["target_first_year"]
                <= complete["source_support_year"] + 5
            )
        )
        successes = int(complete["target_within_5y"].sum())
        lower, upper = wilson_interval(successes, len(complete))
        fixed_horizon_rows.append(
            {
                "scenario": scenario,
                "source_support_threshold": threshold,
                "last_complete_year": cutoff,
                "latest_eligible_source_support_year": cutoff - 5,
                "complete_followup_pairs": len(complete),
                "target_cooccurrences_within_5y": successes,
                "five_year_fraction": successes / len(complete)
                if len(complete)
                else np.nan,
                "wilson_95_low": lower,
                "wilson_95_high": upper,
                "uncertainty_note": (
                    "Naive binomial interval; co-occurrence pairs share source "
                    "and target papers/nodes and are not independent."
                ),
            }
        )
    return (
        pd.concat(curves, ignore_index=True),
        pd.DataFrame(summaries),
        pd.DataFrame(fixed_horizon_rows),
        event_tables,
    )


def competing_risk_outputs(
    source_evidence: pd.DataFrame,
    target_evidence: pd.DataFrame,
    hybrid_evidence: pd.DataFrame,
    vocab: pd.DataFrame,
    cutoff: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, pd.DataFrame]]:
    target = evidence_summary(target_evidence, "target")
    hybrid = evidence_summary(hybrid_evidence, "hybrid")
    labels = vocab.set_index("concept_id")["canonical_concept"].to_dict()
    all_curves = []
    summaries = []
    pair_tables: dict[int, pd.DataFrame] = {}
    for threshold in [1, 2, 3]:
        support = support_years(source_evidence, threshold)
        pairs = support.merge(
            target[
                ["concept_u_id", "concept_v_id", "target_first_year"]
            ],
            on=["concept_u_id", "concept_v_id"],
            how="left",
        ).merge(
            hybrid[
                ["concept_u_id", "concept_v_id", "hybrid_first_year"]
            ],
            on=["concept_u_id", "concept_v_id"],
            how="left",
        )
        pairs["concept_u"] = pairs["concept_u_id"].map(labels)
        pairs["concept_v"] = pairs["concept_v_id"].map(labels)
        pairs["eligible_at_origin"] = (
            (
                pairs["target_first_year"].isna()
                | (pairs["target_first_year"] > pairs["source_support_year"])
            )
            & (
                pairs["hybrid_first_year"].isna()
                | (pairs["hybrid_first_year"] > pairs["source_support_year"])
            )
        )
        eligible = pairs[pairs["eligible_at_origin"]].copy()
        target_lag = eligible["target_first_year"] - eligible["source_support_year"]
        hybrid_lag = eligible["hybrid_first_year"] - eligible["source_support_year"]
        event_type = []
        duration = []
        for target_time, hybrid_time, support_year in zip(
            target_lag,
            hybrid_lag,
            eligible["source_support_year"],
        ):
            if pd.isna(target_time) and pd.isna(hybrid_time):
                event_type.append("right_censored")
                duration.append(int(cutoff - support_year))
            elif pd.isna(hybrid_time) or (
                pd.notna(target_time) and target_time < hybrid_time
            ):
                event_type.append("exclusive_TG_cooccurrence")
                duration.append(int(target_time))
            elif pd.isna(target_time) or hybrid_time < target_time:
                event_type.append("hybrid_bridge_cooccurrence")
                duration.append(int(hybrid_time))
            else:
                event_type.append("same_year_TG_and_hybrid")
                duration.append(int(target_time))
        eligible["event_type"] = event_type
        eligible["duration_years"] = duration
        eligible["source_support_threshold"] = threshold
        pair_tables[threshold] = eligible.sort_values(
            ["duration_years", "event_type", "concept_u_id", "concept_v_id"]
        )

        survival = 1.0
        cif_target = 0.0
        cif_hybrid = 0.0
        cif_ambiguous = 0.0
        curve_rows = [
            {
                "source_support_threshold": threshold,
                "years_since_source_support": 0,
                "at_risk": len(eligible),
                "exclusive_TG_events": 0,
                "hybrid_bridge_events": 0,
                "same_year_ambiguous_events": 0,
                "censored": int(
                    (
                        eligible["event_type"].eq("right_censored")
                        & eligible["duration_years"].eq(0)
                    ).sum()
                ),
                "event_free_survival": survival,
                "cif_exclusive_TG": cif_target,
                "cif_hybrid_bridge": cif_hybrid,
                "cif_same_year_ambiguous": cif_ambiguous,
            }
        ]
        event_times = sorted(
            eligible.loc[
                ~eligible["event_type"].eq("right_censored"), "duration_years"
            ]
            .astype(int)
            .unique()
        )
        all_times = sorted(
            set(event_times)
            | set(
                eligible.loc[
                    eligible["event_type"].eq("right_censored"),
                    "duration_years",
                ]
                .astype(int)
                .tolist()
            )
        )
        for time in (value for value in all_times if value > 0):
            at_risk = int((eligible["duration_years"] >= time).sum())
            target_events = int(
                (
                    eligible["duration_years"].eq(time)
                    & eligible["event_type"].eq("exclusive_TG_cooccurrence")
                ).sum()
            )
            hybrid_events = int(
                (
                    eligible["duration_years"].eq(time)
                    & eligible["event_type"].eq("hybrid_bridge_cooccurrence")
                ).sum()
            )
            ambiguous_events = int(
                (
                    eligible["duration_years"].eq(time)
                    & eligible["event_type"].eq("same_year_TG_and_hybrid")
                ).sum()
            )
            censored = int(
                (
                    eligible["duration_years"].eq(time)
                    & eligible["event_type"].eq("right_censored")
                ).sum()
            )
            total_events = target_events + hybrid_events + ambiguous_events
            if at_risk:
                cif_target += survival * target_events / at_risk
                cif_hybrid += survival * hybrid_events / at_risk
                cif_ambiguous += survival * ambiguous_events / at_risk
                survival *= 1 - total_events / at_risk
            curve_rows.append(
                {
                    "source_support_threshold": threshold,
                    "years_since_source_support": time,
                    "at_risk": at_risk,
                    "exclusive_TG_events": target_events,
                    "hybrid_bridge_events": hybrid_events,
                    "same_year_ambiguous_events": ambiguous_events,
                    "censored": censored,
                    "event_free_survival": survival,
                    "cif_exclusive_TG": cif_target,
                    "cif_hybrid_bridge": cif_hybrid,
                    "cif_same_year_ambiguous": cif_ambiguous,
                }
            )
        curve = pd.DataFrame(curve_rows)
        all_curves.append(curve)
        for horizon in [1, 3, 5]:
            available = curve[curve["years_since_source_support"] <= horizon]
            row = available.iloc[-1]
            summaries.append(
                {
                    "source_support_threshold": threshold,
                    "horizon_years": horizon,
                    "eligible_pairs": len(eligible),
                    "cif_exclusive_TG": row["cif_exclusive_TG"],
                    "cif_hybrid_bridge": row["cif_hybrid_bridge"],
                    "cif_same_year_ambiguous": row["cif_same_year_ambiguous"],
                    "event_free_survival": row["event_free_survival"],
                }
            )
    return (
        pd.concat(all_curves, ignore_index=True),
        pd.DataFrame(summaries),
        pair_tables,
    )


def five_year_type_rates(
    events: pd.DataFrame, cutoff: int, scenario: str
) -> pd.DataFrame:
    at_risk = events[
        events["diffusion_status"].isin(
            ["source_supported_not_in_target", "source_supported_then_target"]
        )
        & (events["source_support_year"] <= cutoff - 5)
    ].copy()
    at_risk["target_within_5y"] = (
        at_risk["target_first_year"].notna()
        & (at_risk["target_first_year"] > at_risk["source_support_year"])
        & (
            at_risk["target_first_year"]
            <= at_risk["source_support_year"] + 5
        )
    )
    rows = []
    for type_pair, group in at_risk.groupby("type_pair"):
        successes = int(group["target_within_5y"].sum())
        lower, upper = wilson_interval(successes, len(group))
        rows.append(
            {
                "scenario": scenario,
                "type_pair": type_pair,
                "complete_followup_pairs": len(group),
                "target_cooccurrences_within_5y": successes,
                "five_year_fraction": successes / len(group),
                "wilson_95_low": lower,
                "wilson_95_high": upper,
                "uncertainty_note": (
                    "Naive binomial interval; co-occurrence pairs share source "
                    "and target papers/nodes and are not independent."
                ),
                "reporting_status": (
                    "descriptive_only_small_n"
                    if len(group) < 10
                    else "descriptive"
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["complete_followup_pairs", "type_pair"], ascending=[False, True]
    )


def counts_by_pair(
    evidence: pd.DataFrame, end_year: int, start_year: int | None = None
) -> dict[tuple[str, str], int]:
    subset = evidence[evidence["year"] <= end_year]
    if start_year is not None:
        subset = subset[subset["year"] >= start_year]
    return (
        subset.groupby(["concept_u_id", "concept_v_id"])["paper_id"]
        .nunique()
        .to_dict()
    )


def node_counts(
    mapping: pd.DataFrame, end_year: int
) -> dict[str, int]:
    return (
        mapping[mapping["year"] <= end_year]
        .groupby("concept_id")["paper_id"]
        .nunique()
        .to_dict()
    )


def adjacency(edges: set[tuple[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for u, v in edges:
        result[u].add(v)
        result[v].add(u)
    return result


def percentile(values: pd.Series) -> np.ndarray:
    return values.rank(method="average", pct=True).to_numpy()


def annual_relation_risk_set(
    source_evidence: pd.DataFrame,
    target_evidence: pd.DataFrame,
    target_mapping: pd.DataFrame,
    vocab: pd.DataFrame,
    cutoff: int,
    support_threshold: int,
) -> pd.DataFrame:
    source_counts = counts_by_pair(source_evidence, cutoff)
    source_recent = counts_by_pair(source_evidence, cutoff, cutoff - 2)
    target_counts = counts_by_pair(target_evidence, cutoff)
    target_next = set(
        zip(
            target_evidence.loc[
                target_evidence["year"].eq(cutoff + 1), "concept_u_id"
            ],
            target_evidence.loc[
                target_evidence["year"].eq(cutoff + 1), "concept_v_id"
            ],
        )
    )
    target_node_counts = node_counts(target_mapping, cutoff)
    target_adj = adjacency(set(target_counts))
    labels = vocab.set_index("concept_id")["canonical_concept"].to_dict()
    types = vocab.set_index("concept_id")["concept_type"].to_dict()
    rows = []
    for (u, v), count in sorted(source_counts.items()):
        if count < support_threshold:
            continue
        if (u, v) in target_counts:
            continue
        if target_node_counts.get(u, 0) == 0 or target_node_counts.get(v, 0) == 0:
            continue
        neighbors_u = target_adj.get(u, set())
        neighbors_v = target_adj.get(v, set())
        common = neighbors_u & neighbors_v
        union = neighbors_u | neighbors_v
        frequency_u = target_node_counts[u]
        frequency_v = target_node_counts[v]
        rows.append(
            {
                "concept_u_id": u,
                "concept_v_id": v,
                "concept_u": labels.get(u, u),
                "concept_v": labels.get(v, v),
                "u_type": types.get(u, ""),
                "v_type": types.get(v, ""),
                "cutoff_year": cutoff,
                "target_year": cutoff + 1,
                "source_pair_evidence_papers": count,
                "source_pair_recent_papers_3y": source_recent.get((u, v), 0),
                "target_frequency_u": frequency_u,
                "target_frequency_v": frequency_v,
                "target_frequency_min": min(frequency_u, frequency_v),
                "target_frequency_sum": frequency_u + frequency_v,
                "target_common_neighbors": len(common),
                "target_jaccard": len(common) / max(1, len(union)),
                "next_year_target_cooccurrence": int((u, v) in target_next),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    score_columns = [
        "source_pair_evidence_papers",
        "source_pair_recent_papers_3y",
        "target_frequency_min",
        "target_common_neighbors",
        "target_jaccard",
    ]
    rank_columns = []
    for column in score_columns:
        rank_column = f"{column}_rank"
        frame[rank_column] = percentile(frame[column])
        rank_columns.append(rank_column)
    frame["transparent_readiness_score"] = frame[rank_columns].mean(axis=1)
    frame["score_definition"] = (
        "Unweighted mean of within-year percentile ranks: source pair evidence, "
        "source 3-year recency, target minimum node frequency, target common "
        "neighbors, and target Jaccard"
    )
    return frame.sort_values(
        "transparent_readiness_score", ascending=False
    ).reset_index(drop=True)


def ranking_metrics(frame: pd.DataFrame, observation_status: str) -> dict:
    y = frame["next_year_target_cooccurrence"].astype(int).to_numpy()
    score = frame["transparent_readiness_score"].to_numpy()
    result = {
        "cutoff_year": int(frame["cutoff_year"].iloc[0]),
        "target_year": int(frame["target_year"].iloc[0]),
        "observation_status": observation_status,
        "candidates": len(frame),
        "positives": int(y.sum()),
        "positive_rate": float(y.mean()),
        "roc_auc": np.nan,
        "average_precision": np.nan,
        "ap_lift_over_prevalence": np.nan,
    }
    if len(np.unique(y)) == 2:
        result["roc_auc"] = roc_auc_score(y, score)
        result["average_precision"] = average_precision_score(y, score)
        result["ap_lift_over_prevalence"] = (
            result["average_precision"] / result["positive_rate"]
        )
    order = np.argsort(score)[::-1]
    for k in [5, 10, 25]:
        selected = order[: min(k, len(order))]
        result[f"hits_at_{k}"] = int(y[selected].sum())
        result[f"precision_at_{k}"] = (
            float(y[selected].mean()) if len(selected) else np.nan
        )
    return result


def bootstrap_metrics(
    frame: pd.DataFrame, repetitions: int = 2000
) -> pd.DataFrame:
    y = frame["next_year_target_cooccurrence"].astype(int).to_numpy()
    score = frame["transparent_readiness_score"].to_numpy()
    if len(np.unique(y)) < 2:
        return pd.DataFrame()
    rng = np.random.default_rng(RANDOM_STATE)
    rows = []
    for _ in range(repetitions):
        index = rng.integers(0, len(y), len(y))
        sampled_y = y[index]
        if len(np.unique(sampled_y)) < 2:
            continue
        sampled_score = score[index]
        prevalence = float(sampled_y.mean())
        ap = average_precision_score(sampled_y, sampled_score)
        rows.append(
            {
                "roc_auc": roc_auc_score(sampled_y, sampled_score),
                "average_precision": ap,
                "ap_lift_over_prevalence": ap / prevalence,
            }
        )
    if not rows:
        return pd.DataFrame()
    bootstrap = pd.DataFrame(rows)
    return pd.DataFrame(
        [
            {
                "metric": column,
                "bootstrap_valid_repetitions": len(bootstrap),
                "estimate": (
                    roc_auc_score(y, score)
                    if column == "roc_auc"
                    else (
                        average_precision_score(y, score)
                        if column == "average_precision"
                        else average_precision_score(y, score) / y.mean()
                    )
                ),
                "bootstrap_95_low": bootstrap[column].quantile(0.025),
                "bootstrap_95_high": bootstrap[column].quantile(0.975),
                "uncertainty_note": (
                    "Naive pair-row bootstrap; shared target papers and shared "
                    "mechanism nodes are not clustered."
                ),
            }
            for column in [
                "roc_auc",
                "average_precision",
                "ap_lift_over_prevalence",
            ]
        ]
    )


def old_graph_score(frame: pd.DataFrame) -> np.ndarray:
    def rank(column: str, reverse: bool = False) -> np.ndarray:
        values = -frame[column] if reverse else frame[column]
        return values.rank(method="average", pct=True).to_numpy()

    return (
        0.24 * rank("adamic_adar")
        + 0.18 * rank("common_neighbors")
        + 0.12 * rank("jaccard")
        + 0.12 * rank("preferential_attachment")
        + 0.12 * rank("shortest_path", reverse=True)
        + 0.12 * rank("semantic_similarity")
        + 0.10 * rank("recent_frequency_sum")
    )


def legacy_overlap_audit(
    all_target_evidence: pd.DataFrame,
    papers: pd.DataFrame,
    out: Path,
) -> pd.DataFrame:
    legacy_events_path = FLOW / "mechanism_pair_transfer_events.csv"
    risk_path = FLOW / "two_stage_model" / "pair_annual_risk_rows.csv"
    if not legacy_events_path.exists() or not risk_path.exists():
        return pd.DataFrame()

    membership = papers.set_index("paper_id")["source_membership"].to_dict()
    legacy_events = pd.read_csv(legacy_events_path)
    transfers = legacy_events[
        legacy_events["transfer_status"].eq("iTE_then_TG")
    ].copy()
    transfers["target_first_evidence_membership"] = transfers[
        "tg_first_evidence_paper"
    ].map(membership)
    overlap_transfers = transfers[
        transfers["target_first_evidence_membership"].eq("iTE|TG")
    ].copy()
    overlap_transfers.to_csv(
        out / "legacy_transfers_with_ambiguous_target_evidence.csv", index=False
    )

    first_target = (
        all_target_evidence.sort_values(["year", "paper_id"])
        .groupby(["concept_u_id", "concept_v_id"], as_index=False)
        .first()[
            [
                "concept_u_id",
                "concept_v_id",
                "year",
                "paper_id",
                "source_membership",
            ]
        ]
        .rename(
            columns={
                "year": "target_first_year",
                "paper_id": "target_first_paper",
                "source_membership": "target_first_membership",
            }
        )
    )
    risk = pd.read_csv(risk_path)
    risk = risk[risk["cutoff_year"].eq(2025)].copy()
    risk = risk.merge(
        first_target, on=["concept_u_id", "concept_v_id"], how="left"
    )
    risk["ambiguous_positive"] = (
        risk["label"].eq(1)
        & risk["target_first_year"].eq(2026)
        & risk["target_first_membership"].eq("iTE|TG")
    )
    score = old_graph_score(risk)
    y = risk["label"].astype(int).to_numpy()
    unambiguous = ~risk["ambiguous_positive"]
    clean_y = y[unambiguous]
    clean_score = score[unambiguous]
    rows = [
        {
            "audit": "legacy_claimed_transfers",
            "rows": len(transfers),
            "positives": len(transfers),
            "ambiguous_rows_or_positives": len(overlap_transfers),
            "ambiguous_fraction": len(overlap_transfers) / len(transfers),
            "roc_auc": np.nan,
            "average_precision": np.nan,
            "positive_rate": np.nan,
        },
        {
            "audit": "legacy_2025_to_2026_graph_all_labels",
            "rows": len(risk),
            "positives": int(y.sum()),
            "ambiguous_rows_or_positives": int(risk["ambiguous_positive"].sum()),
            "ambiguous_fraction": float(
                risk.loc[risk["label"].eq(1), "ambiguous_positive"].mean()
            ),
            "roc_auc": roc_auc_score(y, score),
            "average_precision": average_precision_score(y, score),
            "positive_rate": float(y.mean()),
        },
        {
            "audit": "legacy_2025_to_2026_graph_excluding_ambiguous_positives",
            "rows": int(unambiguous.sum()),
            "positives": int(clean_y.sum()),
            "ambiguous_rows_or_positives": 0,
            "ambiguous_fraction": 0.0,
            "roc_auc": roc_auc_score(clean_y, clean_score),
            "average_precision": average_precision_score(clean_y, clean_score),
            "positive_rate": float(clean_y.mean()),
        },
    ]
    return pd.DataFrame(rows)


def target_paper_concentration(
    events: pd.DataFrame, papers: pd.DataFrame
) -> pd.DataFrame:
    transfers = events[
        events["diffusion_status"].eq("source_supported_then_target")
    ].copy()
    concentration = (
        transfers.groupby("target_first_evidence_paper")
        .size()
        .rename("first_target_event_pairs")
        .reset_index()
        .sort_values(
            ["first_target_event_pairs", "target_first_evidence_paper"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )
    concentration = concentration.merge(
        papers[
            ["paper_id", "year", "title", "journal", "source_membership"]
        ].rename(columns={"paper_id": "target_first_evidence_paper"}),
        on="target_first_evidence_paper",
        how="left",
    )
    total = max(1, int(concentration["first_target_event_pairs"].sum()))
    concentration["event_pair_fraction"] = (
        concentration["first_target_event_pairs"] / total
    )
    concentration["cumulative_event_pair_fraction"] = concentration[
        "event_pair_fraction"
    ].cumsum()
    concentration["possible_review_title_flag"] = concentration[
        "title"
    ].str.contains(
        r"\b(?:review|perspective|overview|progress|advances|recent developments)\b",
        case=False,
        regex=True,
        na=False,
    )
    concentration["manual_article_type_and_relation_review_required"] = True
    return concentration


def relation_verification_queue(
    events: pd.DataFrame,
    source_evidence: pd.DataFrame,
    papers: pd.DataFrame,
) -> pd.DataFrame:
    paper_info = papers.set_index("paper_id")
    rows = []
    transfers = events[
        events["diffusion_status"].eq("source_supported_then_target")
    ].copy()
    for event in transfers.itertuples(index=False):
        source_rows = source_evidence[
            source_evidence["concept_u_id"].eq(event.concept_u_id)
            & source_evidence["concept_v_id"].eq(event.concept_v_id)
            & (source_evidence["year"] <= event.source_support_year)
        ].sort_values(["year", "paper_id"])
        source_ids = list(dict.fromkeys(source_rows["paper_id"]))
        source_titles = list(dict.fromkeys(source_rows["title"]))
        target_id = event.target_first_evidence_paper
        target_title = (
            paper_info.at[target_id, "title"]
            if target_id in paper_info.index
            else ""
        )
        target_journal = (
            paper_info.at[target_id, "journal"]
            if target_id in paper_info.index
            else ""
        )
        rows.append(
            {
                "concept_u_id": event.concept_u_id,
                "concept_v_id": event.concept_v_id,
                "concept_u": event.concept_u,
                "concept_v": event.concept_v,
                "source_support_year": event.source_support_year,
                "source_support_evidence_paper_ids": "; ".join(source_ids),
                "source_support_evidence_titles": " | ".join(source_titles),
                "target_first_year": event.target_first_year,
                "target_first_evidence_paper": target_id,
                "target_first_evidence_title": target_title,
                "target_first_evidence_journal": target_journal,
                "relation_evidence_standard": (
                    "Directly asserted mechanistic link in sentence/full text; "
                    "co-mention alone is insufficient."
                ),
                "source_direct_relation_verified": "",
                "target_direct_relation_verified": "",
                "target_article_type_verified_primary_research": "",
                "reviewer_1": "",
                "reviewer_2": "",
                "adjudication": "",
                "include_in_confirmatory_analysis": "",
                "verification_status": "pending_manual_dual_review",
            }
        )
    return pd.DataFrame(rows)


def add_candidate_evidence(
    candidates: pd.DataFrame,
    source_evidence: pd.DataFrame,
) -> pd.DataFrame:
    evidence = (
        source_evidence.sort_values(["year", "paper_id"])
        .groupby(["concept_u_id", "concept_v_id"])
        .agg(
            source_evidence_paper_ids=(
                "paper_id",
                lambda values: "; ".join(dict.fromkeys(values)),
            ),
            source_evidence_years=(
                "year",
                lambda values: "; ".join(str(value) for value in sorted(set(values))),
            ),
            source_evidence_titles=(
                "title",
                lambda values: " | ".join(dict.fromkeys(values)),
            ),
        )
        .reset_index()
    )
    return candidates.merge(
        evidence, on=["concept_u_id", "concept_v_id"], how="left"
    )


def write_readme(
    out: Path,
    cutoff: int,
    support_threshold: int,
    legacy_audit: pd.DataFrame,
    ranking: pd.DataFrame,
    gate_reasons: list[str],
) -> None:
    legacy_transfer_row = legacy_audit[
        legacy_audit["audit"].eq("legacy_claimed_transfers")
    ]
    legacy_text = ""
    if not legacy_transfer_row.empty:
        row = legacy_transfer_row.iloc[0]
        legacy_text = (
            f"- Of the legacy {int(row['positives'])} claimed transfers, "
            f"{int(row['ambiguous_rows_or_positives'])} used an `iTE|TG` paper "
            "as first target evidence.\n"
        )
    holdout = ranking[ranking["observation_status"].eq("complete_holdout")]
    holdout_text = "No eligible complete-year holdout was available."
    if not holdout.empty:
        row = holdout.iloc[0]
        holdout_text = (
            f"The {int(row['cutoff_year'])}→{int(row['target_year'])} complete "
            f"holdout contains {int(row['candidates'])} candidates and only "
            f"{int(row['positives'])} positive co-occurrences "
            f"(AUC={row['roc_auc']:.3f}, AP={row['average_precision']:.3f})."
        )
    text = f"""# Strict mechanism co-occurrence diffusion analysis

Generated by `scripts/run_strict_mechanism_diffusion.py`.

## Decision

**Do not present the current model as validated future prediction.** Use the
exclusive-domain, fixed-follow-up descriptive results as the primary analysis.
The ranked table is an unvalidated manual literature-audit queue, not a
probability forecast.

## Primary design

- Last complete observation year: **{cutoff}**.
- Source domain: papers whose membership is exactly `iTE`.
- Target domain: papers whose membership is exactly `TG`.
- `iTE|TG` papers are excluded from the primary analysis and included only in
  sensitivity/audit outputs; a separate competing-risk table treats hybrid
  co-occurrence as a bridge event competing with exclusive-TG co-occurrence.
- An edge means two curated mechanism concepts were annotated in the same
  paper. It is therefore called a **co-occurrence**, not a causal relation.
- Primary source support requires **{support_threshold} independent papers**.
- Five-year rates use only cohorts with a full five years of observable
  follow-up; Kaplan–Meier outputs retain right-censored pairs.

## Residual limitations that still require author curation

- The installed 68-node vocabulary was curated from the full corpus. It must
  be re-curated by domain experts while blinded to TG outcomes before formal
  inference.
- Paper-level concept cliques are not direct textual relations. Every retained
  event still needs sentence/full-text evidence and relation typing.
- Review/article type is not available as a reliable structured field. The
  target-paper concentration table is an audit list, not an automatic review
  exclusion.
- The source files are fixed-size retrieval exports; conclusions apply only
  to this frozen corpus unless search completeness is documented.
- Wilson and row-bootstrap intervals are diagnostic only because pairs share
  papers and nodes.

## Why the legacy workflow looked unreasonable

{legacy_text}- The 2025→2026 outcome used an incomplete 2026 observation year.
- Candidate edges were co-mentions, while output language implied mechanistic
  relations and calibrated probabilities.
- The latest figure depended on a ranking CSV with no repository script that
  generated it.

## Ranking validation

{holdout_text}

Deployment gate: **failed**.

Reasons:
{chr(10).join(f'- {reason}' for reason in gate_reasons)}

## Main files

- `strict_pair_events_support_{support_threshold}.csv`: primary exclusive-domain events.
- `paper_domain_counts.csv`: mutually exclusive corpus sizes at the freeze year.
- `domain_sensitivity_summary.csv`: exclusive versus hybrid-inclusive sensitivity.
- `kaplan_meier_cooccurrence.csv`: censoring-aware cumulative co-occurrence.
- `competing_risk_cumulative_incidence.csv`: exclusive-TG versus hybrid bridge
  cumulative incidence.
- `fixed_five_year_summary.csv`: fixed-follow-up estimates with Wilson intervals.
- `five_year_rates_by_type.csv`: family results with small-n flags.
- `target_first_evidence_paper_concentration.csv`: event clustering and manual
  article-type/full-text audit queue.
- `direct_relation_verification_queue.csv`: evidence-linked dual-review sheet;
  co-mentions are not confirmatory until this is completed.
- `walk_forward_ranking_metrics.csv`: complete and partial-year ranking checks.
- `prospective_candidate_audit_queue_after_{cutoff}.csv`: manual audit queue;
  scores are not probabilities and partial-next-year non-events remain censored.
- `legacy_overlap_contamination_audit.csv`: quantified legacy label ambiguity.
- `run_manifest.json`: parameters, software versions, and SHA-256 input hashes.

## Re-run

```bash
python3 scripts/run_strict_mechanism_diffusion.py --complete-through {cutoff}
```
"""
    (out / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    cutoff = args.complete_through
    support_threshold = args.support_papers
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    vocab, mapping, papers = load_data()
    source_exclusive = mapping[
        mapping["source_membership"].eq("iTE") & (mapping["year"] <= cutoff)
    ].copy()
    target_exclusive = mapping[
        mapping["source_membership"].eq("TG") & (mapping["year"] <= cutoff)
    ].copy()
    hybrid = mapping[
        mapping["source_membership"].eq("iTE|TG")
        & (mapping["year"] <= cutoff)
    ].copy()
    if not source_exclusive["source_membership"].eq("iTE").all():
        raise RuntimeError("Primary source contains a non-exclusive paper.")
    if not target_exclusive["source_membership"].eq("TG").all():
        raise RuntimeError("Primary target contains a non-exclusive paper.")
    primary_year_max = pd.concat(
        [
            source_exclusive[["year"]],
            target_exclusive[["year"]],
            hybrid[["year"]],
        ],
        ignore_index=True,
    )["year"].max()
    if pd.notna(primary_year_max) and primary_year_max > cutoff:
        raise RuntimeError("Primary analysis includes data after the freeze year.")

    source_all_years = mapping[mapping["source_membership"].eq("iTE")].copy()
    target_all_years = mapping[mapping["source_membership"].eq("TG")].copy()
    hybrid_all_years = mapping[mapping["source_membership"].eq("iTE|TG")].copy()

    source_evidence = pair_evidence(source_exclusive)
    target_evidence = pair_evidence(target_exclusive)
    hybrid_evidence = pair_evidence(hybrid)
    source_evidence_all_years = pair_evidence(source_all_years)
    target_evidence_all_years = pair_evidence(target_all_years)
    hybrid_evidence_all_years = pair_evidence(hybrid_all_years)
    domain_counts = (
        papers[papers["year"] <= cutoff]
        .groupby("source_membership")["paper_id"]
        .nunique()
        .rename("papers")
        .reset_index()
        .sort_values("source_membership")
    )
    domain_counts["complete_through"] = cutoff
    domain_counts.to_csv(out / "paper_domain_counts.csv", index=False)

    scenarios = {
        "exclusive_iTE_to_exclusive_TG": (
            source_evidence,
            target_evidence,
        ),
        "exclusive_iTE_to_TG_plus_hybrid_sensitivity": (
            source_evidence,
            pd.concat([target_evidence, hybrid_evidence], ignore_index=True),
        ),
        "legacy_dual_assignment_replication": (
            pd.concat([source_evidence, hybrid_evidence], ignore_index=True),
            pd.concat([target_evidence, hybrid_evidence], ignore_index=True),
        ),
    }

    all_curves = []
    all_summaries = []
    all_fixed = []
    primary_events: dict[int, pd.DataFrame] = {}
    for scenario, (scenario_source, scenario_target) in scenarios.items():
        curves, summaries, fixed, event_tables = survival_outputs(
            scenario_source,
            scenario_target,
            vocab,
            cutoff,
            scenario,
        )
        all_curves.append(curves)
        all_summaries.append(summaries)
        all_fixed.append(fixed)
        if scenario == "exclusive_iTE_to_exclusive_TG":
            primary_events = event_tables

    curves = pd.concat(all_curves, ignore_index=True)
    sensitivity = pd.concat(all_summaries, ignore_index=True)
    fixed = pd.concat(all_fixed, ignore_index=True)
    curves.to_csv(out / "kaplan_meier_cooccurrence.csv", index=False)
    sensitivity.to_csv(out / "domain_sensitivity_summary.csv", index=False)
    fixed.to_csv(out / "fixed_five_year_summary.csv", index=False)
    for threshold, events in primary_events.items():
        events.to_csv(
            out / f"strict_pair_events_support_{threshold}.csv", index=False
        )
    type_rates = five_year_type_rates(
        primary_events[support_threshold],
        cutoff,
        "exclusive_iTE_to_exclusive_TG",
    )
    type_rates.to_csv(out / "five_year_rates_by_type.csv", index=False)
    competing_curve, competing_summary, competing_pairs = competing_risk_outputs(
        source_evidence,
        target_evidence,
        hybrid_evidence,
        vocab,
        cutoff,
    )
    competing_curve.to_csv(
        out / "competing_risk_cumulative_incidence.csv", index=False
    )
    competing_summary.to_csv(
        out / "competing_risk_summary.csv", index=False
    )
    for threshold, pairs in competing_pairs.items():
        pairs.to_csv(
            out / f"competing_risk_pair_outcomes_support_{threshold}.csv",
            index=False,
        )
    concentration = target_paper_concentration(
        primary_events[support_threshold], papers
    )
    concentration.to_csv(
        out / "target_first_evidence_paper_concentration.csv", index=False
    )
    verification = relation_verification_queue(
        primary_events[support_threshold],
        source_evidence,
        papers,
    )
    verification.to_csv(
        out / "direct_relation_verification_queue.csv", index=False
    )

    risk_frames = []
    metric_rows = []
    first_cutoff = max(
        int(source_evidence_all_years["year"].min()),
        int(target_evidence_all_years["year"].min()),
    )
    for risk_cutoff in range(first_cutoff, cutoff + 1):
        source_until_cutoff = source_evidence_all_years[
            source_evidence_all_years["year"] <= risk_cutoff
        ]
        target_until_next = target_evidence_all_years[
            target_evidence_all_years["year"] <= risk_cutoff + 1
        ]
        target_mapping_until_next = target_all_years[
            target_all_years["year"] <= risk_cutoff + 1
        ]
        risk = annual_relation_risk_set(
            source_until_cutoff,
            target_until_next,
            target_mapping_until_next,
            vocab,
            risk_cutoff,
            support_threshold,
        )
        if risk.empty:
            continue
        risk["observation_status"] = (
            "partial_interim"
            if risk_cutoff + 1 > cutoff
            else (
                "complete_holdout"
                if risk_cutoff + 1 == cutoff
                else "complete_historical"
            )
        )
        risk_frames.append(risk)
        metric_rows.append(
            ranking_metrics(risk, str(risk["observation_status"].iloc[0]))
        )

    annual_risk = pd.concat(risk_frames, ignore_index=True)
    ranking = pd.DataFrame(metric_rows)
    annual_risk.to_csv(out / "annual_relation_risk_sets.csv", index=False)
    ranking.to_csv(out / "walk_forward_ranking_metrics.csv", index=False)

    complete_holdout = annual_risk[
        annual_risk["observation_status"].eq("complete_holdout")
    ].copy()
    bootstrap = bootstrap_metrics(complete_holdout)
    bootstrap.to_csv(out / "complete_holdout_bootstrap.csv", index=False)

    prospective = annual_risk[
        annual_risk["cutoff_year"].eq(cutoff)
    ].copy()
    prospective = add_candidate_evidence(
        prospective, source_evidence_all_years[
            source_evidence_all_years["year"] <= cutoff
        ]
    )
    prospective["partial_next_year_observed_exclusive_TG_cooccurrence"] = (
        prospective["next_year_target_cooccurrence"].astype(int)
    )
    prospective["output_role"] = "manual_literature_audit_queue"
    prospective["probability_claim_allowed"] = False
    prospective["relation_claim_allowed_without_full_text_review"] = False
    prospective["partial_next_year_status"] = np.where(
        prospective[
            "partial_next_year_observed_exclusive_TG_cooccurrence"
        ].eq(1),
        "observed_in_exclusive_TG_during_partial_next_year",
        "not_yet_observed_or_not_yet_indexed",
    )
    prospective["next_year_target_cooccurrence"] = pd.NA
    prospective.to_csv(
        out / f"prospective_candidate_audit_queue_after_{cutoff}.csv",
        index=False,
    )

    all_target_evidence = pd.concat(
        [target_evidence_all_years, hybrid_evidence_all_years],
        ignore_index=True,
    )
    legacy_audit = legacy_overlap_audit(all_target_evidence, papers, out)
    legacy_audit.to_csv(
        out / "legacy_overlap_contamination_audit.csv", index=False
    )

    holdout_metrics = ranking[
        ranking["observation_status"].eq("complete_holdout")
    ]
    gate_reasons = []
    if holdout_metrics.empty:
        gate_reasons.append("No complete-year holdout was available.")
    else:
        holdout = holdout_metrics.iloc[0]
        if int(holdout["positives"]) < 10:
            gate_reasons.append(
                "The complete holdout has fewer than 10 positive events, so "
                "performance estimates are too unstable for deployment."
            )
        if pd.isna(holdout["roc_auc"]) or holdout["roc_auc"] < 0.65:
            gate_reasons.append(
                "The complete-holdout AUC does not reach the pre-specified "
                "exploratory threshold of 0.65."
            )
        if (
            pd.isna(holdout["ap_lift_over_prevalence"])
            or holdout["ap_lift_over_prevalence"] < 1.5
        ):
            gate_reasons.append(
                "Average precision is less than 1.5× the holdout prevalence."
            )
    if not gate_reasons:
        gate_reasons.append(
            "Numeric gate passed, but full-text relation verification and an "
            "expanded independent target corpus are still required."
        )

    summary = {
        "generated_on": date.today().isoformat(),
        "complete_through": cutoff,
        "source_support_papers": support_threshold,
        "primary_source_domain": "source_membership == 'iTE'",
        "primary_target_domain": "source_membership == 'TG'",
        "hybrid_handling": "excluded_from_primary; sensitivity_only",
        "edge_interpretation": "paper-level concept co-occurrence, not causal relation",
        "ontology_status": (
            "pre-existing full-corpus curation; blinded expert re-curation "
            "required before formal inference"
        ),
        "article_type_status": (
            "manual review required; no reliable structured review flag"
        ),
        "uncertainty_status": (
            "diagnostic intervals only; shared-paper/shared-node dependence "
            "not fully modeled"
        ),
        "formal_prediction_validated": False,
        "deployment_gate_reasons": gate_reasons,
        "prospective_audit_candidates": len(prospective),
    }
    (out / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    input_paths = [
        FLOW / "pure_mechanism_vocabulary.csv",
        DATA / "final_paper_concept_map.csv",
        DATA / "final_paper_index.csv",
    ]
    manifest = {
        "script_version": SCRIPT_VERSION,
        "script_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "script_sha256": sha256(Path(__file__).resolve()),
        "generated_on": date.today().isoformat(),
        "parameters": {
            "complete_through": cutoff,
            "source_support_papers": support_threshold,
            "random_state": RANDOM_STATE,
        },
        "paper_domain_counts": dict(
            zip(domain_counts["source_membership"], domain_counts["papers"])
        ),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "inputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in input_paths
        ],
    }
    (out / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    write_readme(
        out,
        cutoff,
        support_threshold,
        legacy_audit,
        ranking,
        gate_reasons,
    )

    print("Strict mechanism diffusion analysis complete")
    print(f"Output: {out}")
    print("\nPrimary fixed five-year summary")
    print(
        fixed[
            fixed["scenario"].eq("exclusive_iTE_to_exclusive_TG")
        ].to_string(index=False)
    )
    print("\nComplete/interim ranking checks")
    print(ranking.tail(3).to_string(index=False))
    print("\nFormal prediction validated: NO")
    for reason in gate_reasons:
        print(f"- {reason}")


if __name__ == "__main__":
    main()
