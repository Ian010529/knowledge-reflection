#!/usr/bin/env python3
"""Run typed evidence-graph analyses for the iTE -> TG workflow.

This script deliberately treats the knowledge graph as an evidence-navigation
structure.  It does not turn curated hypothesis edges into positive labels and
does not report a success probability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import textwrap
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "ite_tg_complementarity"
DEFAULT_OUTPUT = DEFAULT_INPUT / "graph_analysis"
LAYOUT_SEED = 42

EXPECTED_EDGE_SCHEMA = {
    "reports": ("paper", "iTE_insight"),
    "expresses_lever": ("iTE_insight", "iTE_transferable_lever"),
    "supports_hypothesis": ("iTE_insight", "translation_program"),
    "adapted_into": ("iTE_transferable_lever", "translation_program"),
    "targets": ("translation_program", "TG_recipient_system"),
    "exemplifies": ("paper", "TG_recipient_system"),
}

EDGE_LAYER = {
    "reports": "source_verified",
    "exemplifies": "source_verified",
    "expresses_lever": "taxonomy_assignment",
    "supports_hypothesis": "curated_hypothesis",
    "adapted_into": "curated_hypothesis",
    "targets": "curated_hypothesis",
    "direct_TG_precedent_for": "prior_art_relation",
    "related_TG_precedent_for": "prior_art_relation",
    "source_coupled_precedent_for": "prior_art_relation",
}

TIER_WEIGHT = {
    "A_direct_evidence_ready": 1.00,
    "B_direct_needs_evidence_repair": 0.75,
    "C_adjacent_enabling_evidence": 0.55,
    "P_coupled_precedent": 0.45,
}
SUPPORT_WEIGHT = {
    "claim_direct_support": 1.00,
    "role_sentence_support": 0.65,
}

STATUS_COLOR = {
    "new_cross_mechanism_hypothesis": "#8E63B6",
    "mechanism_extension_white_space": "#2F7F78",
    "direct_TG_precedent_upgrade_candidate": "#C57A2A",
    "known_TG_precedent_positive_control": "#6F7782",
}
BATCH_COLOR = {"B1": "#3976A8", "B2": "#34876A", "B3": "#B87333"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze the current claim-level iTE -> TG evidence graph."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def require_columns(frame: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def split_codes(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return sorted({item.strip() for item in text.split(";") if item.strip()})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_edge_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha1(payload).hexdigest()[:12]}"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Arial Unicode MS",
                "PingFang SC",
                "Hiragino Sans GB",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 9,
        }
    )


def load_inputs(input_dir: Path) -> dict[str, pd.DataFrame]:
    paths = {
        "nodes": "knowledge_graph_nodes.csv",
        "edges": "knowledge_graph_edges.csv",
        "programs": "ite_tg_complementarity_programs.csv",
        "evidence": "ite_tg_candidate_evidence.csv",
        "inventory": "ite_claim_inventory_with_levers.csv",
        "actions": "ite_tg_next_action_queue.csv",
        "priors": "tg_prior_art_by_program.csv",
        "review": "ite_tg_edge_review_queue.csv",
    }
    frames: dict[str, pd.DataFrame] = {}
    for key, filename in paths.items():
        path = input_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        frames[key] = pd.read_csv(path)

    require_columns(
        frames["nodes"],
        ["node_id", "node_type", "label", "evidence_status"],
        "knowledge_graph_nodes.csv",
    )
    require_columns(
        frames["edges"],
        [
            "edge_id",
            "source_node",
            "edge_type",
            "target_node",
            "evidence_ref",
            "verified",
        ],
        "knowledge_graph_edges.csv",
    )
    require_columns(
        frames["evidence"],
        [
            "program_id",
            "source_insight_id",
            "source_paper_id",
            "source_evidence_tier",
            "rule_match_support_class",
            "scope_caveat",
            "evidence_edge_status",
            "rule_match_verified",
        ],
        "ite_tg_candidate_evidence.csv",
    )
    return frames


def repair_baseline_metadata(
    nodes: pd.DataFrame, programs: pd.DataFrame
) -> tuple[pd.DataFrame, int]:
    """Backfill baseline-paper metadata for older graph exports.

    The current generator includes these fields, but keeping this repair makes
    the adapter safe for a previous export and makes the temporal audit explicit.
    """
    nodes = nodes.copy()
    if "year" not in nodes:
        nodes["year"] = np.nan
    if "doi" not in nodes:
        nodes["doi"] = ""
    repaired = 0
    for row in programs.itertuples(index=False):
        node_id = f"paper:{row.TG_baseline_paper_id}"
        mask = nodes["node_id"].eq(node_id)
        if not mask.any():
            continue
        missing_year = nodes.loc[mask, "year"].isna()
        missing_doi = nodes.loc[mask, "doi"].fillna("").eq("")
        if missing_year.any() and pd.notna(row.TG_baseline_year):
            nodes.loc[mask & nodes["year"].isna(), "year"] = row.TG_baseline_year
            repaired += 1
        if missing_doi.any() and clean_text(row.TG_baseline_doi):
            nodes.loc[mask & nodes["doi"].fillna("").eq(""), "doi"] = row.TG_baseline_doi
    return nodes, repaired


def make_base_graph(nodes: pd.DataFrame, edges: pd.DataFrame) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for row in nodes.to_dict("records"):
        node_id = row.pop("node_id")
        graph.add_node(node_id, **{k: graphml_scalar(v) for k, v in row.items()})
    for row in edges.to_dict("records"):
        edge_id = row.pop("edge_id")
        source = row.pop("source_node")
        target = row.pop("target_node")
        attrs = {k: graphml_scalar(v) for k, v in row.items()}
        attrs["edge_layer"] = EDGE_LAYER.get(attrs.get("edge_type", ""), "unknown")
        attrs["experimental_validation_status"] = (
            "not_applicable_source_fact"
            if attrs.get("edge_type") in {"reports", "exemplifies"}
            else "pending_or_not_applicable"
        )
        graph.add_edge(source, target, key=edge_id, edge_id=edge_id, **attrs)
    return graph


def graphml_scalar(value: Any) -> str | int | float | bool:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value)
    return str(value)


def graph_audit(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    evidence: pd.DataFrame,
    review: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, tuple[int, int]]]:
    node_ids = set(nodes["node_id"])
    node_type = nodes.set_index("node_id")["node_type"].to_dict()
    endpoint_errors: list[dict[str, str]] = []
    schema_errors: list[dict[str, str]] = []
    typed_edges: set[tuple[str, str, str]] = set()
    duplicate_typed_edges = 0
    for row in edges.itertuples(index=False):
        if row.source_node not in node_ids or row.target_node not in node_ids:
            endpoint_errors.append(
                {
                    "edge_id": row.edge_id,
                    "source_node": row.source_node,
                    "target_node": row.target_node,
                }
            )
            continue
        typed_key = (row.source_node, row.edge_type, row.target_node)
        duplicate_typed_edges += int(typed_key in typed_edges)
        typed_edges.add(typed_key)
        expected = EXPECTED_EDGE_SCHEMA.get(row.edge_type)
        actual = (node_type[row.source_node], node_type[row.target_node])
        if expected is None or actual != expected:
            schema_errors.append(
                {
                    "edge_id": row.edge_id,
                    "edge_type": row.edge_type,
                    "actual": f"{actual[0]}->{actual[1]}",
                    "expected": "unknown" if expected is None else f"{expected[0]}->{expected[1]}",
                }
            )

    simple = nx.DiGraph()
    simple.add_nodes_from(node_ids)
    simple.add_edges_from(
        edges[["source_node", "target_node"]].itertuples(index=False, name=None)
    )
    components = sorted(
        nx.weakly_connected_components(simple), key=lambda part: (-len(part), min(part))
    )
    component_lookup: dict[str, tuple[int, int]] = {}
    for index, component in enumerate(components, start=1):
        for node_id in component:
            component_lookup[node_id] = (index, len(component))

    support_pairs = set(
        edges.loc[
            edges["edge_type"].eq("supports_hypothesis"),
            ["source_node", "target_node"],
        ].itertuples(index=False, name=None)
    )
    evidence_pairs = {
        (f"insight:{row.source_insight_id}", f"program:{row.program_id}")
        for row in evidence.itertuples(index=False)
    }
    review_pairs = {
        (f"insight:{row.source_insight_id}", row.program_rule_code)
        for row in review.itertuples(index=False)
    }
    primary_review_overlap = 0
    if review_pairs:
        program_code_by_id = {}
        for row in evidence[["program_id", "program_rule_code"]].drop_duplicates().itertuples(index=False):
            program_code_by_id[f"program:{row.program_id}"] = row.program_rule_code
        primary_review_overlap = sum(
            (source, program_code_by_id.get(target, "")) in review_pairs
            for source, target in support_pairs
        )

    edge_type_counts = {
        edge_type: {
            "total": int(len(group)),
            "verified_true": int(group["verified"].map(bool_value).sum()),
            "verified_false": int((~group["verified"].map(bool_value)).sum()),
            "semantic_layer": EDGE_LAYER.get(edge_type, "unknown"),
        }
        for edge_type, group in edges.groupby("edge_type", sort=True)
    }
    paper_nodes = nodes[nodes["node_type"].eq("paper")]
    audit = {
        "node_count": int(len(nodes)),
        "edge_count": int(len(edges)),
        "node_type_counts": {
            str(key): int(value)
            for key, value in nodes["node_type"].value_counts().sort_index().items()
        },
        "edge_type_counts": edge_type_counts,
        "duplicate_node_ids": int(nodes["node_id"].duplicated().sum()),
        "duplicate_edge_ids": int(edges["edge_id"].duplicated().sum()),
        "duplicate_typed_edges": int(duplicate_typed_edges),
        "missing_endpoint_count": int(len(endpoint_errors)),
        "endpoint_errors": endpoint_errors[:20],
        "typed_schema_error_count": int(len(schema_errors)),
        "typed_schema_errors": schema_errors[:20],
        "self_loop_count": int(nx.number_of_selfloops(simple)),
        "is_directed_acyclic_graph": bool(nx.is_directed_acyclic_graph(simple)),
        "weak_component_count": int(len(components)),
        "largest_weak_component_size": int(len(components[0]) if components else 0),
        "isolate_count": int(nx.number_of_isolates(simple)),
        "paper_nodes_missing_year": int(paper_nodes["year"].isna().sum()),
        "supports_hypothesis_pair_count": int(len(support_pairs)),
        "accepted_evidence_pair_count": int(len(evidence_pairs)),
        "supports_exactly_match_accepted_evidence": support_pairs == evidence_pairs,
        "review_queue_edge_count": int(len(review)),
        "review_queue_overlap_with_primary_graph": int(primary_review_overlap),
        "interpretation_guardrails": [
            "verified=False is not a negative label.",
            "supports_hypothesis edges are curated candidates, not experimental positives.",
            "missing edges are unreviewed or uncovered, not experimental negatives.",
            "centrality and component size describe this curation schema, not scientific efficacy.",
        ],
    }
    return audit, component_lookup


def typed_node_metrics(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    component_lookup: dict[str, tuple[int, int]],
) -> pd.DataFrame:
    incoming: dict[str, Counter[str]] = defaultdict(Counter)
    outgoing: dict[str, Counter[str]] = defaultdict(Counter)
    verified_in: Counter[str] = Counter()
    verified_out: Counter[str] = Counter()
    for row in edges.itertuples(index=False):
        outgoing[row.source_node][row.edge_type] += 1
        incoming[row.target_node][row.edge_type] += 1
        if bool_value(row.verified):
            verified_out[row.source_node] += 1
            verified_in[row.target_node] += 1

    edge_types = sorted(edges["edge_type"].unique())
    rows: list[dict[str, Any]] = []
    for node in nodes.itertuples(index=False):
        component_id, component_size = component_lookup[node.node_id]
        row: dict[str, Any] = {
            "node_id": node.node_id,
            "node_type": node.node_type,
            "label": node.label,
            "evidence_status": node.evidence_status,
            "component_id": component_id,
            "component_size": component_size,
            "in_degree": int(sum(incoming[node.node_id].values())),
            "out_degree": int(sum(outgoing[node.node_id].values())),
            "verified_in_degree": int(verified_in[node.node_id]),
            "verified_out_degree": int(verified_out[node.node_id]),
        }
        for edge_type in edge_types:
            row[f"in__{edge_type}"] = int(incoming[node.node_id][edge_type])
            row[f"out__{edge_type}"] = int(outgoing[node.node_id][edge_type])
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["node_type", "node_id"])


def evidence_weight(row: Any) -> float:
    tier = TIER_WEIGHT.get(clean_text(row.source_evidence_tier), 0.35)
    support = SUPPORT_WEIGHT.get(clean_text(row.rule_match_support_class), 0.50)
    caveat_factor = 0.60 if clean_text(row.scope_caveat) else 1.00
    return float(tier * support * caveat_factor)


def concentration_hhi(values: pd.Series) -> float:
    counts = values.value_counts()
    if counts.empty:
        return float("nan")
    shares = counts / counts.sum()
    return float(np.square(shares).sum())


def make_action_graph(programs: pd.DataFrame, include_controls: bool = True) -> nx.Graph:
    selected = programs.copy() if include_controls else programs[~programs["positive_control"].map(bool_value)].copy()
    graph = nx.Graph()
    for row in selected.itertuples(index=False):
        program_node = f"program:{row.program_id}"
        lever_node = f"lever:{row.source_lever_code}"
        target_node = f"tg_system:{row.target_redox_family}"
        graph.add_node(program_node, node_type="translation_program")
        graph.add_node(lever_node, node_type="iTE_transferable_lever")
        graph.add_node(target_node, node_type="TG_recipient_system")
        graph.add_edge(lever_node, program_node, relation="adapted_into")
        graph.add_edge(program_node, target_node, relation="targets")
    return graph


def program_support_table(
    programs: pd.DataFrame,
    evidence: pd.DataFrame,
    actions: pd.DataFrame,
) -> pd.DataFrame:
    evidence = evidence.copy()
    evidence["evidence_path_weight"] = [
        evidence_weight(row) for row in evidence.itertuples(index=False)
    ]
    action_cols = [
        "program_id",
        "batch_id",
        "batch_order",
        "batch_name_cn",
        "cost_level_cn",
        "entry_stage",
    ]
    action_lookup = actions[action_cols].drop_duplicates("program_id").set_index("program_id")
    all_action_graph = make_action_graph(programs, include_controls=True)
    action_components = sorted(
        nx.connected_components(all_action_graph), key=lambda part: (-len(part), min(part))
    )
    action_component_lookup: dict[str, tuple[int, int]] = {}
    for index, component in enumerate(action_components, start=1):
        program_count = sum(node.startswith("program:") for node in component)
        for node in component:
            action_component_lookup[node] = (index, program_count)

    rows: list[dict[str, Any]] = []
    for program in programs.itertuples(index=False):
        subset = evidence[evidence["program_id"].eq(program.program_id)].copy()
        direct = subset["rule_match_support_class"].eq("claim_direct_support")
        caveat = subset["scope_caveat"].fillna("").ne("")
        program_node = f"program:{program.program_id}"
        component_id, component_program_count = action_component_lookup[program_node]
        lever_peers = programs[
            programs["source_lever_code"].eq(program.source_lever_code)
            & programs["program_id"].ne(program.program_id)
        ]["program_id"].nunique()
        target_peers = programs[
            programs["target_redox_family"].eq(program.target_redox_family)
            & programs["program_id"].ne(program.program_id)
        ]["program_id"].nunique()
        structural_peers = set(
            programs.loc[
                programs["source_lever_code"].eq(program.source_lever_code)
                | programs["target_redox_family"].eq(program.target_redox_family),
                "program_id",
            ]
        ) - {program.program_id}
        source_years = pd.to_numeric(subset["source_year"], errors="coerce").dropna()
        action = (
            action_lookup.loc[program.program_id].to_dict()
            if program.program_id in action_lookup.index
            else {
                "batch_id": "CONTROL",
                "batch_order": np.nan,
                "batch_name_cn": "正对照",
                "cost_level_cn": "",
                "entry_stage": "positive_control",
            }
        )
        paper_hhi = concentration_hhi(subset["source_paper_id"])
        rows.append(
            {
                "program_id": program.program_id,
                "program_rule_code": program.program_rule_code,
                "program_title_cn": program.program_title_cn,
                "candidate_status": program.candidate_status,
                "positive_control": bool_value(program.positive_control),
                "batch_id": action["batch_id"],
                "batch_order": action["batch_order"],
                "batch_name_cn": action["batch_name_cn"],
                "cost_level_cn": action["cost_level_cn"],
                "entry_stage": action["entry_stage"],
                "source_lever_code": program.source_lever_code,
                "source_lever_cn": program.source_lever_cn,
                "target_redox_family": program.target_redox_family,
                "target_redox_system_cn": program.target_redox_system_cn,
                "independent_source_paper_count": int(subset["source_paper_id"].nunique()),
                "independent_source_claim_count": int(subset["source_insight_id"].nunique()),
                "evidence_path_count": int(len(subset)),
                "claim_direct_count": int(direct.sum()),
                "role_sentence_count": int((~direct).sum()),
                "claim_direct_fraction": round(float(direct.mean()) if len(subset) else 0.0, 4),
                "scope_caveat_count": int(caveat.sum()),
                "scope_caveat_fraction": round(float(caveat.mean()) if len(subset) else 0.0, 4),
                "A_direct_ready_count": int(subset["source_evidence_tier"].eq("A_direct_evidence_ready").sum()),
                "B_needs_repair_count": int(subset["source_evidence_tier"].eq("B_direct_needs_evidence_repair").sum()),
                "C_adjacent_count": int(subset["source_evidence_tier"].eq("C_adjacent_enabling_evidence").sum()),
                "P_coupled_benchmark_count": int(subset["source_evidence_tier"].eq("P_coupled_precedent").sum()),
                "weighted_evidence_mass": round(float(subset["evidence_path_weight"].sum()), 4),
                "mean_evidence_path_weight": round(float(subset["evidence_path_weight"].mean()) if len(subset) else 0.0, 4),
                "paper_concentration_hhi": round(paper_hhi, 4) if not math.isnan(paper_hhi) else np.nan,
                "source_year_min": int(source_years.min()) if len(source_years) else np.nan,
                "source_year_max": int(source_years.max()) if len(source_years) else np.nan,
                "direct_TG_prior_art_count": int(program.direct_TG_prior_art_count),
                "related_TG_prior_art_count": int(program.related_TG_prior_art_count),
                "source_coupled_precedent_count": int(program.source_coupled_precedent_count),
                "same_lever_other_program_count": int(lever_peers),
                "same_target_other_program_count": int(target_peers),
                "explicit_structural_peer_count": int(len(structural_peers)),
                "action_component_id": int(component_id),
                "action_component_program_count": int(component_program_count),
                "score_interpretation": "evidence coverage only; not experimental success probability",
            }
        )
    result = pd.DataFrame(rows)
    result["evidence_reading_order"] = (
        result.sort_values(
            [
                "positive_control",
                "weighted_evidence_mass",
                "independent_source_paper_count",
                "claim_direct_fraction",
                "program_id",
            ],
            ascending=[True, False, False, False, True],
        )
        .groupby("positive_control")
        .cumcount()
        .add(1)
        .sort_index()
        .astype(int)
    )
    return result.sort_values(["positive_control", "evidence_reading_order"])


def evidence_paths(
    evidence: pd.DataFrame, programs: pd.DataFrame
) -> pd.DataFrame:
    program_cols = [
        "program_id",
        "program_rule_code",
        "program_title_cn",
        "source_lever_code",
        "source_lever_cn",
        "target_redox_family",
        "target_redox_system_cn",
        "candidate_status",
        "positive_control",
    ]
    merged = evidence.merge(
        programs[program_cols], on=["program_id", "program_rule_code", "program_title_cn"], how="left"
    )
    merged["evidence_path_weight"] = [
        evidence_weight(row) for row in merged.itertuples(index=False)
    ]
    merged["source_paper_node"] = "paper:" + merged["source_paper_id"].astype(str)
    merged["source_insight_node"] = "insight:" + merged["source_insight_id"].astype(str)
    merged["source_lever_node"] = "lever:" + merged["source_lever_code"].astype(str)
    merged["program_node"] = "program:" + merged["program_id"].astype(str)
    merged["target_system_node"] = "tg_system:" + merged["target_redox_family"].astype(str)
    merged["graph_path"] = (
        merged["source_paper_node"]
        + " --reports--> "
        + merged["source_insight_node"]
        + " --supports_hypothesis--> "
        + merged["program_node"]
        + " --targets--> "
        + merged["target_system_node"]
    )
    merged["path_semantics"] = (
        "source report verified; rule match verified; transfer hypothesis experimentally pending"
    )
    keep = [
        "program_id",
        "program_rule_code",
        "program_title_cn",
        "candidate_status",
        "positive_control",
        "source_paper_id",
        "source_year",
        "source_title",
        "source_doi",
        "source_insight_id",
        "source_claim",
        "source_evidence_tier",
        "source_evidence_level",
        "source_hypothesis_lane",
        "source_scope_route",
        "rule_match_support_class",
        "scope_caveat",
        "evidence_edge_status",
        "rule_match_verified",
        "evidence_path_weight",
        "source_lever_code",
        "source_lever_cn",
        "target_redox_family",
        "target_redox_system_cn",
        "source_paper_node",
        "source_insight_node",
        "source_lever_node",
        "program_node",
        "target_system_node",
        "graph_path",
        "path_semantics",
    ]
    return merged[keep].sort_values(["program_id", "source_paper_id", "source_insight_id"])


def add_prior_art_layer(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    priors: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    relation_edge_type = {
        "direct": "direct_TG_precedent_for",
        "related": "related_TG_precedent_for",
        "source_coupled_benchmark": "source_coupled_precedent_for",
    }
    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    relation_rows: list[dict[str, Any]] = []
    existing_nodes = set(nodes["node_id"])
    for row in priors.itertuples(index=False):
        relation = clean_text(row.prior_art_relation)
        edge_type = relation_edge_type.get(relation, f"{relation}_TG_precedent_for")
        paper_node = f"paper:{row.TG_paper_id}"
        program_node = f"program:{row.program_id}"
        if paper_node not in existing_nodes:
            node_rows.append(
                {
                    "node_id": paper_node,
                    "node_type": "paper",
                    "label": row.TG_title,
                    "evidence_status": f"TG_prior_art_{relation}",
                    "year": row.TG_year,
                    "doi": row.TG_doi,
                    "discovery_status": "TG_prior_art",
                }
            )
            existing_nodes.add(paper_node)
        edge_id = stable_edge_id("PA", paper_node, edge_type, program_node)
        edge_rows.append(
            {
                "edge_id": edge_id,
                "source_node": paper_node,
                "edge_type": edge_type,
                "target_node": program_node,
                "evidence_ref": row.TG_paper_id,
                "verified": True,
            }
        )
        relation_rows.append(
            {
                "edge_id": edge_id,
                "prior_art_relation": relation,
                "edge_type": edge_type,
                "TG_paper_id": row.TG_paper_id,
                "TG_year": row.TG_year,
                "TG_title": row.TG_title,
                "TG_doi": row.TG_doi,
                "program_id": row.program_id,
                "program_title_cn": row.program_title_cn,
                "target_redox_family": row.target_redox_family,
                "relation_interpretation": "corpus prior-art relation; not a success label",
            }
        )
    augmented_nodes = pd.concat([nodes, pd.DataFrame(node_rows)], ignore_index=True).drop_duplicates("node_id")
    augmented_edges = pd.concat([edges, pd.DataFrame(edge_rows)], ignore_index=True).drop_duplicates("edge_id")
    relation_frame = pd.DataFrame(relation_rows).sort_values(
        ["program_id", "prior_art_relation", "TG_year", "TG_paper_id"]
    )
    return augmented_nodes, augmented_edges, relation_frame


def program_relations(programs: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    program_rows = {row.program_id: row for row in programs.itertuples(index=False)}
    sources = {
        program_id: set(group["source_paper_id"].astype(str))
        for program_id, group in evidence.groupby("program_id")
    }
    rows: list[dict[str, Any]] = []
    for left_id, right_id in combinations(sorted(program_rows), 2):
        left = program_rows[left_id]
        right = program_rows[right_id]
        relations: list[tuple[str, str]] = []
        if left.source_lever_code == right.source_lever_code:
            relations.append(("shared_transfer_lever", left.source_lever_code))
        if left.target_redox_family == right.target_redox_family:
            relations.append(("shared_TG_recipient_system", left.target_redox_family))
        shared_papers = sorted(sources.get(left_id, set()) & sources.get(right_id, set()))
        if shared_papers:
            relations.append(("shared_source_paper", "; ".join(shared_papers)))
        for relation_type, evidence_ref in relations:
            rows.append(
                {
                    "program_left": left_id,
                    "program_left_title_cn": left.program_title_cn,
                    "program_right": right_id,
                    "program_right_title_cn": right.program_title_cn,
                    "relation_type": relation_type,
                    "relation_evidence": evidence_ref,
                    "interpretation": "explicit shared node; no composite similarity score",
                }
            )
    return pd.DataFrame(rows).sort_values(["relation_type", "program_left", "program_right"])


def lever_target_tables(
    nodes: pd.DataFrame, programs: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    levers = nodes[nodes["node_type"].eq("iTE_transferable_lever")][
        ["node_id", "label"]
    ].drop_duplicates()
    targets = nodes[nodes["node_type"].eq("TG_recipient_system")][
        ["node_id", "label"]
    ].drop_duplicates()
    lever_codes = sorted(node.replace("lever:", "", 1) for node in levers["node_id"])
    target_codes = sorted(node.replace("tg_system:", "", 1) for node in targets["node_id"])
    lever_label = {row.node_id.replace("lever:", "", 1): row.label for row in levers.itertuples(index=False)}
    target_label = {row.node_id.replace("tg_system:", "", 1): row.label for row in targets.itertuples(index=False)}
    matrix_rows: list[dict[str, Any]] = []
    long_rows: list[dict[str, Any]] = []
    for lever in lever_codes:
        matrix_row: dict[str, Any] = {"lever_code": lever, "lever_label_cn": lever_label[lever]}
        for target in target_codes:
            subset = programs[
                programs["source_lever_code"].eq(lever)
                & programs["target_redox_family"].eq(target)
            ]
            matrix_row[target] = int(len(subset))
            long_rows.append(
                {
                    "lever_code": lever,
                    "lever_label_cn": lever_label[lever],
                    "target_redox_family": target,
                    "target_redox_system_cn": target_label[target],
                    "curated_program_count": int(len(subset)),
                    "program_ids": "; ".join(subset["program_id"].astype(str)),
                    "candidate_program_count": int((~subset["positive_control"].map(bool_value)).sum()) if len(subset) else 0,
                    "positive_control_count": int(subset["positive_control"].map(bool_value).sum()) if len(subset) else 0,
                    "cell_status": "curated_program_present" if len(subset) else "current_rules_uninstantiated",
                    "cell_interpretation": (
                        "curated mapping exists; experimental validation pending or benchmark only"
                        if len(subset)
                        else "not covered by current curated rules; not a literature white space"
                    ),
                }
            )
        matrix_rows.append(matrix_row)
    return pd.DataFrame(matrix_rows), pd.DataFrame(long_rows)


def lever_cooccurrence(
    inventory: pd.DataFrame,
    nodes: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], nx.Graph]:
    lever_nodes = nodes[nodes["node_type"].eq("iTE_transferable_lever")][
        ["node_id", "label"]
    ].drop_duplicates()
    lever_labels = {
        row.node_id.replace("lever:", "", 1): row.label
        for row in lever_nodes.itertuples(index=False)
    }
    claim_sets: dict[str, set[str]] = {lever: set() for lever in lever_labels}
    paper_sets: dict[str, set[str]] = {lever: set() for lever in lever_labels}
    pair_claims: Counter[tuple[str, str]] = Counter()
    pair_papers: dict[tuple[str, str], set[str]] = defaultdict(set)
    claims_with_any = 0
    claims_with_multiple = 0
    for row in inventory.itertuples(index=False):
        codes = [code for code in split_codes(row.transferable_lever_codes) if code in lever_labels]
        if not codes:
            continue
        claims_with_any += 1
        claims_with_multiple += int(len(codes) > 1)
        for code in codes:
            claim_sets[code].add(row.insight_id)
            paper_sets[code].add(row.paper_id)
        for left, right in combinations(codes, 2):
            key = tuple(sorted((left, right)))
            pair_claims[key] += 1
            pair_papers[key].add(row.paper_id)

    edge_rows: list[dict[str, Any]] = []
    for (left, right), count in sorted(pair_claims.items()):
        union_count = len(claim_sets[left] | claim_sets[right])
        edge_rows.append(
            {
                "lever_left": left,
                "lever_left_label_cn": lever_labels[left],
                "lever_right": right,
                "lever_right_label_cn": lever_labels[right],
                "cooccurring_claim_count": int(count),
                "cooccurring_paper_count": int(len(pair_papers[(left, right)])),
                "claim_jaccard": round(count / union_count, 6) if union_count else 0.0,
                "projection_interpretation": "same claim carries both taxonomy labels; not causal coupling",
            }
        )
    edge_frame = pd.DataFrame(edge_rows).sort_values(
        ["cooccurring_claim_count", "claim_jaccard", "lever_left", "lever_right"],
        ascending=[False, False, True, True],
    )

    def partition_for(threshold: int, seed: int) -> tuple[list[set[str]], float, nx.Graph]:
        graph = nx.Graph()
        for lever in lever_labels:
            graph.add_node(
                lever,
                label=lever_labels[lever],
                claim_count=len(claim_sets[lever]),
                paper_count=len(paper_sets[lever]),
            )
        selected = edge_frame[edge_frame["cooccurring_claim_count"].ge(threshold)]
        for row in selected.itertuples(index=False):
            graph.add_edge(
                row.lever_left,
                row.lever_right,
                weight=int(row.cooccurring_claim_count),
                claim_jaccard=float(row.claim_jaccard),
            )
        connected = graph.subgraph([node for node in graph if graph.degree(node) > 0]).copy()
        communities: list[set[str]] = []
        if connected.number_of_edges():
            communities.extend(
                nx.community.louvain_communities(connected, weight="weight", seed=seed)
            )
            modularity = nx.community.modularity(connected, communities, weight="weight")
        else:
            modularity = 0.0
        covered = set().union(*communities) if communities else set()
        communities.extend([{node} for node in sorted(set(graph) - covered)])
        communities = sorted(communities, key=lambda group: (-len(group), min(group)))
        return communities, float(modularity), graph

    def labels_from_partition(partition: list[set[str]], ordered_nodes: list[str]) -> list[int]:
        lookup = {node: index for index, group in enumerate(partition) for node in group}
        return [lookup[node] for node in ordered_nodes]

    ordered_nodes = sorted(lever_labels)
    sensitivity: dict[str, Any] = {
        "claim_count_with_at_least_one_lever": int(claims_with_any),
        "claim_count_with_multiple_levers": int(claims_with_multiple),
        "claim_count_with_single_lever": int(claims_with_any - claims_with_multiple),
        "thresholds": {},
        "cross_threshold_ARI": {},
        "interpretation": "communities are descriptive co-annotation groups and are threshold-sensitive",
    }
    best_by_threshold: dict[int, list[set[str]]] = {}
    for threshold in (1, 2, 3):
        runs: list[tuple[list[set[str]], float, nx.Graph]] = [
            partition_for(threshold, seed) for seed in range(100)
        ]
        reference_labels = labels_from_partition(runs[0][0], ordered_nodes)
        aris = [
            adjusted_rand_score(reference_labels, labels_from_partition(partition, ordered_nodes))
            for partition, _, _ in runs
        ]
        best = max(runs, key=lambda item: (item[1], tuple(sorted(map(sorted, item[0])))))
        best_by_threshold[threshold] = best[0]
        sensitivity["thresholds"][str(threshold)] = {
            "node_count": int(best[2].number_of_nodes()),
            "edge_count": int(best[2].number_of_edges()),
            "community_count_including_singletons": int(len(best[0])),
            "nontrivial_community_count": int(sum(len(group) > 1 for group in best[0])),
            "modularity_mean": round(float(np.mean([run[1] for run in runs])), 6),
            "modularity_sd": round(float(np.std([run[1] for run in runs])), 6),
            "ARI_vs_seed0_mean": round(float(np.mean(aris)), 6),
            "ARI_vs_seed0_min": round(float(np.min(aris)), 6),
        }
    for left, right in combinations((1, 2, 3), 2):
        score = adjusted_rand_score(
            labels_from_partition(best_by_threshold[left], ordered_nodes),
            labels_from_partition(best_by_threshold[right], ordered_nodes),
        )
        sensitivity["cross_threshold_ARI"][f"w>={left}_vs_w>={right}"] = round(float(score), 6)

    chosen_partition = best_by_threshold[2]
    community_lookup = {
        node: index for index, group in enumerate(chosen_partition, start=1) for node in group
    }
    node_rows = [
        {
            "lever_code": lever,
            "lever_label_cn": lever_labels[lever],
            "claim_count": int(len(claim_sets[lever])),
            "independent_paper_count": int(len(paper_sets[lever])),
            "community_w_ge_2": int(community_lookup[lever]),
            "community_size": int(len(chosen_partition[community_lookup[lever] - 1])),
            "community_interpretation": "co-annotation community, not a natural mechanism family",
        }
        for lever in ordered_nodes
    ]
    _, _, chosen_graph = partition_for(2, LAYOUT_SEED)
    nx.set_node_attributes(chosen_graph, community_lookup, "community_w_ge_2")
    return pd.DataFrame(node_rows), edge_frame, sensitivity, chosen_graph


def projection_graph(programs: pd.DataFrame, relations: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    for row in programs.itertuples(index=False):
        graph.add_node(
            row.program_id,
            label=row.program_title_cn,
            candidate_status=row.candidate_status,
            positive_control=bool_value(row.positive_control),
        )
    if relations.empty:
        return graph
    for (left, right), group in relations.groupby(["program_left", "program_right"]):
        graph.add_edge(
            left,
            right,
            relation_types="; ".join(sorted(group["relation_type"].unique())),
            relation_evidence=" | ".join(group["relation_evidence"].astype(str)),
            interpretation="explicit shared nodes; no composite similarity score",
        )
    return graph


def write_graphml(path: Path, graph: nx.Graph) -> None:
    clean = graph.__class__()
    for node, attrs in graph.nodes(data=True):
        clean.add_node(node, **{key: graphml_scalar(value) for key, value in attrs.items()})
    if graph.is_multigraph():
        for source, target, key, attrs in graph.edges(keys=True, data=True):
            clean.add_edge(
                source,
                target,
                key=key,
                **{name: graphml_scalar(value) for name, value in attrs.items()},
            )
    else:
        for source, target, attrs in graph.edges(data=True):
            clean.add_edge(
                source,
                target,
                **{name: graphml_scalar(value) for name, value in attrs.items()},
            )
    nx.write_graphml(clean, path)


def wrap_cjk(text: str, width: int) -> str:
    text = clean_text(text)
    return "\n".join(text[index : index + width] for index in range(0, len(text), width))


def plot_action_overview(program_support: pd.DataFrame, output_dir: Path) -> None:
    data = program_support[~program_support["positive_control"]].copy()
    data = data.sort_values(["batch_id", "batch_order"])
    count = len(data)
    y_values = np.linspace(0.93, 0.08, count)
    data["y_position"] = y_values
    lever_y = data.groupby(["source_lever_code", "source_lever_cn"])["y_position"].mean().to_dict()
    target_y = data.groupby(["target_redox_family", "target_redox_system_cn"])["y_position"].mean().to_dict()

    figure, axis = plt.subplots(figsize=(18, 14))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    figure.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.05)

    axis.text(0.03, 0.985, "iTE transferable lever", ha="left", va="top", fontsize=11, weight="bold", color="#25313C")
    axis.text(0.50, 0.985, "translation program（括号：独立论文数 / claim数）", ha="center", va="top", fontsize=11, weight="bold", color="#25313C")
    axis.text(0.97, 0.985, "TG recipient system", ha="right", va="top", fontsize=11, weight="bold", color="#25313C")

    for row in data.itertuples(index=False):
        color = BATCH_COLOR.get(row.batch_id, "#6F7782")
        ly = lever_y[(row.source_lever_code, row.source_lever_cn)]
        ty = target_y[(row.target_redox_family, row.target_redox_system_cn)]
        width = 0.7 + 2.2 * math.log1p(row.independent_source_paper_count) / math.log(12)
        axis.plot([0.22, 0.35], [ly, row.y_position], color=color, alpha=0.34, linewidth=width, solid_capstyle="round", zorder=1)
        axis.plot([0.65, 0.82], [row.y_position, ty], color=color, alpha=0.52, linewidth=width, solid_capstyle="round", zorder=1)
        title = wrap_cjk(row.program_title_cn, 17)
        label = f"{row.batch_id}-{int(row.batch_order)}  {title}\n({row.independent_source_paper_count}P / {row.independent_source_claim_count}C)"
        axis.text(
            0.50,
            row.y_position,
            label,
            ha="center",
            va="center",
            fontsize=8.1,
            color="#17212B",
            bbox={
                "boxstyle": "round,pad=0.46,rounding_size=0.12",
                "facecolor": "white",
                "edgecolor": color,
                "linewidth": 1.35,
            },
            zorder=3,
        )

    for (lever_code, lever_label), y in lever_y.items():
        axis.text(
            0.215,
            y,
            wrap_cjk(lever_label, 11),
            ha="right",
            va="center",
            fontsize=8.5,
            color="#26323D",
            bbox={"boxstyle": "round,pad=0.28", "facecolor": "#F2F5F7", "edgecolor": "#CBD3D9"},
            zorder=3,
        )
    for (target_code, target_label), y in target_y.items():
        axis.text(
            0.825,
            y,
            wrap_cjk(target_label, 13),
            ha="left",
            va="center",
            fontsize=8.5,
            color="#26323D",
            bbox={"boxstyle": "round,pad=0.30", "facecolor": "#F2F5F7", "edgecolor": "#CBD3D9"},
            zorder=3,
        )

    legend_y = 0.015
    for index, (batch, color) in enumerate(BATCH_COLOR.items()):
        axis.text(0.32 + index * 0.18, legend_y, f"● {batch}", color=color, ha="center", va="center", fontsize=9, weight="bold")
    figure.suptitle(
        "iTE → TG 分类型行动图（仅显示15个非正对照程序）",
        fontsize=16,
        weight="bold",
        color="#17212B",
        y=0.975,
    )
    axis.set_title(
        "边宽表示独立 source paper 数；连线表示策展映射，不表示实验已成功",
        fontsize=10,
        color="#5B6670",
        pad=16,
    )
    figure.savefig(output_dir / "ite_tg_action_graph.svg", bbox_inches="tight")
    figure.savefig(output_dir / "ite_tg_action_graph.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def plot_lever_graph(graph: nx.Graph, output_dir: Path) -> None:
    communities = nx.get_node_attributes(graph, "community_w_ge_2")
    palette = ["#3976A8", "#34876A", "#B87333", "#8E63B6", "#A35C5C", "#6B7A8F", "#6F7782"]
    ordered_nodes = sorted(
        graph.nodes,
        key=lambda node: (
            communities.get(node, 999),
            -graph.nodes[node].get("paper_count", 0),
            graph.nodes[node].get("label", node),
        ),
    )
    angles = np.linspace(math.pi / 2, math.pi / 2 - 2 * math.pi, len(ordered_nodes), endpoint=False)
    position = {
        node: np.array([math.cos(angle), math.sin(angle)])
        for node, angle in zip(ordered_nodes, angles)
    }
    label_position = {
        node: np.array([1.18 * math.cos(angle), 1.18 * math.sin(angle)])
        for node, angle in zip(ordered_nodes, angles)
    }
    node_colors = [palette[(communities.get(node, 1) - 1) % len(palette)] for node in ordered_nodes]
    node_sizes = [190 + 34 * math.sqrt(max(1, graph.nodes[node].get("paper_count", 1))) for node in ordered_nodes]
    widths = [0.6 + 1.8 * math.log1p(data.get("weight", 1)) for _, _, data in graph.edges(data=True)]

    figure, axis = plt.subplots(figsize=(14, 12))
    axis.axis("off")
    axis.set_xlim(-1.48, 1.48)
    axis.set_ylim(-1.42, 1.42)
    nx.draw_networkx_edges(graph, position, ax=axis, edge_color="#97A2AC", alpha=0.22, width=widths)
    nx.draw_networkx_nodes(
        graph,
        position,
        nodelist=ordered_nodes,
        ax=axis,
        node_color=node_colors,
        node_size=node_sizes,
        edgecolors="white",
        linewidths=1.2,
    )
    for node in ordered_nodes:
        x, y = label_position[node]
        axis.text(
            x,
            y,
            wrap_cjk(graph.nodes[node].get("label", node), 8),
            ha="left" if x >= 0 else "right",
            va="center",
            fontsize=7.7,
            color="#27323C",
        )
    figure.suptitle("iTE claim 的 lever 共现投影（w ≥ 2）", fontsize=16, weight="bold", y=0.98)
    axis.set_title("两 lever 在同一 claim 中共同出现；颜色是共标注社区，不是客观机制家族", fontsize=10, color="#5B6670")
    figure.savefig(output_dir / "lever_cooccurrence_graph.svg", bbox_inches="tight")
    figure.savefig(output_dir / "lever_cooccurrence_graph.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def plot_program_leverage(program_support: pd.DataFrame, output_dir: Path) -> None:
    data = program_support[~program_support["positive_control"]].copy()
    figure, axis = plt.subplots(figsize=(12.5, 8.5))
    for status, group in data.groupby("candidate_status"):
        axis.scatter(
            group["paper_concentration_hhi"],
            group["claim_direct_fraction"],
            s=90 + 35 * group["independent_source_paper_count"],
            color=STATUS_COLOR.get(status, "#6F7782"),
            alpha=0.82,
            edgecolor="white",
            linewidth=1.1,
            label=status,
        )
    coordinate_seen: Counter[tuple[float, float]] = Counter()
    offsets = [(6, 7), (6, -12), (-28, 7), (-28, -12), (6, 18)]
    for row in data.itertuples(index=False):
        coordinate = (round(float(row.paper_concentration_hhi), 4), round(float(row.claim_direct_fraction), 4))
        offset = offsets[coordinate_seen[coordinate] % len(offsets)]
        coordinate_seen[coordinate] += 1
        axis.annotate(
            f"{row.batch_id}-{int(row.batch_order)}",
            (row.paper_concentration_hhi, row.claim_direct_fraction),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            color="#26323D",
        )
    axis.set_xlabel("paper concentration HHI（越低，来源越分散）")
    axis.set_ylabel("claim-direct 支持比例")
    axis.set_xlim(0.0, 1.05)
    axis.set_ylim(-0.03, 1.08)
    axis.grid(True, color="#D9DEE3", linewidth=0.7, alpha=0.65)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, fontsize=8, loc="lower left")
    axis.set_title(
        "Program source leverage：来源广度 × 直接证据比例\n气泡大小=独立 source paper 数；不是成功概率",
        fontsize=14,
        weight="bold",
        pad=14,
    )
    figure.tight_layout()
    figure.savefig(output_dir / "program_source_leverage.svg", bbox_inches="tight")
    figure.savefig(output_dir / "program_source_leverage.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def report_cn(
    audit: dict[str, Any],
    program_support: pd.DataFrame,
    paths: pd.DataFrame,
    prior_edges: pd.DataFrame,
    lever_nodes: pd.DataFrame,
    lever_edges: pd.DataFrame,
    sensitivity: dict[str, Any],
    matrix_long: pd.DataFrame,
) -> str:
    noncontrol = program_support[~program_support["positive_control"]].copy()
    top = noncontrol.nsmallest(6, "evidence_reading_order")
    single_source = noncontrol[noncontrol["independent_source_paper_count"].le(1)]
    instantiated = int(matrix_long["curated_program_count"].gt(0).sum())
    total_cells = int(len(matrix_long))
    prior_counts = prior_edges["prior_art_relation"].value_counts().to_dict()
    threshold2 = sensitivity["thresholds"]["2"]
    lines = [
        "# iTE → TG graph 运行结果",
        "",
        "## 一句话结论",
        "",
        "这次跑的是 **分类型证据图**：它能回答“哪篇 iTE claim 通过哪个可操作 lever，支撑哪个 TG 实验程序，以及已有 TG 先例在哪里”；它不能回答实验成功概率。",
        "",
        "## 图是否可用",
        "",
        f"- 基础图：{audit['node_count']} 个节点、{audit['edge_count']} 条边。",
        f"- 完整性：悬空端点 {audit['missing_endpoint_count']}、typed schema 错误 {audit['typed_schema_error_count']}、重复 typed edge {audit['duplicate_typed_edges']}、self-loop {audit['self_loop_count']}。",
        f"- 图是 DAG：{audit['is_directed_acyclic_graph']}；弱连通分量 {audit['weak_component_count']}，最大分量 {audit['largest_weak_component_size']}，孤立节点 {audit['isolate_count']}。",
        f"- {audit['supports_hypothesis_pair_count']} 条 `supports_hypothesis` 与 accepted evidence pair 完全一致：{audit['supports_exactly_match_accepted_evidence']}。review queue 的 {audit['review_queue_edge_count']} 条被排除边与主图重叠 {audit['review_queue_overlap_with_primary_graph']} 条。",
        "",
        "注意：大连通分量主要是宽泛 lever taxonomy 把文献连起来，不代表这些机制已构成一个真实科学共同体。",
        "",
        "## 三层边必须分开看",
        "",
        "1. `source_verified`：论文报告 claim、TG baseline 归属。",
        "2. `taxonomy_assignment`：claim 被规则标注为某个 transferable lever。",
        "3. `curated_hypothesis`：lever/claim 被策展到 TG 程序；尚未经过实验验证。",
        "",
        "原表中的 `verified=False` 横跨第 2、3 层，不能当负样本。",
        "",
        "## Program–source leverage",
        "",
        f"当前 {len(paths)} 条支持路径来自 {paths['source_insight_id'].nunique()} 条独立 claim、{paths['source_paper_id'].nunique()} 篇独立 source paper。",
        "按来源证据覆盖读取顺序（不是成功排名）：",
        "",
    ]
    for row in top.itertuples(index=False):
        lines.append(
            f"- **{row.batch_id}-{int(row.batch_order)} {row.program_title_cn}**：{row.independent_source_paper_count} 篇 / {row.independent_source_claim_count} claim；direct={row.claim_direct_fraction:.0%}，scope caveat={row.scope_caveat_fraction:.0%}，weighted evidence mass={row.weighted_evidence_mass:.2f}。"
        )
    lines.extend(
        [
            "",
            f"只有 1 篇独立来源的程序有 {len(single_source)} 个；它们不是自动淘汰，但证据对单篇论文高度敏感，应该先做便宜的机制证伪。",
            "",
            "`weighted_evidence_mass` 只使用显式规则：A/B/C/P tier × direct/role-sentence × scope-caveat penalty。它用于发现证据薄弱点，不折算成概率。",
            "",
            "## Lever 共现图",
            "",
            f"- 至少带一个 lever 的 claim：{sensitivity['claim_count_with_at_least_one_lever']}；单 lever {sensitivity['claim_count_with_single_lever']}，多 lever {sensitivity['claim_count_with_multiple_levers']}。",
            f"- 在 w≥2 时：{threshold2['node_count']} 个 lever、{threshold2['edge_count']} 条共现边、{threshold2['nontrivial_community_count']} 个多节点社区；modularity≈{threshold2['modularity_mean']:.3f}。",
            "- 社区是“同一 claim 被共同标注的 lever 组合”；阈值敏感，不能命名成客观机制家族。",
            "",
            "## TG 先例层",
            "",
            f"已把 `tg_prior_art_by_program.csv` 的 {len(prior_edges)} 条关系派生加入增强图：direct={prior_counts.get('direct', 0)}、related={prior_counts.get('related', 0)}、source-coupled={prior_counts.get('source_coupled_benchmark', 0)}。",
            "这层让图可以明确区分“已有 TG 机制升级”和“当前本地语料未见同一组合”，但仍不是全球新颖性检索。",
            "",
            "## Lever × TG 覆盖矩阵",
            "",
            f"24 个 lever × 7 个 TG system 共 {total_cells} 个结构格，其中 {instantiated} 格有策展程序。其余 {total_cells - instantiated} 格只表示**当前规则尚未实例化**，不表示文献空白，也不应该自动生成候选。",
            "",
            "## 后面能干嘛",
            "",
            "- 现在：按 paper → claim → program → TG 路径追证据；找单来源依赖、scope caveat 和已有先例；按 B1/B2/B3 管实验。",
            "- 第一轮实验后：新增 program outcome 表，记录 pass/fail、效应量、误差、失败模式和条件，再做 active learning 或 supervised ML。",
            "- 目前不要做 link prediction：83 条候选边是规则生成的，拿它们当 positive 会让模型只复述规则。",
            "",
            "## 主要文件",
            "",
            "- `ite_tg_action_graph.svg`：15 个行动程序的 lever → program → TG 主图。",
            "- `program_graph_support.csv`：每个程序的来源广度、直接支持、caveat、先例和实验批次。",
            "- `program_evidence_paths.csv`：83 条可追溯路径。",
            "- `lever_cooccurrence_graph.svg` / `lever_cooccurrence_edges.csv`：lever 共现投影。",
            "- `lever_target_matrix.csv`：结构覆盖矩阵。",
            "- `augmented_knowledge_graph.graphml`：含完整 TG prior-art 派生层的增强图。",
            "- `graph_audit.json` / `community_sensitivity.json`：QA 与社区稳健性。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()

    frames = load_inputs(input_dir)
    nodes, repaired_count = repair_baseline_metadata(frames["nodes"], frames["programs"])
    edges = frames["edges"].copy()
    audit, component_lookup = graph_audit(nodes, edges, frames["evidence"], frames["review"])
    audit["baseline_metadata_fields_repaired_in_adapter"] = int(repaired_count)

    if any(
        [
            audit["duplicate_node_ids"],
            audit["duplicate_edge_ids"],
            audit["duplicate_typed_edges"],
            audit["missing_endpoint_count"],
            audit["typed_schema_error_count"],
            audit["self_loop_count"],
            not audit["supports_exactly_match_accepted_evidence"],
            audit["review_queue_overlap_with_primary_graph"],
        ]
    ):
        raise RuntimeError(f"Graph integrity check failed: {audit}")

    typed_metrics = typed_node_metrics(nodes, edges, component_lookup)
    program_support = program_support_table(frames["programs"], frames["evidence"], frames["actions"])
    paths = evidence_paths(frames["evidence"], frames["programs"])
    relations = program_relations(frames["programs"], frames["evidence"])
    matrix, matrix_long = lever_target_tables(nodes, frames["programs"])
    lever_nodes, lever_edges, sensitivity, lever_graph = lever_cooccurrence(
        frames["inventory"], nodes
    )
    augmented_nodes, augmented_edges, prior_edges = add_prior_art_layer(
        nodes, edges, frames["priors"]
    )

    typed_metrics.to_csv(output_dir / "typed_node_metrics.csv", index=False)
    program_support.to_csv(output_dir / "program_graph_support.csv", index=False)
    paths.to_csv(output_dir / "program_evidence_paths.csv", index=False)
    relations.to_csv(output_dir / "program_program_relations.csv", index=False)
    matrix.to_csv(output_dir / "lever_target_matrix.csv", index=False)
    matrix_long.to_csv(output_dir / "lever_target_programs.csv", index=False)
    lever_nodes.to_csv(output_dir / "lever_cooccurrence_nodes.csv", index=False)
    lever_edges.to_csv(output_dir / "lever_cooccurrence_edges.csv", index=False)
    prior_edges.to_csv(output_dir / "tg_prior_art_program_edges.csv", index=False)
    augmented_nodes.to_csv(output_dir / "augmented_graph_nodes.csv", index=False)
    augmented_edges.to_csv(output_dir / "augmented_graph_edges.csv", index=False)
    write_json(output_dir / "graph_audit.json", audit)
    write_json(output_dir / "community_sensitivity.json", sensitivity)

    base_graph = make_base_graph(nodes, edges)
    augmented_graph = make_base_graph(augmented_nodes, augmented_edges)
    write_graphml(output_dir / "knowledge_graph.graphml", base_graph)
    write_graphml(output_dir / "augmented_knowledge_graph.graphml", augmented_graph)
    write_graphml(output_dir / "lever_cooccurrence.graphml", lever_graph)
    write_graphml(output_dir / "program_projection.graphml", projection_graph(frames["programs"], relations))

    plot_action_overview(program_support, output_dir)
    plot_lever_graph(lever_graph, output_dir)
    plot_program_leverage(program_support, output_dir)

    report = report_cn(
        audit,
        program_support,
        paths,
        prior_edges,
        lever_nodes,
        lever_edges,
        sensitivity,
        matrix_long,
    )
    (output_dir / "GRAPH_RESULTS_CN.md").write_text(report, encoding="utf-8")

    input_files = sorted(
        [
            input_dir / "knowledge_graph_nodes.csv",
            input_dir / "knowledge_graph_edges.csv",
            input_dir / "ite_tg_complementarity_programs.csv",
            input_dir / "ite_tg_candidate_evidence.csv",
            input_dir / "ite_claim_inventory_with_levers.csv",
            input_dir / "ite_tg_next_action_queue.csv",
            input_dir / "tg_prior_art_by_program.csv",
            input_dir / "ite_tg_edge_review_queue.csv",
        ]
    )
    output_files = sorted(
        path for path in output_dir.iterdir() if path.is_file() and path.name != "graph_analysis_manifest.json"
    )
    manifest = {
        "analysis_name": "typed_iTE_to_TG_evidence_graph",
        "layout_seed": LAYOUT_SEED,
        "community_random_seeds": 100,
        "community_thresholds": [1, 2, 3],
        "input_sha256": {path.name: sha256_file(path) for path in input_files},
        "output_sha256": {path.name: sha256_file(path) for path in output_files},
        "counts": {
            "base_nodes": int(len(nodes)),
            "base_edges": int(len(edges)),
            "augmented_nodes": int(len(augmented_nodes)),
            "augmented_edges": int(len(augmented_edges)),
            "programs": int(len(program_support)),
            "noncontrol_programs": int((~program_support["positive_control"]).sum()),
            "evidence_paths": int(len(paths)),
            "TG_prior_art_edges": int(len(prior_edges)),
            "lever_cooccurrence_edges_w_ge_1": int(len(lever_edges)),
            "lever_cooccurrence_edges_w_ge_2": int(lever_edges["cooccurring_claim_count"].ge(2).sum()),
        },
        "label_policy": {
            "supervised_success_label_present": False,
            "verified_false_used_as_negative": False,
            "supports_hypothesis_used_as_positive": False,
            "priority_score_used_as_target": False,
        },
    }
    write_json(output_dir / "graph_analysis_manifest.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
