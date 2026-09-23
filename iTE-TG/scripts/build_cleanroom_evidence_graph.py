#!/usr/bin/env python3
"""Materialize the cleanroom iTE–TG evidence graph without creating closure facts.

The exporter has a deliberately narrow contract:

* layer-qualified concept nodes are facts extracted from direct-layer abstracts;
* same-sentence pair edges are observed co-occurrences, not causal relations;
* cross-layer alignment edges mean exact normalized identity only;
* relation extractions remain a separate audit graph unless independently eligible;
* candidate paths and cross-endpoint mappings never enter an observed GraphML.

No file from the legacy complementarity/graph-analysis workflow is read here.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET

import networkx as nx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "cleanroom_abstract_pair_layer"
DEFAULT_OUTPUT = DEFAULT_INPUT / "evidence_graph"
DIRECT_LAYERS = ("iTE", "TG")
ALLOWED_CROSS_ENDPOINT_STATUS = {
    "iTE": {
        "not_observed_in_frozen_iTE_abstract_corpus",
        "already_observed_in_iTE",
    },
    "TG": {
        "not_observed_in_frozen_TG_abstract_corpus",
        "already_observed_in_TG",
    },
}
REVIEW_GRADE_CLASS_AND_ORDER = {
    "R2_dual_direct_sentence_relations": ("R2", 1),
    "R1_single_direct_sentence_relation": ("R1", 2),
    "R0_cooccurrence_only_or_rejected": ("R0", 3),
}
MACHINE_GRADE_CLASS_AND_ORDER = {
    "G2_dual_strict_syntax_candidates": ("G2", 1),
    "G1_single_strict_syntax_candidate": ("G1", 2),
    "G0_cooccurrence_only": ("G0", 3),
}

EXPECTED_V3 = {
    "concept_nodes": 3172,
    "pair_endpoint_nodes": 2853,
    "isolated_concept_nodes": 319,
    "pair_edges": 6413,
    "ite_pair_edges": 4023,
    "tg_pair_edges": 2390,
    "exact_alignments_all": 196,
    "exact_alignments_pair_endpoints": 167,
    "direct_relation_audit_edges": 241,
    "direct_strict_relation_candidates": 52,
    "observed_relation_edges": 0,
    "candidate_paths_all": 50025,
    "candidate_paths_focus_pre_gate": 20157,
    "candidate_paths_endpoint_pass": 12721,
    "candidate_paths_quarantine": 7436,
    "oriented_cross_endpoint_candidates": 12456,
    "unordered_cross_endpoint_groups": 12412,
    "mirrored_unordered_groups": 44,
    "review_queue_paths": 397,
}


def clean(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def as_bool(value: object) -> bool:
    return clean(value).casefold() in {"1", "true", "yes", "y", "affirmed"}


def stable_id(prefix: str, *values: object) -> str:
    payload = "\x1f".join(clean(value).casefold() for value in values)
    return f"{prefix}_{sha1(payload.encode('utf-8')).hexdigest()[:12]}"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frame_sha256(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return sha256(payload).hexdigest()


def sorted_unique(values: Iterable[object]) -> list[str]:
    return sorted({clean(value) for value in values if clean(value)})


def join_unique(values: Iterable[object], separator: str = "; ") -> str:
    return separator.join(sorted_unique(values))


def deterministic_mode(values: Iterable[object]) -> str:
    cleaned = [clean(value) for value in values if clean(value)]
    if not cleaned:
        return ""
    counts = Counter(cleaned)
    return sorted(counts, key=lambda value: (-counts[value], value))[0]


def safe_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def graphml_scalar(value: object) -> str | int | float | bool:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    return clean(value)


def effective_production_eligible(
    relation: Mapping[str, object], review: Mapping[str, object]
) -> bool:
    """Single authoritative promotion gate used by nodes, pairs and relations."""
    return (
        as_bool(relation.get("strict_syntax_eligible", False))
        and clean(relation.get("assertion_status")) == "observed_assertion"
        and clean(review.get("semantic_verdict")) == "accepted"
        and as_bool(review.get("direct_sentence_entailment", False))
        and as_bool(review.get("production_graph_eligible", False))
        and clean(review.get("human_confirmation_status")) == "affirmed"
    )


def grade_class(value: object) -> str:
    return REVIEW_GRADE_CLASS_AND_ORDER.get(clean(value), ("UNCLASSIFIED", 99))[0]


def expected_grade_order(value: object, namespace: object) -> int:
    grade = clean(value)
    if clean(namespace).startswith("R_"):
        return REVIEW_GRADE_CLASS_AND_ORDER.get(grade, ("UNCLASSIFIED", 99))[1]
    if clean(namespace).startswith("G_"):
        return MACHINE_GRADE_CLASS_AND_ORDER.get(grade, ("UNCLASSIFIED", 99))[1]
    return 99


def read_csv(input_dir: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(input_dir / name, low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def load_inputs(input_dir: Path) -> dict[str, pd.DataFrame]:
    names = {
        "concepts": "paper_concepts.csv",
        "ite_pairs": "ite_pair_bank.csv",
        "tg_pairs": "tg_pair_bank.csv",
        "support": "pair_support_evidence.csv",
        "relations": "abstract_relations.csv",
        "adjudication": "relation_semantic_adjudication.csv",
        "shared_summary": "all_shared_node_evidence_summary.csv",
        "direct_overlaps": "direct_pair_overlaps.csv",
        "paths_all": "tiered_shared_node_pair_candidates_full.csv",
        "paths_focus": "tiered_focus_node_pair_paths_full.csv",
        "paths_pass": "semantic_reviewed_focus_candidates.csv",
        "paths_quarantine": "tiered_focus_endpoint_quarantine.csv",
        "review_queue": "balanced_focus_review_queue.csv",
    }
    return {key: read_csv(input_dir, filename) for key, filename in names.items()}


def validate_upstream_contract(
    input_dir: Path, data: dict[str, pd.DataFrame]
) -> dict[str, object]:
    required_columns = {
        "concepts": {
            "paper_id", "analysis_layer", "year", "normalized_label",
            "lexical_category", "global_concept_id", "layer_node_id",
        },
        "ite_pairs": {
            "pair_id", "analysis_layer", "pair_key", "left_global_concept_id",
            "right_global_concept_id", "paper_count", "sentence_count",
        },
        "tg_pairs": {
            "pair_id", "analysis_layer", "pair_key", "left_global_concept_id",
            "right_global_concept_id", "paper_count", "sentence_count",
        },
        "support": {
            "pair_evidence_id", "pair_id", "sentence_pair_id", "relation_id",
            "paper_id", "evidence_sentence", "strict_syntax_eligible",
        },
        "relations": {
            "relation_id", "analysis_layer", "source_global_concept_id",
            "target_global_concept_id", "assertion_status", "strict_syntax_eligible",
        },
        "adjudication": {
            "relation_id", "semantic_verdict", "direct_sentence_entailment",
            "production_graph_eligible", "human_confirmation_status",
        },
        "paths_all": {
            "candidate_id", "shared_global_concept_id", "ite_pair_id", "tg_pair_id",
            "ite_other_global_concept_id", "tg_other_global_concept_id",
        },
        "paths_focus": {
            "candidate_id", "shared_global_concept_id", "ite_pair_id", "tg_pair_id",
            "ite_other_global_concept_id", "tg_other_global_concept_id",
        },
        "paths_pass": {
            "candidate_id", "shared_global_concept_id", "ite_pair_id", "tg_pair_id",
            "review_adjusted_evidence_grade", "review_adjusted_evidence_grade_order",
        },
        "paths_quarantine": {
            "candidate_id", "shared_global_concept_id", "ite_pair_id", "tg_pair_id",
        },
    }
    missing = {
        key: sorted(columns - set(data[key].columns))
        for key, columns in required_columns.items()
        if columns - set(data[key].columns)
    }
    run_manifest_path = input_dir / "run_manifest.json"
    base_qa_path = input_dir / "qa_report.json"
    semantic_qa_path = input_dir / "semantic_review_qa.json"
    for path in (run_manifest_path, base_qa_path, semantic_qa_path):
        if not path.is_file():
            raise ValueError(f"missing upstream contract file: {path.name}")
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    base_qa = json.loads(base_qa_path.read_text(encoding="utf-8"))
    semantic_qa = json.loads(semantic_qa_path.read_text(encoding="utf-8"))
    upstream_builder_path = ROOT / "scripts" / "build_cleanroom_abstract_pair_layer.py"
    upstream_builder_hash = (
        file_sha256(upstream_builder_path) if upstream_builder_path.is_file() else ""
    )
    checks = {
        "required_columns_present": not missing,
        "upstream_pipeline_is_cleanroom_v3": run_manifest.get("pipeline")
        == "cleanroom_abstract_pair_layer_v3",
        "upstream_base_qa_passed": base_qa.get("all_checks_pass") is True,
        "upstream_semantic_qa_passed": semantic_qa.get("all_checks_pass") is True,
        "upstream_builder_hash_matches_manifest": bool(upstream_builder_hash)
        and run_manifest.get("script_sha256") == upstream_builder_hash,
    }
    if not all(checks.values()):
        raise ValueError(f"invalid upstream contract: checks={checks}, missing={missing}")
    return {
        "checks": checks,
        "missing_columns": missing,
        "run_manifest_sha256": file_sha256(run_manifest_path),
        "base_qa_sha256": file_sha256(base_qa_path),
        "semantic_qa_sha256": file_sha256(semantic_qa_path),
        "upstream_builder_sha256": upstream_builder_hash,
    }


def build_node_registry(
    concepts: pd.DataFrame,
    pair_banks: pd.DataFrame,
    relations: pd.DataFrame,
    adjudication: pd.DataFrame,
    shared_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[tuple[str, str], str]]:
    direct = concepts[concepts["analysis_layer"].isin(DIRECT_LAYERS)].copy()
    direct_relations = relations[relations["analysis_layer"].isin(DIRECT_LAYERS)].copy()
    adjud_by_relation = adjudication.set_index("relation_id").to_dict("index")

    pair_degree: Counter[tuple[str, str]] = Counter()
    for row in pair_banks.itertuples(index=False):
        pair_degree[(row.analysis_layer, row.left_global_concept_id)] += 1
        pair_degree[(row.analysis_layer, row.right_global_concept_id)] += 1

    relation_stats: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in direct_relations.itertuples(index=False):
        review = adjud_by_relation.get(row.relation_id, {})
        verdict = clean(review.get("semantic_verdict", "pending")) or "pending"
        production = effective_production_eligible(row._asdict(), review)
        for global_id in {row.source_global_concept_id, row.target_global_concept_id}:
            key = (row.analysis_layer, global_id)
            relation_stats[key]["all"] += 1
            if as_bool(row.strict_syntax_eligible):
                relation_stats[key]["strict"] += 1
            relation_stats[key][f"semantic_{verdict}"] += 1
            if production:
                relation_stats[key]["production"] += 1

    shared_info = shared_summary.set_index("shared_global_concept_id").to_dict("index")
    rows: list[dict[str, Any]] = []
    local_lookup: dict[tuple[str, str], str] = {}
    for (layer, global_id), group in direct.groupby(
        ["analysis_layer", "global_concept_id"], sort=True
    ):
        local_ids = sorted_unique(group["layer_node_id"])
        labels = sorted_unique(group["normalized_label"])
        if len(local_ids) != 1:
            raise ValueError(f"non-unique layer node for {(layer, global_id)}: {local_ids}")
        if len(labels) != 1:
            raise ValueError(f"non-unique label for {global_id}: {labels}")
        local_id = local_ids[0]
        local_lookup[(layer, global_id)] = local_id
        stats = relation_stats[(layer, global_id)]
        shared = shared_info.get(global_id, {})
        degree = pair_degree[(layer, global_id)]
        rows.append(
            {
                "node_id": local_id,
                "layer_node_id": local_id,
                "analysis_layer": layer,
                "global_concept_id": global_id,
                "normalized_label": labels[0],
                "lexical_category": deterministic_mode(group["lexical_category"]),
                "layer_document_frequency": int(group["paper_id"].nunique()),
                "occurrence_count": int(
                    pd.to_numeric(group["occurrence_count"], errors="coerce")
                    .fillna(1)
                    .sum()
                ),
                "first_year": int(pd.to_numeric(group["year"], errors="coerce").min()),
                "last_year": int(pd.to_numeric(group["year"], errors="coerce").max()),
                "pair_endpoint_eligible": degree > 0,
                "pair_degree": degree,
                "relation_candidate_incident_count": stats["all"],
                "strict_relation_incident_count": stats["strict"],
                "semantic_accepted_relation_incident_count": stats["semantic_accepted"],
                "semantic_rejected_relation_incident_count": stats["semantic_rejected"],
                "semantic_pending_relation_incident_count": stats["semantic_pending"],
                "production_relation_incident_count": stats["production"],
                "shared_pair_endpoint_focus_eligible": as_bool(
                    shared.get("shared_node_focus_eligible", False)
                ),
                "shared_pair_endpoint_release_status": clean(
                    shared.get("release_status", "not_in_shared_pair_inventory")
                ),
                "node_fact_status": "selected_direct_abstract_concept",
            }
        )

    frame = pd.DataFrame(rows).sort_values(
        ["analysis_layer", "global_concept_id"]
    ).reset_index(drop=True)
    global_layers = frame.groupby("global_concept_id")["analysis_layer"].nunique()
    exact_shared = set(global_layers[global_layers.eq(2)].index)
    pair_shared = {
        global_id
        for global_id in exact_shared
        if pair_degree[("iTE", global_id)] > 0 and pair_degree[("TG", global_id)] > 0
    }
    frame["is_exact_shared_selected_concept"] = frame["global_concept_id"].isin(
        exact_shared
    )
    frame["is_exact_shared_pair_endpoint"] = frame["global_concept_id"].isin(
        pair_shared
    )
    frame["node_role"] = frame.apply(
        lambda row: (
            "exact_shared_pair_endpoint"
            if row["is_exact_shared_pair_endpoint"]
            else "exact_shared_isolate_or_one_sided_pair_endpoint"
            if row["is_exact_shared_selected_concept"]
            else "layer_pair_endpoint"
            if row["pair_endpoint_eligible"]
            else "layer_isolated_selected_concept"
        ),
        axis=1,
    )
    return frame, local_lookup


def build_alignment_edges(
    nodes: pd.DataFrame,
    local_lookup: dict[tuple[str, str], str],
    shared_summary: pd.DataFrame,
    paths_all: pd.DataFrame,
    paths_pass: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, str]]:
    by_layer = {
        layer: set(nodes.loc[nodes["analysis_layer"].eq(layer), "global_concept_id"])
        for layer in DIRECT_LAYERS
    }
    shared_ids = sorted(by_layer["iTE"] & by_layer["TG"])
    node_by_local = nodes.set_index("layer_node_id").to_dict("index")
    shared_info = shared_summary.set_index("shared_global_concept_id").to_dict("index")
    all_counts = paths_all.groupby("shared_global_concept_id").size().to_dict()
    pass_counts = paths_pass.groupby("shared_global_concept_id").size().to_dict()
    rows = []
    alignment_lookup: dict[str, str] = {}
    for global_id in shared_ids:
        ite_node = local_lookup[("iTE", global_id)]
        tg_node = local_lookup[("TG", global_id)]
        ite = node_by_local[ite_node]
        tg = node_by_local[tg_node]
        alignment_id = stable_id("AL", global_id, ite_node, tg_node)
        alignment_lookup[global_id] = alignment_id
        shared = shared_info.get(global_id, {})
        both_pair = bool(ite["pair_endpoint_eligible"] and tg["pair_endpoint_eligible"])
        rows.append(
            {
                "alignment_id": alignment_id,
                "edge_id": alignment_id,
                "edge_type": "exact_node_alignment",
                "global_concept_id": global_id,
                "normalized_label": ite["normalized_label"],
                "ite_layer_node_id": ite_node,
                "tg_layer_node_id": tg_node,
                "source_node_id": ite_node,
                "target_node_id": tg_node,
                "alignment_method": "exact_global_concept_id",
                "exact_label_match": ite["normalized_label"] == tg["normalized_label"],
                "category_match": ite["lexical_category"] == tg["lexical_category"],
                "ite_lexical_category": ite["lexical_category"],
                "tg_lexical_category": tg["lexical_category"],
                "both_pair_endpoints": both_pair,
                "path_eligible": both_pair,
                "all_nontrivial_path_count": int(all_counts.get(global_id, 0)),
                "endpoint_pass_focus_path_count": int(pass_counts.get(global_id, 0)),
                "focus_eligible": as_bool(shared.get("shared_node_focus_eligible", False)),
                "release_status": clean(
                    shared.get(
                        "release_status",
                        "not_in_pair_path_inventory" if not both_pair else "not_focus_eligible",
                    )
                ),
                "directed": False,
                "scientific_relation": False,
                "causal_claim_allowed": False,
                "graph_edge_status": "alignment_identity_not_scientific_relation",
            }
        )
    return pd.DataFrame(rows).sort_values("global_concept_id").reset_index(drop=True), alignment_lookup


def build_pair_edges(
    pair_banks: pd.DataFrame,
    support: pd.DataFrame,
    relations: pd.DataFrame,
    adjudication: pd.DataFrame,
    direct_overlaps: pd.DataFrame,
    local_lookup: dict[tuple[str, str], str],
) -> pd.DataFrame:
    adjud_by_relation = adjudication.set_index("relation_id").to_dict("index")
    relation_by_id = relations.set_index("relation_id").to_dict("index")
    support_by_pair = {key: group for key, group in support.groupby("pair_id")}
    overlap_partner: dict[str, str] = {}
    overlap_id: dict[str, str] = {}
    for row in direct_overlaps.itertuples(index=False):
        overlap_partner[row.pair_id_ite] = row.pair_id_tg
        overlap_partner[row.pair_id_tg] = row.pair_id_ite
        overlap_id[row.pair_id_ite] = row.overlap_id
        overlap_id[row.pair_id_tg] = row.overlap_id

    rows = []
    for row in pair_banks.itertuples(index=False):
        evidence = support_by_pair.get(row.pair_id, pd.DataFrame())
        relation_ids = sorted_unique(
            evidence["relation_id"] if not evidence.empty else []
        )
        strict_relation_ids = sorted_unique(
            evidence.loc[
                evidence["strict_syntax_eligible"].map(as_bool), "relation_id"
            ]
            if not evidence.empty
            else []
        )
        accepted = [
            rid
            for rid in strict_relation_ids
            if clean(adjud_by_relation.get(rid, {}).get("semantic_verdict")) == "accepted"
        ]
        rejected = [
            rid
            for rid in strict_relation_ids
            if clean(adjud_by_relation.get(rid, {}).get("semantic_verdict")) == "rejected"
        ]
        reviewed = set(accepted) | set(rejected)
        pending = [rid for rid in strict_relation_ids if rid not in reviewed]
        production = [
            rid
            for rid in accepted
            if effective_production_eligible(
                relation_by_id.get(rid, {}), adjud_by_relation.get(rid, {})
            )
        ]
        if production:
            semantic_status = "human_confirmed_production_relation"
        elif accepted:
            semantic_status = "semantic_accepted_human_pending"
        elif pending:
            semantic_status = "machine_strict_pending_semantic_review"
        elif rejected:
            semantic_status = "semantic_rejected_cooccurrence_retained"
        else:
            semantic_status = "same_sentence_cooccurrence_only"
        rows.append(
            {
                "pair_id": row.pair_id,
                "edge_id": row.pair_id,
                "edge_type": "same_sentence_pair",
                "analysis_layer": row.analysis_layer,
                "pair_key": row.pair_key,
                "left_global_concept_id": row.left_global_concept_id,
                "left_label": row.left_label,
                "left_layer_node_id": local_lookup[
                    (row.analysis_layer, row.left_global_concept_id)
                ],
                "right_global_concept_id": row.right_global_concept_id,
                "right_label": row.right_label,
                "right_layer_node_id": local_lookup[
                    (row.analysis_layer, row.right_global_concept_id)
                ],
                "source_node_id": local_lookup[
                    (row.analysis_layer, row.left_global_concept_id)
                ],
                "target_node_id": local_lookup[
                    (row.analysis_layer, row.right_global_concept_id)
                ],
                "directed": False,
                "paper_count": safe_int(row.paper_count),
                "sentence_count": safe_int(row.sentence_count),
                "strict_syntax_relation_paper_count": safe_int(
                    row.strict_syntax_relation_paper_count
                ),
                "first_year": safe_int(row.first_year),
                "last_year": safe_int(row.last_year),
                "atomic_evidence_record_count": len(evidence),
                "unique_sentence_support_count": int(
                    evidence["sentence_pair_id"].nunique() if not evidence.empty else 0
                ),
                "authoritative_provenance_fk": row.pair_id,
                "relation_candidate_ids": "; ".join(relation_ids),
                "strict_relation_candidate_ids": "; ".join(strict_relation_ids),
                "semantic_accepted_relation_ids": "; ".join(accepted),
                "semantic_rejected_relation_ids": "; ".join(rejected),
                "semantic_pending_relation_ids": "; ".join(pending),
                "production_relation_ids": "; ".join(production),
                "pair_evidence_status": semantic_status,
                "is_direct_exact_pair_overlap": row.pair_id in overlap_partner,
                "direct_pair_overlap_id": overlap_id.get(row.pair_id, ""),
                "cross_layer_partner_pair_id": overlap_partner.get(row.pair_id, ""),
                "observed_evidence": True,
                "causal_claim": False,
                "graph_edge_status": "observed_pair_topology_noncausal",
            }
        )
    return pd.DataFrame(rows).sort_values(["analysis_layer", "pair_id"]).reset_index(
        drop=True
    )


def build_relation_audit_edges(
    relations: pd.DataFrame,
    adjudication: pd.DataFrame,
    pair_edges: pd.DataFrame,
    local_lookup: dict[tuple[str, str], str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    direct = relations[relations["analysis_layer"].isin(DIRECT_LAYERS)].copy()
    adjud_by_relation = adjudication.set_index("relation_id").to_dict("index")
    pair_lookup = pair_edges.set_index(["analysis_layer", "pair_key"])[
        "pair_id"
    ].to_dict()
    rows = []
    for row in direct.itertuples(index=False):
        pair_key = "::".join(
            sorted([row.source_global_concept_id, row.target_global_concept_id])
        )
        review = adjud_by_relation.get(row.relation_id, {})
        verdict = clean(review.get("semantic_verdict", "pending")) or "pending"
        strict = as_bool(row.strict_syntax_eligible)
        production = effective_production_eligible(row._asdict(), review)
        if production:
            state = "human_confirmed_observed"
        elif verdict == "accepted":
            state = "semantic_accepted_human_pending"
        elif verdict == "rejected":
            state = "semantic_rejected"
        elif strict:
            state = "strict_unreviewed_candidate"
        else:
            state = "audit_non_strict"
        rows.append(
            {
                "relation_id": row.relation_id,
                "edge_id": row.relation_id,
                "edge_type": "direct_relation_candidate_audit",
                "analysis_layer": row.analysis_layer,
                "paper_id": row.paper_id,
                "doi": clean(row.doi),
                "title": row.title,
                "sentence_id": safe_int(row.sentence_id),
                "evidence_sentence": row.evidence_sentence,
                "source_global_concept_id": row.source_global_concept_id,
                "source_label": row.source_normalized_label,
                "source_node_id": local_lookup[
                    (row.analysis_layer, row.source_global_concept_id)
                ],
                "predicate_surface": row.predicate_surface,
                "predicate_normalized": row.predicate_normalized,
                "target_global_concept_id": row.target_global_concept_id,
                "target_label": row.target_normalized_label,
                "target_node_id": local_lookup[
                    (row.analysis_layer, row.target_global_concept_id)
                ],
                "pair_id": pair_lookup.get((row.analysis_layer, pair_key), ""),
                "pair_key": pair_key,
                "assertion_status": row.assertion_status,
                "risk_reasons": clean(row.risk_reasons),
                "strict_syntax_eligible": strict,
                "semantic_verdict": verdict,
                "direct_sentence_entailment": as_bool(
                    review.get("direct_sentence_entailment", False)
                ),
                "claim_context": clean(review.get("claim_context", "not_reviewed")),
                "human_confirmation_status": clean(
                    review.get("human_confirmation_status", "pending")
                )
                or "pending",
                "review_basis": clean(review.get("review_basis", "not_reviewed")),
                "decision_rationale": clean(review.get("decision_rationale", "")),
                "edge_state": state,
                "directed": True,
                "graph_eligible": production,
                "production_graph_eligible": production,
                "graph_edge_status": "audit_only" if not production else "observed_relation",
            }
        )
    audit = pd.DataFrame(rows).sort_values(
        ["analysis_layer", "paper_id", "relation_id"]
    ).reset_index(drop=True)
    observed = audit[audit["production_graph_eligible"]].copy().reset_index(drop=True)
    return audit, observed


def normalize_paths(
    source: pd.DataFrame,
    scope: str,
    path_state: str,
    nodes: pd.DataFrame,
    local_lookup: dict[tuple[str, str], str],
    alignment_lookup: dict[str, str],
    pair_edges: pd.DataFrame,
    adjudication: pd.DataFrame,
    shared_summary: pd.DataFrame,
    review_queue: pd.DataFrame,
) -> pd.DataFrame:
    pair_by_id = pair_edges.set_index("pair_id").to_dict("index")
    node_by_key = nodes.set_index(["analysis_layer", "global_concept_id"]).to_dict(
        "index"
    )
    observed_pair_keys = {
        layer: set(
            pair_edges.loc[pair_edges["analysis_layer"].eq(layer), "pair_key"]
        )
        for layer in DIRECT_LAYERS
    }
    verdict_by_relation = adjudication.set_index("relation_id")[
        "semantic_verdict"
    ].map(clean).to_dict()
    has_review_overlay = "review_adjusted_evidence_grade" in source.columns
    shared_info = shared_summary.set_index("shared_global_concept_id").to_dict("index")
    queue_info = review_queue.set_index("candidate_id").to_dict("index")
    rows = []
    for row in source.to_dict("records"):
        shared_id = row["shared_global_concept_id"]
        ite_other = row["ite_other_global_concept_id"]
        tg_other = row["tg_other_global_concept_id"]
        ite_pair = pair_by_id[row["ite_pair_id"]]
        tg_pair = pair_by_id[row["tg_pair_id"]]
        shared = shared_info.get(shared_id, {})
        queue = queue_info.get(row["candidate_id"], {})
        source_reviewed_grade = clean(row.get("review_adjusted_evidence_grade"))
        source_reviewed_grade_order = safe_int(
            row.get("review_adjusted_evidence_grade_order"), default=99
        )
        source_base_grade = clean(row.get("evidence_grade"))
        source_base_grade_order = safe_int(row.get("evidence_grade_order"), default=99)
        ite_strict_ids = sorted_unique(
            clean(ite_pair["strict_relation_candidate_ids"]).split("; ")
        )
        tg_strict_ids = sorted_unique(
            clean(tg_pair["strict_relation_candidate_ids"]).split("; ")
        )
        strict_side_count = int(bool(ite_strict_ids)) + int(bool(tg_strict_ids))
        if strict_side_count == 2:
            base_grade, base_grade_order = (
                "G2_dual_strict_syntax_candidates",
                1,
            )
        elif strict_side_count == 1:
            base_grade, base_grade_order = (
                "G1_single_strict_syntax_candidate",
                2,
            )
        else:
            base_grade, base_grade_order = "G0_cooccurrence_only", 3

        def reviewed_side_status(relation_ids: list[str]) -> str:
            verdicts = {verdict_by_relation.get(relation_id, "pending") for relation_id in relation_ids}
            if "accepted" in verdicts:
                return "direct_sentence_relation_accepted"
            if "rejected" in verdicts:
                return "machine_relation_rejected_retain_cooccurrence_only"
            if relation_ids:
                return "machine_relation_pending_semantic_review"
            return "cooccurrence_only"

        canonical_ite_semantic_status = reviewed_side_status(ite_strict_ids)
        canonical_tg_semantic_status = reviewed_side_status(tg_strict_ids)
        accepted_side_count = int(
            canonical_ite_semantic_status == "direct_sentence_relation_accepted"
        ) + int(
            canonical_tg_semantic_status == "direct_sentence_relation_accepted"
        )
        if has_review_overlay and accepted_side_count == 2:
            evidence_grade, evidence_grade_order = (
                "R2_dual_direct_sentence_relations",
                1,
            )
        elif has_review_overlay and accepted_side_count == 1:
            evidence_grade, evidence_grade_order = (
                "R1_single_direct_sentence_relation",
                2,
            )
        elif has_review_overlay:
            evidence_grade, evidence_grade_order = (
                "R0_cooccurrence_only_or_rejected",
                3,
            )
        else:
            evidence_grade, evidence_grade_order = base_grade, base_grade_order
        grade_namespace = (
            "R_independent_AI_sentence_semantic_review"
            if has_review_overlay
            else "G_machine_syntax_candidate_grade"
        )
        grade_basis = (
            "two_independent_AI_sentence_reviews_human_confirmation_pending"
            if has_review_overlay
            else "same_sentence_pair_plus_machine_strict_syntax_support"
        )
        ite_shared_node = node_by_key[("iTE", shared_id)]
        tg_shared_node = node_by_key[("TG", shared_id)]
        ite_other_node = node_by_key[("iTE", ite_other)]
        tg_other_node = node_by_key[("TG", tg_other)]
        cross_pair_key = "::".join(sorted([ite_other, tg_other]))
        derived_ite_status = (
            "already_observed_in_iTE"
            if cross_pair_key in observed_pair_keys["iTE"]
            else "not_observed_in_frozen_iTE_abstract_corpus"
        )
        derived_tg_status = (
            "already_observed_in_TG"
            if cross_pair_key in observed_pair_keys["TG"]
            else "not_observed_in_frozen_TG_abstract_corpus"
        )
        source_ite_status = clean(row.get("cross_endpoint_status_in_iTE"))
        source_tg_status = clean(row.get("cross_endpoint_status_in_TG"))
        canonical_ite_paper_count = safe_int(ite_pair["paper_count"])
        canonical_ite_sentence_count = safe_int(ite_pair["sentence_count"])
        canonical_tg_paper_count = safe_int(tg_pair["paper_count"])
        canonical_tg_sentence_count = safe_int(tg_pair["sentence_count"])
        canonical_minimum_paper_count = min(
            canonical_ite_paper_count, canonical_tg_paper_count
        )
        canonical_minimum_sentence_count = min(
            canonical_ite_sentence_count, canonical_tg_sentence_count
        )
        source_ite_strict_ids = clean(row.get("ite_strict_relation_ids"))
        source_tg_strict_ids = clean(row.get("tg_strict_relation_ids"))
        rows.append(
            {
                "candidate_id": row["candidate_id"],
                "path_scope": scope,
                "path_state": path_state,
                "graph_eligible": False,
                "scientific_claim_status": clean(
                    row.get("scientific_claim_status", "retrieval_candidate_only")
                )
                or "retrieval_candidate_only",
                "shared_global_concept_id": shared_id,
                "shared_label": ite_shared_node["normalized_label"],
                "shared_category": ite_shared_node["lexical_category"],
                "source_shared_label_matches_registry": clean(row["shared_label"])
                == ite_shared_node["normalized_label"],
                "source_shared_category_matches_registry": clean(row["shared_category"])
                == ite_shared_node["lexical_category"],
                "shared_layer_labels_match": ite_shared_node["normalized_label"]
                == tg_shared_node["normalized_label"],
                "shared_layer_categories_match": ite_shared_node["lexical_category"]
                == tg_shared_node["lexical_category"],
                "ite_shared_layer_node_id": local_lookup[("iTE", shared_id)],
                "tg_shared_layer_node_id": local_lookup[("TG", shared_id)],
                "alignment_id": alignment_lookup[shared_id],
                "alignment_state": "exact_identity_not_scientific_relation",
                "ite_pair_id": row["ite_pair_id"],
                "ite_pair_edge_status": ite_pair["pair_evidence_status"],
                "ite_other_global_concept_id": ite_other,
                "ite_other_label": ite_other_node["normalized_label"],
                "ite_other_category": ite_other_node["lexical_category"],
                "source_ite_other_label_matches_registry": clean(
                    row["ite_other_label"]
                )
                == ite_other_node["normalized_label"],
                "source_ite_other_category_matches_registry": clean(
                    row["ite_other_category"]
                )
                == ite_other_node["lexical_category"],
                "ite_other_layer_node_id": local_lookup[("iTE", ite_other)],
                "ite_pair_paper_count": canonical_ite_paper_count,
                "ite_pair_sentence_count": canonical_ite_sentence_count,
                "source_ite_pair_paper_count_matches_pair_bank": safe_int(
                    row.get("ite_pair_paper_count")
                )
                == canonical_ite_paper_count,
                "source_ite_pair_sentence_count_matches_pair_bank": safe_int(
                    row.get("ite_pair_sentence_count")
                )
                == canonical_ite_sentence_count,
                "ite_strict_relation_ids": ite_pair["strict_relation_candidate_ids"],
                "source_ite_strict_relation_ids_match_pair_bank": (
                    source_ite_strict_ids
                    == clean(ite_pair["strict_relation_candidate_ids"])
                ),
                "ite_semantic_relation_review_status": (
                    canonical_ite_semantic_status
                    if has_review_overlay
                    else "not_applied_base_machine_grade"
                ),
                "source_ite_semantic_review_status_matches_recomputed": (
                    not has_review_overlay
                    or clean(row.get("ite_semantic_relation_review_status"))
                    == canonical_ite_semantic_status
                ),
                "ite_authoritative_provenance_fk": row["ite_pair_id"],
                "tg_pair_id": row["tg_pair_id"],
                "tg_pair_edge_status": tg_pair["pair_evidence_status"],
                "tg_other_global_concept_id": tg_other,
                "tg_other_label": tg_other_node["normalized_label"],
                "tg_other_category": tg_other_node["lexical_category"],
                "source_tg_other_label_matches_registry": clean(
                    row["tg_other_label"]
                )
                == tg_other_node["normalized_label"],
                "source_tg_other_category_matches_registry": clean(
                    row["tg_other_category"]
                )
                == tg_other_node["lexical_category"],
                "tg_other_layer_node_id": local_lookup[("TG", tg_other)],
                "tg_pair_paper_count": canonical_tg_paper_count,
                "tg_pair_sentence_count": canonical_tg_sentence_count,
                "source_tg_pair_paper_count_matches_pair_bank": safe_int(
                    row.get("tg_pair_paper_count")
                )
                == canonical_tg_paper_count,
                "source_tg_pair_sentence_count_matches_pair_bank": safe_int(
                    row.get("tg_pair_sentence_count")
                )
                == canonical_tg_sentence_count,
                "tg_strict_relation_ids": tg_pair["strict_relation_candidate_ids"],
                "source_tg_strict_relation_ids_match_pair_bank": (
                    source_tg_strict_ids
                    == clean(tg_pair["strict_relation_candidate_ids"])
                ),
                "tg_semantic_relation_review_status": (
                    canonical_tg_semantic_status
                    if has_review_overlay
                    else "not_applied_base_machine_grade"
                ),
                "source_tg_semantic_review_status_matches_recomputed": (
                    not has_review_overlay
                    or clean(row.get("tg_semantic_relation_review_status"))
                    == canonical_tg_semantic_status
                ),
                "tg_authoritative_provenance_fk": row["tg_pair_id"],
                "evidence_tier": clean(row.get("evidence_tier")),
                "base_evidence_grade": base_grade,
                "base_evidence_grade_order": base_grade_order,
                "source_base_evidence_grade_matches_recomputed": (
                    source_base_grade == base_grade
                ),
                "source_base_evidence_grade_order_matches_recomputed": (
                    source_base_grade_order == base_grade_order
                ),
                "evidence_grade": evidence_grade,
                "evidence_grade_order": evidence_grade_order,
                "source_reviewed_evidence_grade_matches_recomputed": (
                    not has_review_overlay or source_reviewed_grade == evidence_grade
                ),
                "source_reviewed_evidence_grade_order_matches_recomputed": (
                    not has_review_overlay
                    or source_reviewed_grade_order == evidence_grade_order
                ),
                "grade_namespace": grade_namespace,
                "grade_basis": grade_basis,
                "minimum_pair_paper_count": canonical_minimum_paper_count,
                "minimum_pair_sentence_count": canonical_minimum_sentence_count,
                "source_minimum_pair_paper_count_matches_recomputed": safe_int(
                    row.get("minimum_pair_paper_count")
                )
                == canonical_minimum_paper_count,
                "source_minimum_pair_sentence_count_matches_recomputed": safe_int(
                    row.get("minimum_pair_sentence_count")
                )
                == canonical_minimum_sentence_count,
                "source_closure_group_id": clean(row.get("closure_group_id")),
                "source_cross_endpoint_pair_key": clean(
                    row.get("cross_endpoint_pair_key")
                ),
                "cross_endpoint_status_in_iTE": derived_ite_status,
                "cross_endpoint_status_in_TG": derived_tg_status,
                "source_cross_endpoint_status_in_iTE": source_ite_status,
                "source_cross_endpoint_status_in_TG": source_tg_status,
                "source_cross_endpoint_status_in_iTE_matches_recomputed": (
                    source_ite_status == derived_ite_status
                ),
                "source_cross_endpoint_status_in_TG_matches_recomputed": (
                    source_tg_status == derived_tg_status
                ),
                "human_relation_review_status": clean(
                    row.get("human_relation_review_status", "pending")
                )
                or "pending",
                "cross_paper_compatibility_status": clean(
                    row.get("cross_paper_compatibility_status", "untested")
                )
                or "untested",
                "cross_endpoint_evaluation_status": clean(
                    row.get("cross_endpoint_evaluation_status", "not_tested")
                )
                or "not_tested",
                "novelty_status": clean(row.get("novelty_status", "not_assessed"))
                or "not_assessed",
                "novelty_claim_allowed": as_bool(row.get("novelty_claim_allowed", False)),
                "candidate_interpretation": clean(row.get("candidate_interpretation")),
                "shared_node_release_status": clean(
                    shared.get("release_status", "not_in_pair_path_inventory")
                ),
                "cross_endpoint_edge_state": "not_created",
                "review_selected": bool(queue),
                "review_queue_order": safe_int(queue.get("review_queue_order")),
                "review_selection_reason": clean(queue.get("review_selection_reason")),
                "selection_policy_id": clean(queue.get("selection_policy_id")),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["evidence_grade_order", "candidate_id"]
    ).reset_index(drop=True)


def cross_endpoint_bucket(ite_status: str, tg_status: str) -> str:
    ite_status = clean(ite_status)
    tg_status = clean(tg_status)
    if (
        ite_status not in ALLOWED_CROSS_ENDPOINT_STATUS["iTE"]
        or tg_status not in ALLOWED_CROSS_ENDPOINT_STATUS["TG"]
    ):
        return "unknown_or_not_evaluated_quarantine"
    ite_observed = ite_status == "already_observed_in_iTE"
    tg_observed = tg_status == "already_observed_in_TG"
    if not ite_observed and not tg_observed:
        return "both_not_observed_in_frozen_direct_corpora"
    if ite_observed and not tg_observed:
        return "observed_in_iTE_only"
    if not ite_observed and tg_observed:
        return "observed_in_TG_only"
    return "observed_in_both_direct_corpora"


def build_cross_endpoint_candidates(
    endpoint_pass_paths: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    shared_hubness = (
        endpoint_pass_paths.groupby("shared_global_concept_id").size().to_dict()
    )
    rows = []
    group_columns = ["ite_other_global_concept_id", "tg_other_global_concept_id"]
    for (ite_id, tg_id), group in endpoint_pass_paths.groupby(group_columns, sort=True):
        if ite_id == tg_id:
            raise ValueError(f"self-loop cross endpoint candidate: {ite_id}")
        mapping_id = stable_id("CM", ite_id, tg_id)
        low, high = sorted([ite_id, tg_id])
        unordered_id = stable_id("UG", low, high)
        grade_orders = pd.to_numeric(group["evidence_grade_order"], errors="coerce")
        best_order = int(grade_orders.min())
        worst_order = int(grade_orders.max())
        best_group = group[grade_orders.eq(best_order)].copy()
        best_group["_hubness"] = best_group["shared_global_concept_id"].map(
            shared_hubness
        )
        best_group = best_group.sort_values(
            [
                "minimum_pair_paper_count",
                "minimum_pair_sentence_count",
                "shared_global_concept_id",
                "candidate_id",
            ],
            ascending=[False, False, True, True],
        )
        representative = best_group.iloc[0]
        grade_by_order = (
            group[["evidence_grade_order", "evidence_grade"]]
            .drop_duplicates()
            .sort_values(["evidence_grade_order", "evidence_grade"])
            .set_index("evidence_grade_order")["evidence_grade"]
            .to_dict()
        )
        grade_counts = Counter(grade_class(value) for value in group["evidence_grade"])
        ite_status = deterministic_mode(group["cross_endpoint_status_in_iTE"])
        tg_status = deterministic_mode(group["cross_endpoint_status_in_TG"])
        rows.append(
            {
                "mapping_candidate_id": mapping_id,
                "candidate_edge_id": mapping_id,
                "edge_role": "iTE_role_endpoint_to_TG_role_endpoint_noncausal",
                "ite_endpoint_global_concept_id": ite_id,
                "ite_endpoint_label": deterministic_mode(group["ite_other_label"]),
                "ite_endpoint_category": deterministic_mode(group["ite_other_category"]),
                "ite_endpoint_layer_node_id": deterministic_mode(
                    group["ite_other_layer_node_id"]
                ),
                "tg_endpoint_global_concept_id": tg_id,
                "tg_endpoint_label": deterministic_mode(group["tg_other_label"]),
                "tg_endpoint_category": deterministic_mode(group["tg_other_category"]),
                "tg_endpoint_layer_node_id": deterministic_mode(
                    group["tg_other_layer_node_id"]
                ),
                "unordered_group_id": unordered_id,
                "path_count": len(group),
                "distinct_shared_route_count": group[
                    "shared_global_concept_id"
                ].nunique(),
                "candidate_path_ids": join_unique(group["candidate_id"]),
                "shared_global_concept_ids": join_unique(
                    group["shared_global_concept_id"]
                ),
                "shared_labels": join_unique(group["shared_label"]),
                "ite_pair_ids": join_unique(group["ite_pair_id"]),
                "tg_pair_ids": join_unique(group["tg_pair_id"]),
                "source_closure_group_ids": join_unique(
                    group["source_closure_group_id"]
                ),
                "best_evidence_grade": grade_by_order[best_order],
                "best_evidence_grade_order": best_order,
                "worst_evidence_grade": grade_by_order[worst_order],
                "worst_evidence_grade_order": worst_order,
                "best_grade_path_count": len(best_group),
                "best_grade_distinct_shared_route_count": best_group[
                    "shared_global_concept_id"
                ].nunique(),
                "best_path_ids": join_unique(best_group["candidate_id"]),
                "R2_path_count": grade_counts["R2"],
                "R1_path_count": grade_counts["R1"],
                "R0_path_count": grade_counts["R0"],
                "unclassified_path_count": grade_counts["UNCLASSIFIED"],
                "representative_best_path_id": representative["candidate_id"],
                "representative_best_shared_global_concept_id": representative[
                    "shared_global_concept_id"
                ],
                "representative_best_shared_label": representative["shared_label"],
                "representative_best_minimum_pair_paper_count": safe_int(
                    representative["minimum_pair_paper_count"]
                ),
                "representative_best_minimum_pair_sentence_count": safe_int(
                    representative["minimum_pair_sentence_count"]
                ),
                "representative_best_shared_route_hubness": safe_int(
                    representative["_hubness"]
                ),
                "ite_semantic_status_signature": join_unique(
                    group["ite_semantic_relation_review_status"]
                ),
                "tg_semantic_status_signature": join_unique(
                    group["tg_semantic_relation_review_status"]
                ),
                "cross_endpoint_status_in_iTE": join_unique(
                    group["cross_endpoint_status_in_iTE"]
                ),
                "cross_endpoint_status_in_TG": join_unique(
                    group["cross_endpoint_status_in_TG"]
                ),
                "discovery_bucket": cross_endpoint_bucket(ite_status, tg_status),
                "human_confirmation_status": join_unique(
                    group["human_relation_review_status"]
                ),
                "cross_paper_compatibility_status": join_unique(
                    group["cross_paper_compatibility_status"]
                ),
                "cross_endpoint_evaluation_status": join_unique(
                    group["cross_endpoint_evaluation_status"]
                ),
                "novelty_status": join_unique(group["novelty_status"]),
                "novelty_claim_allowed_signature": join_unique(
                    group["novelty_claim_allowed"]
                ),
                "novelty_claim_allowed": bool(
                    group["novelty_claim_allowed"].map(as_bool).all()
                ),
                "scientific_claim_status": join_unique(
                    group["scientific_claim_status"]
                ),
                "candidate_edge_status": "candidate_not_observed",
                "graph_eligible": False,
            }
        )

    oriented = pd.DataFrame(rows)
    group_to_ids = oriented.groupby("unordered_group_id")["mapping_candidate_id"].apply(
        list
    )
    orientation_count = group_to_ids.map(len).to_dict()
    mirror_map: dict[str, str] = {}
    for ids in group_to_ids:
        if len(ids) == 2:
            mirror_map[ids[0]] = ids[1]
            mirror_map[ids[1]] = ids[0]
    oriented["orientation_count"] = oriented["unordered_group_id"].map(
        orientation_count
    )
    oriented["is_mirrored"] = oriented["mapping_candidate_id"].isin(mirror_map)
    oriented["mirror_mapping_candidate_id"] = oriented["mapping_candidate_id"].map(
        mirror_map
    ).fillna("")

    bucket_order = {
        "both_not_observed_in_frozen_direct_corpora": 1,
        "observed_in_iTE_only": 2,
        "observed_in_TG_only": 3,
        "observed_in_both_direct_corpora": 4,
        "unknown_or_not_evaluated_quarantine": 99,
    }
    oriented["discovery_bucket_order"] = oriented["discovery_bucket"].map(bucket_order)
    evidence_sort = [
        "best_evidence_grade_order",
        "best_grade_path_count",
        "best_grade_distinct_shared_route_count",
        "representative_best_minimum_pair_paper_count",
        "representative_best_minimum_pair_sentence_count",
        "mapping_candidate_id",
    ]
    evidence_ascending = [True, False, False, False, False, True]
    oriented = oriented.sort_values(
        evidence_sort,
        ascending=evidence_ascending,
    ).reset_index(drop=True)
    oriented["identity_blind_evidence_audit_order"] = range(1, len(oriented) + 1)
    discovery_view = oriented.sort_values(
        [
            "discovery_bucket_order",
            "best_evidence_grade_order",
            "best_grade_path_count",
            "best_grade_distinct_shared_route_count",
            "representative_best_minimum_pair_paper_count",
            "representative_best_minimum_pair_sentence_count",
            "representative_best_shared_route_hubness",
            "path_count",
            "mapping_candidate_id",
        ],
        ascending=[True, True, False, False, False, False, True, False, True],
    ).copy()
    discovery_view["discovery_queue_order_within_bucket"] = (
        discovery_view.groupby("discovery_bucket").cumcount() + 1
    )
    discovery_order = discovery_view.set_index("mapping_candidate_id")[
        "discovery_queue_order_within_bucket"
    ].to_dict()
    oriented["discovery_queue_order_within_bucket"] = oriented[
        "mapping_candidate_id"
    ].map(discovery_order)
    oriented["evidence_order_policy_id"] = (
        "identity_blind_real_path_grade_then_support_v2_no_status_bucket_no_weighted_score"
    )
    oriented["discovery_queue_policy_id"] = (
        "optional_within_status_bucket_evidence_then_lower_shared_hubness_v1"
    )

    unordered_rows = []
    path_lookup = endpoint_pass_paths.set_index("candidate_id")
    for unordered_id, group in oriented.groupby("unordered_group_id", sort=True):
        path_ids = sorted_unique(
            candidate_id
            for values in group["candidate_path_ids"]
            for candidate_id in clean(values).split("; ")
            if candidate_id
        )
        paths = path_lookup.loc[path_ids]
        low, high = sorted(
            {
                *group["ite_endpoint_global_concept_id"],
                *group["tg_endpoint_global_concept_id"],
            }
        )
        label_lookup = {}
        for row in group.itertuples(index=False):
            label_lookup[row.ite_endpoint_global_concept_id] = row.ite_endpoint_label
            label_lookup[row.tg_endpoint_global_concept_id] = row.tg_endpoint_label
        best_order = int(group["best_evidence_grade_order"].min())
        worst_order = int(group["worst_evidence_grade_order"].max())
        best_paths = paths[paths["evidence_grade_order"].eq(best_order)]
        unordered_rows.append(
            {
                "unordered_group_id": unordered_id,
                "endpoint_a_global_concept_id": low,
                "endpoint_a_label": label_lookup[low],
                "endpoint_b_global_concept_id": high,
                "endpoint_b_label": label_lookup[high],
                "orientation_count": len(group),
                "is_mirrored": len(group) == 2,
                "oriented_mapping_candidate_ids": join_unique(
                    group["mapping_candidate_id"]
                ),
                "unordered_path_count": len(paths),
                "candidate_path_ids": "; ".join(path_ids),
                "distinct_shared_route_count": paths[
                    "shared_global_concept_id"
                ].nunique(),
                "shared_global_concept_ids": join_unique(
                    paths["shared_global_concept_id"]
                ),
                "best_evidence_grade": deterministic_mode(
                    best_paths["evidence_grade"]
                ),
                "best_evidence_grade_order": best_order,
                "worst_evidence_grade": deterministic_mode(
                    paths.loc[
                        paths["evidence_grade_order"].eq(worst_order), "evidence_grade"
                    ]
                ),
                "worst_evidence_grade_order": worst_order,
                "R2_path_count": int(
                    paths["evidence_grade"].str.startswith("R2").sum()
                ),
                "R1_path_count": int(
                    paths["evidence_grade"].str.startswith("R1").sum()
                ),
                "R0_path_count": int(
                    paths["evidence_grade"].str.startswith("R0").sum()
                ),
                "unclassified_path_count": int(
                    paths["evidence_grade"].map(grade_class).eq("UNCLASSIFIED").sum()
                ),
                "candidate_group_status": "candidate_not_observed",
                "graph_eligible": False,
            }
        )
    unordered = pd.DataFrame(unordered_rows).sort_values(
        ["best_evidence_grade_order", "unordered_group_id"]
    ).reset_index(drop=True)
    return oriented, unordered


def add_node(graph: nx.Graph, record: dict[str, Any]) -> None:
    graph.add_node(
        record["layer_node_id"],
        label=graphml_scalar(record["normalized_label"]),
        analysis_layer=graphml_scalar(record["analysis_layer"]),
        global_concept_id=graphml_scalar(record["global_concept_id"]),
        lexical_category=graphml_scalar(record["lexical_category"]),
        layer_document_frequency=graphml_scalar(record["layer_document_frequency"]),
        pair_degree=graphml_scalar(record["pair_degree"]),
        node_fact_status=graphml_scalar(record["node_fact_status"]),
    )


def write_graphml(graph: nx.Graph, path: Path) -> None:
    nx.write_graphml(graph, path, edge_id_from_attribute="edge_id")


def build_observed_graphmls(
    output_dir: Path,
    nodes: pd.DataFrame,
    pair_edges: pd.DataFrame,
    alignments: pd.DataFrame,
    relation_audit: pd.DataFrame,
    observed_relations: pd.DataFrame,
) -> dict[str, Path]:
    node_records = nodes.set_index("layer_node_id").to_dict("index")

    def pair_graph(layer: str) -> nx.MultiGraph:
        graph = nx.MultiGraph(
            graph_kind="observed_same_sentence_pair_topology",
            causal_interpretation_allowed=False,
        )
        layer_pairs = pair_edges[pair_edges["analysis_layer"].eq(layer)]
        endpoint_ids = set(layer_pairs["left_layer_node_id"]) | set(
            layer_pairs["right_layer_node_id"]
        )
        for node_id in sorted(endpoint_ids):
            add_node(graph, {"layer_node_id": node_id, **node_records[node_id]})
        for edge in layer_pairs.to_dict("records"):
            graph.add_edge(
                edge["left_layer_node_id"],
                edge["right_layer_node_id"],
                key=edge["pair_id"],
                edge_id=edge["pair_id"],
                edge_type="same_sentence_pair",
                analysis_layer=layer,
                paper_count=int(edge["paper_count"]),
                sentence_count=int(edge["sentence_count"]),
                pair_evidence_status=edge["pair_evidence_status"],
                graph_edge_status="observed_pair_topology_noncausal",
                causal_claim=False,
            )
        return graph

    paths = {
        "ite_observed_pairs": output_dir / "ite_observed_pairs.graphml",
        "tg_observed_pairs": output_dir / "tg_observed_pairs.graphml",
        "exact_alignment_pair_endpoints": output_dir
        / "exact_alignment_pair_endpoints.graphml",
        "two_layer_pair_alignment": output_dir / "two_layer_pair_alignment.graphml",
        "direct_relation_candidate_audit": output_dir
        / "direct_relation_candidate_audit.graphml",
        "observed_relations": output_dir / "observed_relations.graphml",
    }
    ite_graph = pair_graph("iTE")
    tg_graph = pair_graph("TG")
    write_graphml(ite_graph, paths["ite_observed_pairs"])
    write_graphml(tg_graph, paths["tg_observed_pairs"])

    active_alignments = alignments[alignments["both_pair_endpoints"]]
    alignment_graph = nx.MultiGraph(
        graph_kind="exact_identity_alignment_pair_endpoints",
        scientific_relation=False,
    )
    for edge in active_alignments.to_dict("records"):
        for node_id in [edge["ite_layer_node_id"], edge["tg_layer_node_id"]]:
            if node_id not in alignment_graph:
                add_node(
                    alignment_graph,
                    {"layer_node_id": node_id, **node_records[node_id]},
                )
        alignment_graph.add_edge(
            edge["ite_layer_node_id"],
            edge["tg_layer_node_id"],
            key=edge["alignment_id"],
            edge_id=edge["alignment_id"],
            edge_type="exact_node_alignment",
            alignment_method="exact_global_concept_id",
            scientific_relation=False,
        )
    write_graphml(alignment_graph, paths["exact_alignment_pair_endpoints"])

    combined = nx.compose(ite_graph, tg_graph)
    for node_id, attrs in alignment_graph.nodes(data=True):
        if node_id not in combined:
            combined.add_node(node_id, **attrs)
    for left, right, key, attrs in alignment_graph.edges(keys=True, data=True):
        combined.add_edge(left, right, key=key, **attrs)
    combined.graph.update(
        graph_kind="two_layer_pair_topology_plus_exact_identity",
        candidate_closure_edges_included=False,
        causal_interpretation_allowed=False,
    )
    write_graphml(combined, paths["two_layer_pair_alignment"])

    audit_graph = nx.MultiDiGraph(
        graph_kind="direct_relation_candidate_audit",
        production_graph=False,
    )
    audit_nodes = set(relation_audit["source_node_id"]) | set(
        relation_audit["target_node_id"]
    )
    for node_id in sorted(audit_nodes):
        add_node(audit_graph, {"layer_node_id": node_id, **node_records[node_id]})
    for edge in relation_audit.to_dict("records"):
        audit_graph.add_edge(
            edge["source_node_id"],
            edge["target_node_id"],
            key=edge["relation_id"],
            edge_id=edge["relation_id"],
            edge_type="direct_relation_candidate_audit",
            analysis_layer=edge["analysis_layer"],
            predicate=edge["predicate_normalized"],
            strict_syntax_eligible=bool(edge["strict_syntax_eligible"]),
            semantic_verdict=edge["semantic_verdict"],
            human_confirmation_status=edge["human_confirmation_status"],
            production_graph_eligible=bool(edge["production_graph_eligible"]),
            graph_edge_status=edge["graph_edge_status"],
        )
    write_graphml(audit_graph, paths["direct_relation_candidate_audit"])

    observed_graph = nx.MultiDiGraph(
        graph_kind="human_confirmed_observed_relations",
        production_graph=True,
    )
    for edge in observed_relations.to_dict("records"):
        for node_id in [edge["source_node_id"], edge["target_node_id"]]:
            if node_id not in observed_graph:
                add_node(
                    observed_graph,
                    {"layer_node_id": node_id, **node_records[node_id]},
                )
        observed_graph.add_edge(
            edge["source_node_id"],
            edge["target_node_id"],
            key=edge["relation_id"],
            edge_id=edge["relation_id"],
            edge_type="observed_relation",
            predicate=edge["predicate_normalized"],
            production_graph_eligible=True,
        )
    write_graphml(observed_graph, paths["observed_relations"])
    return paths


def canonical_edge_signature(
    source: object, target: object, edge_type: object, directed: bool
) -> tuple[str, str, str]:
    left, right = clean(source), clean(target)
    if not directed:
        left, right = sorted([left, right])
    return left, right, clean(edge_type)


def graphml_snapshot(path: Path) -> dict[str, object]:
    graph = nx.read_graphml(path, force_multigraph=True)
    signatures: dict[str, tuple[str, str, str]] = {}
    duplicate_edge_ids = 0
    xml_key_matches_data_id = True
    for source, target, key, attrs in graph.edges(keys=True, data=True):
        edge_id = clean(attrs.get("edge_id", key))
        if edge_id in signatures:
            duplicate_edge_ids += 1
        signatures[edge_id] = canonical_edge_signature(
            source, target, attrs.get("edge_type"), graph.is_directed()
        )
        xml_key_matches_data_id &= clean(key) == edge_id
    xml_root = ET.parse(path).getroot()
    xml_edge_ids = {
        clean(element.attrib.get("id"))
        for element in xml_root.findall("{http://graphml.graphdrawing.org/xmlns}graph/{http://graphml.graphdrawing.org/xmlns}edge")
    }
    return {
        "graph": graph,
        "node_ids": set(graph.nodes),
        "edge_ids": set(signatures),
        "edge_signatures": signatures,
        "edge_count": graph.number_of_edges(),
        "duplicate_edge_ids": duplicate_edge_ids,
        "xml_edge_ids": xml_edge_ids,
        "xml_key_matches_data_id": xml_key_matches_data_id,
    }


def path_fk_failures(
    paths: pd.DataFrame,
    pair_edges: pd.DataFrame,
    alignments: pd.DataFrame,
) -> dict[str, int]:
    pair_lookup = pair_edges.set_index("pair_id").to_dict("index")
    alignment_lookup = alignments.set_index("alignment_id").to_dict("index")
    failures = Counter()
    for row in paths.itertuples(index=False):
        ite_pair = pair_lookup.get(row.ite_pair_id)
        tg_pair = pair_lookup.get(row.tg_pair_id)
        alignment = alignment_lookup.get(row.alignment_id)
        if not ite_pair or ite_pair["analysis_layer"] != "iTE":
            failures["ite_pair_fk"] += 1
        if not tg_pair or tg_pair["analysis_layer"] != "TG":
            failures["tg_pair_fk"] += 1
        if not alignment:
            failures["alignment_fk"] += 1
            continue
        if alignment["global_concept_id"] != row.shared_global_concept_id:
            failures["alignment_shared_id"] += 1
        if (
            alignment["ite_layer_node_id"] != row.ite_shared_layer_node_id
            or alignment["tg_layer_node_id"] != row.tg_shared_layer_node_id
        ):
            failures["alignment_layer_node_ids"] += 1
        if ite_pair and row.shared_global_concept_id not in {
            ite_pair["left_global_concept_id"],
            ite_pair["right_global_concept_id"],
        }:
            failures["ite_shared_endpoint"] += 1
        if tg_pair and row.shared_global_concept_id not in {
            tg_pair["left_global_concept_id"],
            tg_pair["right_global_concept_id"],
        }:
            failures["tg_shared_endpoint"] += 1
        if ite_pair and row.ite_other_global_concept_id not in {
            ite_pair["left_global_concept_id"],
            ite_pair["right_global_concept_id"],
        }:
            failures["ite_other_endpoint"] += 1
        if ite_pair and row.ite_other_layer_node_id not in {
            ite_pair["left_layer_node_id"],
            ite_pair["right_layer_node_id"],
        }:
            failures["ite_other_layer_node"] += 1
        if tg_pair and row.tg_other_global_concept_id not in {
            tg_pair["left_global_concept_id"],
            tg_pair["right_global_concept_id"],
        }:
            failures["tg_other_endpoint"] += 1
        if tg_pair and row.tg_other_layer_node_id not in {
            tg_pair["left_layer_node_id"],
            tg_pair["right_layer_node_id"],
        }:
            failures["tg_other_layer_node"] += 1
        for field in (
            "source_shared_label_matches_registry",
            "source_shared_category_matches_registry",
            "shared_layer_labels_match",
            "shared_layer_categories_match",
            "source_ite_other_label_matches_registry",
            "source_ite_other_category_matches_registry",
            "source_tg_other_label_matches_registry",
            "source_tg_other_category_matches_registry",
            "source_cross_endpoint_status_in_iTE_matches_recomputed",
            "source_cross_endpoint_status_in_TG_matches_recomputed",
            "source_ite_pair_paper_count_matches_pair_bank",
            "source_ite_pair_sentence_count_matches_pair_bank",
            "source_tg_pair_paper_count_matches_pair_bank",
            "source_tg_pair_sentence_count_matches_pair_bank",
            "source_ite_strict_relation_ids_match_pair_bank",
            "source_tg_strict_relation_ids_match_pair_bank",
            "source_minimum_pair_paper_count_matches_recomputed",
            "source_minimum_pair_sentence_count_matches_recomputed",
            "source_ite_semantic_review_status_matches_recomputed",
            "source_tg_semantic_review_status_matches_recomputed",
            "source_base_evidence_grade_matches_recomputed",
            "source_base_evidence_grade_order_matches_recomputed",
            "source_reviewed_evidence_grade_matches_recomputed",
            "source_reviewed_evidence_grade_order_matches_recomputed",
        ):
            if not as_bool(getattr(row, field)):
                failures[field] += 1
        if row.cross_endpoint_status_in_iTE not in ALLOWED_CROSS_ENDPOINT_STATUS["iTE"]:
            failures["invalid_ite_cross_endpoint_status"] += 1
        if row.cross_endpoint_status_in_TG not in ALLOWED_CROSS_ENDPOINT_STATUS["TG"]:
            failures["invalid_tg_cross_endpoint_status"] += 1
        expected_order = expected_grade_order(row.evidence_grade, row.grade_namespace)
        if expected_order == 99:
            failures["unclassified_grade_or_namespace"] += 1
        elif safe_int(row.evidence_grade_order, 99) != expected_order:
            failures["grade_order_mismatch"] += 1
    return dict(failures)


PATH_IDENTITY_COLUMNS = [
    "shared_global_concept_id",
    "ite_pair_id",
    "tg_pair_id",
    "ite_other_global_concept_id",
    "tg_other_global_concept_id",
    "ite_shared_layer_node_id",
    "tg_shared_layer_node_id",
    "ite_other_layer_node_id",
    "tg_other_layer_node_id",
    "alignment_id",
]


def path_identity_mismatch_count(
    subset: pd.DataFrame, parent: pd.DataFrame
) -> int:
    parent_index = parent.set_index("candidate_id")
    mismatches = 0
    for row in subset.set_index("candidate_id")[PATH_IDENTITY_COLUMNS].itertuples():
        if row.Index not in parent_index.index:
            mismatches += 1
            continue
        expected = tuple(parent_index.loc[row.Index, PATH_IDENTITY_COLUMNS])
        if tuple(row[1:]) != expected:
            mismatches += 1
    return mismatches


def direct_overlap_failures(
    overlaps: pd.DataFrame, pair_edges: pd.DataFrame
) -> dict[str, int]:
    pair_lookup = pair_edges.set_index("pair_id").to_dict("index")
    failures = Counter()
    if not overlaps["overlap_id"].is_unique:
        failures["duplicate_overlap_id"] += int(overlaps["overlap_id"].duplicated().sum())
    if not overlaps["pair_id_ite"].is_unique:
        failures["duplicate_ite_pair"] += int(overlaps["pair_id_ite"].duplicated().sum())
    if not overlaps["pair_id_tg"].is_unique:
        failures["duplicate_tg_pair"] += int(overlaps["pair_id_tg"].duplicated().sum())
    for row in overlaps.itertuples(index=False):
        ite = pair_lookup.get(row.pair_id_ite)
        tg = pair_lookup.get(row.pair_id_tg)
        if not ite:
            failures["missing_ite_pair"] += 1
        if not tg:
            failures["missing_tg_pair"] += 1
        if ite and ite["analysis_layer"] != "iTE":
            failures["wrong_ite_layer"] += 1
        if tg and tg["analysis_layer"] != "TG":
            failures["wrong_tg_layer"] += 1
        if ite and tg and not (
            ite["pair_key"] == tg["pair_key"] == row.pair_key
        ):
            failures["pair_key_mismatch"] += 1
    return dict(failures)


def mirror_failures(
    oriented: pd.DataFrame, unordered: pd.DataFrame
) -> dict[str, int]:
    lookup = oriented.set_index("mapping_candidate_id").to_dict("index")
    failures = Counter()
    if not oriented["orientation_count"].isin([1, 2]).all():
        failures["invalid_orientation_count"] += int(
            (~oriented["orientation_count"].isin([1, 2])).sum()
        )
    for row in oriented.itertuples(index=False):
        mirror_id = clean(row.mirror_mapping_candidate_id)
        if row.is_mirrored:
            mirror = lookup.get(mirror_id)
            if not mirror:
                failures["missing_mirror"] += 1
                continue
            if clean(mirror["mirror_mapping_candidate_id"]) != row.mapping_candidate_id:
                failures["mirror_not_involution"] += 1
            if not (
                mirror["ite_endpoint_global_concept_id"]
                == row.tg_endpoint_global_concept_id
                and mirror["tg_endpoint_global_concept_id"]
                == row.ite_endpoint_global_concept_id
            ):
                failures["mirror_endpoints_not_reversed"] += 1
            if mirror["unordered_group_id"] != row.unordered_group_id:
                failures["mirror_unordered_group_mismatch"] += 1
        elif mirror_id:
            failures["unmirrored_row_has_pointer"] += 1
    unordered_lookup = unordered.set_index("unordered_group_id").to_dict("index")
    for group_id, group in oriented.groupby("unordered_group_id"):
        record = unordered_lookup.get(group_id)
        if not record:
            failures["missing_unordered_group"] += 1
            continue
        oriented_path_ids = {
            path_id
            for value in group["candidate_path_ids"]
            for path_id in clean(value).split("; ")
            if path_id
        }
        unordered_path_ids = {
            path_id
            for path_id in clean(record["candidate_path_ids"]).split("; ")
            if path_id
        }
        if oriented_path_ids != unordered_path_ids:
            failures["unordered_path_union_mismatch"] += 1
        if len(group) != safe_int(record["orientation_count"]):
            failures["unordered_orientation_count_mismatch"] += 1
    return dict(failures)


def aggregate_candidate_state_failures(
    oriented: pd.DataFrame, paths: pd.DataFrame
) -> dict[str, int]:
    path_lookup = paths.set_index("candidate_id")
    failures = Counter()
    aggregate_fields = {
        "human_confirmation_status": "human_relation_review_status",
        "cross_paper_compatibility_status": "cross_paper_compatibility_status",
        "cross_endpoint_evaluation_status": "cross_endpoint_evaluation_status",
        "novelty_status": "novelty_status",
        "scientific_claim_status": "scientific_claim_status",
        "novelty_claim_allowed_signature": "novelty_claim_allowed",
    }
    for row in oriented.itertuples(index=False):
        path_ids = [
            value
            for value in clean(row.candidate_path_ids).split("; ")
            if value
        ]
        group = path_lookup.loc[path_ids]
        for aggregate_field, path_field in aggregate_fields.items():
            expected = join_unique(group[path_field])
            if clean(getattr(row, aggregate_field)) != expected:
                failures[f"{aggregate_field}_mismatch"] += 1
    return dict(failures)


def build_qa(
    data: dict[str, pd.DataFrame],
    upstream_contract: dict[str, object],
    nodes: pd.DataFrame,
    pair_edges: pd.DataFrame,
    alignments: pd.DataFrame,
    relation_audit: pd.DataFrame,
    observed_relations: pd.DataFrame,
    paths_all: pd.DataFrame,
    paths_focus: pd.DataFrame,
    paths_pass: pd.DataFrame,
    paths_quarantine: pd.DataFrame,
    oriented: pd.DataFrame,
    unordered: pd.DataFrame,
    review_paths: pd.DataFrame,
    graphml_paths: dict[str, Path],
    input_hashes_before: dict[str, str],
    input_hashes_after: dict[str, str],
) -> dict[str, Any]:
    pair_endpoint_nodes = int(nodes["pair_endpoint_eligible"].sum())
    active_alignments = alignments[alignments["both_pair_endpoints"]]
    counts = {
        "concept_nodes": len(nodes),
        "pair_endpoint_nodes": pair_endpoint_nodes,
        "isolated_concept_nodes": len(nodes) - pair_endpoint_nodes,
        "pair_edges": len(pair_edges),
        "ite_pair_edges": int(pair_edges["analysis_layer"].eq("iTE").sum()),
        "tg_pair_edges": int(pair_edges["analysis_layer"].eq("TG").sum()),
        "exact_alignments_all": len(alignments),
        "exact_alignments_pair_endpoints": len(active_alignments),
        "direct_relation_audit_edges": len(relation_audit),
        "direct_strict_relation_candidates": int(
            relation_audit["strict_syntax_eligible"].sum()
        ),
        "observed_relation_edges": len(observed_relations),
        "candidate_paths_all": len(paths_all),
        "candidate_paths_focus_pre_gate": len(paths_focus),
        "candidate_paths_endpoint_pass": len(paths_pass),
        "candidate_paths_quarantine": len(paths_quarantine),
        "oriented_cross_endpoint_candidates": len(oriented),
        "unordered_cross_endpoint_groups": len(unordered),
        "mirrored_unordered_groups": int(unordered["is_mirrored"].sum()),
        "review_queue_paths": len(review_paths),
    }
    checks: dict[str, bool] = {}
    checks["frozen_v3_counts_match"] = counts == EXPECTED_V3
    checks["validated_upstream_cleanroom_contract"] = all(
        upstream_contract["checks"].values()
    )
    checks["layer_node_ids_unique"] = nodes["layer_node_id"].is_unique
    checks["layer_global_pairs_unique"] = not nodes.duplicated(
        ["analysis_layer", "global_concept_id"]
    ).any()
    checks["pair_ids_unique"] = pair_edges["pair_id"].is_unique
    checks["pair_endpoints_same_layer"] = bool(
        pair_edges.apply(
            lambda row: row["left_layer_node_id"].startswith("LN_")
            and row["right_layer_node_id"].startswith("LN_"),
            axis=1,
        ).all()
    )
    node_layer = nodes.set_index("layer_node_id")["analysis_layer"].to_dict()
    node_label = nodes.set_index("layer_node_id")["normalized_label"].to_dict()
    checks["pair_edge_layers_resolve"] = bool(
        pair_edges.apply(
            lambda row: node_layer[row["left_layer_node_id"]]
            == row["analysis_layer"]
            == node_layer[row["right_layer_node_id"]],
            axis=1,
        ).all()
    )
    checks["pair_edge_labels_match_node_registry"] = bool(
        pair_edges.apply(
            lambda row: node_label[row["left_layer_node_id"]] == row["left_label"]
            and node_label[row["right_layer_node_id"]] == row["right_label"],
            axis=1,
        ).all()
    )
    checks["every_pair_has_atomic_evidence"] = bool(
        pair_edges["atomic_evidence_record_count"].gt(0).all()
    )
    checks["unique_sentence_support_matches_pair_bank"] = bool(
        pair_edges["unique_sentence_support_count"].eq(
            pair_edges["sentence_count"]
        ).all()
    )
    checks["all_alignment_ids_unique"] = alignments["alignment_id"].is_unique
    checks["alignment_crosses_layers_only"] = bool(
        alignments.apply(
            lambda row: node_layer[row["ite_layer_node_id"]] == "iTE"
            and node_layer[row["tg_layer_node_id"]] == "TG",
            axis=1,
        ).all()
    )
    checks["alignment_exact_labels_only"] = bool(
        alignments["exact_label_match"].all()
    )
    checks["active_alignment_matches_pair_endpoint_intersection"] = set(
        active_alignments["global_concept_id"]
    ) == (
        set(
            pair_edges.loc[
                pair_edges["analysis_layer"].eq("iTE"), "left_global_concept_id"
            ]
        )
        | set(
            pair_edges.loc[
                pair_edges["analysis_layer"].eq("iTE"), "right_global_concept_id"
            ]
        )
    ) & (
        set(
            pair_edges.loc[
                pair_edges["analysis_layer"].eq("TG"), "left_global_concept_id"
            ]
        )
        | set(
            pair_edges.loc[
                pair_edges["analysis_layer"].eq("TG"), "right_global_concept_id"
            ]
        )
    )
    checks["relation_audit_ids_unique"] = relation_audit["relation_id"].is_unique
    checks["relation_audit_endpoints_same_layer"] = bool(
        relation_audit.apply(
            lambda row: node_layer[row["source_node_id"]]
            == row["analysis_layer"]
            == node_layer[row["target_node_id"]],
            axis=1,
        ).all()
    )
    checks["relation_audit_labels_match_node_registry"] = bool(
        relation_audit.apply(
            lambda row: node_label[row["source_node_id"]] == row["source_label"]
            and node_label[row["target_node_id"]] == row["target_label"],
            axis=1,
        ).all()
    )
    adjud_by_relation = data["adjudication"].set_index("relation_id").to_dict(
        "index"
    )
    expected_production_ids: set[str] = set()
    expected_production_by_pair: defaultdict[tuple[str, str], set[str]] = defaultdict(
        set
    )
    expected_production_incidence: Counter[tuple[str, str]] = Counter()
    for raw_relation in data["relations"].loc[
        data["relations"]["analysis_layer"].isin(DIRECT_LAYERS)
    ].to_dict("records"):
        review = adjud_by_relation.get(raw_relation["relation_id"], {})
        if not effective_production_eligible(raw_relation, review):
            continue
        relation_id = raw_relation["relation_id"]
        expected_production_ids.add(relation_id)
        pair_key = "::".join(
            sorted(
                [
                    raw_relation["source_global_concept_id"],
                    raw_relation["target_global_concept_id"],
                ]
            )
        )
        expected_production_by_pair[(raw_relation["analysis_layer"], pair_key)].add(
            relation_id
        )
        for global_id in {
            raw_relation["source_global_concept_id"],
            raw_relation["target_global_concept_id"],
        }:
            expected_production_incidence[
                (raw_relation["analysis_layer"], global_id)
            ] += 1
    audit_production_ids = set(
        relation_audit.loc[
            relation_audit["production_graph_eligible"], "relation_id"
        ]
    )
    observed_production_ids = set(observed_relations["relation_id"])
    checks["relation_and_observed_sets_match_independent_production_gate"] = (
        audit_production_ids
        == observed_production_ids
        == expected_production_ids
    )
    pair_production_exact = True
    for pair in pair_edges.itertuples(index=False):
        expected_ids = expected_production_by_pair.get(
            (pair.analysis_layer, pair.pair_key), set()
        )
        actual_ids = {
            value
            for value in clean(pair.production_relation_ids).split("; ")
            if value
        }
        pair_production_exact &= actual_ids == expected_ids
    checks["pair_production_relation_ids_match_independent_gate"] = (
        pair_production_exact
    )
    checks["node_production_incidence_matches_independent_gate"] = bool(
        nodes.apply(
            lambda row: safe_int(row["production_relation_incident_count"])
            == expected_production_incidence[
                (row["analysis_layer"], row["global_concept_id"])
            ],
            axis=1,
        ).all()
    )
    path_tables = {
        "all": paths_all,
        "focus": paths_focus,
        "pass": paths_pass,
        "quarantine": paths_quarantine,
    }
    path_fk_details = {
        name: path_fk_failures(frame, pair_edges, alignments)
        for name, frame in path_tables.items()
    }
    checks["all_path_tables_have_unique_candidate_ids"] = all(
        frame["candidate_id"].is_unique for frame in path_tables.values()
    )
    checks["all_path_table_fks_labels_categories_and_statuses_resolve"] = not any(
        path_fk_details.values()
    )
    checks["all_frozen_candidate_paths_remain_retrieval_only_and_unevaluated"] = all(
        bool(
            frame["scientific_claim_status"].eq("retrieval_candidate_only").all()
            and frame["cross_paper_compatibility_status"].eq("untested").all()
            and frame["cross_endpoint_evaluation_status"].eq("not_tested").all()
            and frame["novelty_status"].eq("not_assessed").all()
            and (~frame["novelty_claim_allowed"].map(as_bool)).all()
            and (~frame["graph_eligible"].map(as_bool)).all()
        )
        for frame in path_tables.values()
    )
    focus_ids = set(paths_focus["candidate_id"])
    pass_ids = set(paths_pass["candidate_id"])
    quarantine_ids = set(paths_quarantine["candidate_id"])
    checks["focus_pass_quarantine_strict_partition"] = (
        pass_ids.isdisjoint(quarantine_ids)
        and pass_ids | quarantine_ids == focus_ids
        and len(paths_pass) + len(paths_quarantine) == len(paths_focus)
    )
    checks["focus_paths_subset_of_all_paths"] = focus_ids.issubset(
        set(paths_all["candidate_id"])
    )
    checks["focus_path_identities_match_all_table"] = (
        path_identity_mismatch_count(paths_focus, paths_all) == 0
    )
    checks["pass_path_identities_match_focus_table"] = (
        path_identity_mismatch_count(paths_pass, paths_focus) == 0
    )
    checks["quarantine_path_identities_match_focus_table"] = (
        path_identity_mismatch_count(paths_quarantine, paths_focus) == 0
    )
    checks["review_queue_subset_of_endpoint_pass"] = set(
        review_paths["candidate_id"]
    ).issubset(pass_ids)
    checks["review_queue_output_ids_exactly_match_input_queue"] = set(
        review_paths["candidate_id"]
    ) == set(data["review_queue"]["candidate_id"])
    checks["candidate_paths_are_not_graph_edges"] = bool(
        paths_all["cross_endpoint_edge_state"].eq("not_created").all()
        and (~paths_all["graph_eligible"]).all()
    )
    checks["oriented_candidate_ids_unique"] = oriented[
        "mapping_candidate_id"
    ].is_unique
    checks["oriented_path_counts_reconstruct_paths"] = int(
        oriented["path_count"].sum()
    ) == len(paths_pass)
    checks["unordered_path_counts_reconstruct_paths"] = int(
        unordered["unordered_path_count"].sum()
    ) == len(paths_pass)
    checks["candidate_grade_counts_reconstruct_paths"] = bool(
        oriented[
            [
                "R2_path_count",
                "R1_path_count",
                "R0_path_count",
                "unclassified_path_count",
            ]
        ]
        .sum(axis=1)
        .eq(oriented["path_count"])
        .all()
    )
    checks["all_review_grades_are_explicitly_classified"] = bool(
        oriented["unclassified_path_count"].eq(0).all()
        and unordered["unclassified_path_count"].eq(0).all()
    )
    checks["all_cross_endpoint_status_buckets_are_known"] = bool(
        oriented["discovery_bucket"]
        .ne("unknown_or_not_evaluated_quarantine")
        .all()
    )
    checks["no_oriented_candidate_self_loops"] = bool(
        oriented["ite_endpoint_global_concept_id"].ne(
            oriented["tg_endpoint_global_concept_id"]
        ).all()
    )
    checks["mirror_flags_match_orientation_count"] = bool(
        oriented["is_mirrored"].eq(oriented["orientation_count"].eq(2)).all()
        and unordered["is_mirrored"].eq(unordered["orientation_count"].eq(2)).all()
    )
    mirror_failure_details = mirror_failures(oriented, unordered)
    checks["mirror_pointers_endpoints_and_path_unions_are_exact"] = not bool(
        mirror_failure_details
    )
    overlap_failure_details = direct_overlap_failures(
        data["direct_overlaps"], pair_edges
    )
    checks["direct_pair_overlaps_are_one_to_one_cross_layer_exact_pairs"] = not bool(
        overlap_failure_details
    )
    checks["direct_pair_overlap_inventory_is_complete"] = set(
        data["direct_overlaps"]["pair_key"]
    ) == (
        set(
            pair_edges.loc[pair_edges["analysis_layer"].eq("iTE"), "pair_key"]
        )
        & set(
            pair_edges.loc[pair_edges["analysis_layer"].eq("TG"), "pair_key"]
        )
    )
    aggregate_state_failure_details = aggregate_candidate_state_failures(
        oriented, paths_pass
    )
    checks["oriented_candidate_states_exactly_aggregate_source_paths"] = not bool(
        aggregate_state_failure_details
    )
    checks["all_cross_endpoint_aggregates_remain_candidates"] = bool(
        oriented["candidate_edge_status"].eq("candidate_not_observed").all()
        and (~oriented["graph_eligible"]).all()
        and (~oriented["novelty_claim_allowed"]).all()
    )
    checks["input_files_unchanged"] = input_hashes_before == input_hashes_after

    def pair_signatures(frame: pd.DataFrame) -> dict[str, tuple[str, str, str]]:
        return {
            row.pair_id: canonical_edge_signature(
                row.left_layer_node_id,
                row.right_layer_node_id,
                "same_sentence_pair",
                False,
            )
            for row in frame.itertuples(index=False)
        }

    def alignment_signatures(frame: pd.DataFrame) -> dict[str, tuple[str, str, str]]:
        return {
            row.alignment_id: canonical_edge_signature(
                row.ite_layer_node_id,
                row.tg_layer_node_id,
                "exact_node_alignment",
                False,
            )
            for row in frame.itertuples(index=False)
        }

    def relation_signatures(
        frame: pd.DataFrame, edge_type: str
    ) -> dict[str, tuple[str, str, str]]:
        return {
            row.relation_id: canonical_edge_signature(
                row.source_node_id, row.target_node_id, edge_type, True
            )
            for row in frame.itertuples(index=False)
        }

    ite_pairs = pair_edges[pair_edges["analysis_layer"].eq("iTE")]
    tg_pairs = pair_edges[pair_edges["analysis_layer"].eq("TG")]
    ite_pair_signatures = pair_signatures(ite_pairs)
    tg_pair_signatures = pair_signatures(tg_pairs)
    active_alignment_signatures = alignment_signatures(active_alignments)
    graph_roundtrip = {}
    expected_graphs = {
        "ite_observed_pairs": {
            "nodes": set(ite_pairs["left_layer_node_id"])
            | set(ite_pairs["right_layer_node_id"]),
            "signatures": ite_pair_signatures,
            "directed": False,
        },
        "tg_observed_pairs": {
            "nodes": set(tg_pairs["left_layer_node_id"])
            | set(tg_pairs["right_layer_node_id"]),
            "signatures": tg_pair_signatures,
            "directed": False,
        },
        "exact_alignment_pair_endpoints": {
            "nodes": set(active_alignments["ite_layer_node_id"])
            | set(active_alignments["tg_layer_node_id"]),
            "signatures": active_alignment_signatures,
            "directed": False,
        },
        "two_layer_pair_alignment": {
            "nodes": set(nodes.loc[nodes["pair_endpoint_eligible"], "layer_node_id"]),
            "signatures": {
                **ite_pair_signatures,
                **tg_pair_signatures,
                **active_alignment_signatures,
            },
            "directed": False,
        },
        "direct_relation_candidate_audit": {
            "nodes": set(relation_audit["source_node_id"])
            | set(relation_audit["target_node_id"]),
            "signatures": relation_signatures(
                relation_audit, "direct_relation_candidate_audit"
            ),
            "directed": True,
        },
        "observed_relations": {
            "nodes": set(observed_relations["source_node_id"])
            | set(observed_relations["target_node_id"]),
            "signatures": relation_signatures(
                observed_relations, "observed_relation"
            ),
            "directed": True,
        },
    }
    for name, path in graphml_paths.items():
        snapshot = graphml_snapshot(path)
        expected = expected_graphs[name]
        observed_nodes = snapshot["node_ids"]
        observed_signatures = snapshot["edge_signatures"]
        expected_nodes = expected["nodes"]
        expected_signatures = expected["signatures"]
        roundtrip_exact = (
            observed_nodes == expected_nodes
            and observed_signatures == expected_signatures
            and snapshot["edge_count"] == len(expected_signatures)
            and snapshot["duplicate_edge_ids"] == 0
            and snapshot["xml_edge_ids"] == set(expected_signatures)
            and snapshot["xml_key_matches_data_id"]
            and snapshot["graph"].is_directed() == expected["directed"]
        )
        graph_roundtrip[name] = {
            "node_count": len(observed_nodes),
            "edge_count": snapshot["edge_count"],
            "node_ids_exact": observed_nodes == expected_nodes,
            "edge_ids_exact": set(observed_signatures) == set(expected_signatures),
            "edge_endpoints_and_types_exact": observed_signatures
            == expected_signatures,
            "xml_edge_ids_exact": snapshot["xml_edge_ids"]
            == set(expected_signatures),
            "duplicate_edge_ids": snapshot["duplicate_edge_ids"],
            "directed": snapshot["graph"].is_directed(),
            "directedness_exact": snapshot["graph"].is_directed()
            == expected["directed"],
        }
        checks[f"graphml_{name}_roundtrip_exact"] = roundtrip_exact
    combined_text = graphml_paths["two_layer_pair_alignment"].read_text(
        encoding="utf-8"
    )
    forbidden_tokens = ["TC_", "closure_group_id", "cross_endpoint_pair_key"]
    checks["combined_graphml_contains_no_candidate_closure_material"] = not any(
        token in combined_text for token in forbidden_tokens
    )
    combined_graph = graphml_snapshot(
        graphml_paths["two_layer_pair_alignment"]
    )["graph"]
    cross_layer_edge_types = []
    for left, right, attrs in combined_graph.edges(data=True):
        if node_layer[left] != node_layer[right]:
            cross_layer_edge_types.append(clean(attrs.get("edge_type")))
    checks["combined_cross_layer_edges_are_exact_alignment_only"] = (
        len(cross_layer_edge_types) == len(active_alignments)
        and set(cross_layer_edge_types) == {"exact_node_alignment"}
    )

    failures = [name for name, passed in checks.items() if not passed]
    return {
        "contract": "cleanroom_evidence_graph_v1",
        "counts": counts,
        "expected_v3_counts": EXPECTED_V3,
        "checks": checks,
        "failed_checks": failures,
        "all_checks_pass": not failures,
        "upstream_contract": upstream_contract,
        "path_fk_failure_details": path_fk_details,
        "path_identity_mismatch_counts": {
            "focus_vs_all": path_identity_mismatch_count(paths_focus, paths_all),
            "pass_vs_focus": path_identity_mismatch_count(paths_pass, paths_focus),
            "quarantine_vs_focus": path_identity_mismatch_count(
                paths_quarantine, paths_focus
            ),
        },
        "direct_overlap_failure_details": overlap_failure_details,
        "mirror_failure_details": mirror_failure_details,
        "aggregate_candidate_state_failure_details": aggregate_state_failure_details,
        "independently_recomputed_production_relation_ids": sorted(
            expected_production_ids
        ),
        "graphml_roundtrip": graph_roundtrip,
        "interpretation_guards": {
            "pair_edges": "observed same-sentence co-occurrence, noncausal",
            "alignment_edges": "exact normalized identity, not a scientific relation",
            "relation_audit_edges": "directed extraction candidates, separate from observed graph",
            "candidate_paths": "retrieval paths only; no cross-endpoint edge is created",
            "oriented_mapping_direction": "iTE role to TG role only; never causal direction",
        },
    }


def write_readme(output_dir: Path, counts: dict[str, int]) -> None:
    text = f"""# cleanroom iTE–TG evidence graph

本目录只使用 `cleanroom_abstract_pair_layer` 的冻结摘要层重建，不读取旧的互补性分析、旧 GraphML、正对照身份或预写规则。

## 五层数据契约

1. `graph_nodes.csv`：{counts['concept_nodes']:,} 个 direct-layer、layer-qualified concept 节点；其中 {counts['pair_endpoint_nodes']:,} 个参与 pair，{counts['isolated_concept_nodes']:,} 个孤立 selected concept 仍保留。
2. `graph_pair_edges.csv`：{counts['pair_edges']:,} 条层内同句 pair。它们是 observed co-occurrence，不是因果边。
3. `graph_alignment_edges.csv`：{counts['exact_alignments_all']:,} 条 exact normalized identity；其中 {counts['exact_alignments_pair_endpoints']:,} 条两侧均为 pair endpoint，可进入三段路径。alignment 不是科学 relation。
4. `graph_relation_candidate_edges.csv`：{counts['direct_relation_audit_edges']:,} 条 direct-layer predicate 审计候选；`graph_observed_relation_edges.csv` 当前为 {counts['observed_relation_edges']:,} 条。
5. `graph_candidate_paths_*.csv`：每条路径只引用 iTE pair、exact alignment、TG pair 三段既有证据。cross endpoint 不被物化成 observed edge。

## 跨端点候选的三种身份

- `graph_candidate_paths_endpoint_pass.csv`：{counts['candidate_paths_endpoint_pass']:,} 条 shared-route path。
- `graph_cross_endpoint_candidate_edges.csv`：{counts['oriented_cross_endpoint_candidates']:,} 条 iTE-role → TG-role 候选；箭头仅表示角色方向，不表示因果方向。
- `graph_cross_endpoint_unordered_index.csv`：{counts['unordered_cross_endpoint_groups']:,} 个忽略角色后的 endpoint group，用于关联镜像，不用于替代角色定向主表。

所有 cross-endpoint 记录仍是 `candidate_not_observed`，compatibility 未测试，novelty 未评估。

## GraphML 白名单

- `ite_observed_pairs.graphml` 与 `tg_observed_pairs.graphml`：层内 pair topology。
- `exact_alignment_pair_endpoints.graphml`：167 条 pair-active exact identity。
- `two_layer_pair_alignment.graphml`：pair + pair-active alignment，共 2,853 nodes / 6,580 edges；不含 candidate closure。
- `direct_relation_candidate_audit.graphml`：独立 relation 审计图，不能当 production knowledge graph。
- `observed_relations.graphml`：仅允许人工确认后 production-eligible relation；当前为空。

`graph_qa.json` 必须为 `all_checks_pass: true` 才可使用这些导出。
"""
    (output_dir / "README_CN.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_filenames = {
            "paper_concepts.csv",
            "ite_pair_bank.csv",
            "tg_pair_bank.csv",
            "pair_support_evidence.csv",
            "abstract_relations.csv",
            "relation_semantic_adjudication.csv",
            "all_shared_node_evidence_summary.csv",
            "direct_pair_overlaps.csv",
            "tiered_shared_node_pair_candidates_full.csv",
            "tiered_focus_node_pair_paths_full.csv",
            "semantic_reviewed_focus_candidates.csv",
            "tiered_focus_endpoint_quarantine.csv",
            "balanced_focus_review_queue.csv",
            "run_manifest.json",
            "qa_report.json",
            "semantic_review_qa.json",
        }
    input_files = sorted(input_dir / name for name in input_filenames)
    missing_input_files = [path.name for path in input_files if not path.is_file()]
    if missing_input_files:
        raise ValueError(f"missing cleanroom inputs: {missing_input_files}")
    input_hashes_before = {path.name: file_sha256(path) for path in input_files}
    data = load_inputs(input_dir)
    upstream_contract = validate_upstream_contract(input_dir, data)
    pair_banks = pd.concat([data["ite_pairs"], data["tg_pairs"]], ignore_index=True)

    nodes, local_lookup = build_node_registry(
        data["concepts"],
        pair_banks,
        data["relations"],
        data["adjudication"],
        data["shared_summary"],
    )
    alignments, alignment_lookup = build_alignment_edges(
        nodes,
        local_lookup,
        data["shared_summary"],
        data["paths_all"],
        data["paths_pass"],
    )
    nodes["alignment_id"] = nodes["global_concept_id"].map(alignment_lookup).fillna("")
    pair_edges = build_pair_edges(
        pair_banks,
        data["support"],
        data["relations"],
        data["adjudication"],
        data["direct_overlaps"],
        local_lookup,
    )
    relation_audit, observed_relations = build_relation_audit_edges(
        data["relations"], data["adjudication"], pair_edges, local_lookup
    )

    observed_hashes_before_candidates = {
        "nodes": frame_sha256(nodes),
        "pairs": frame_sha256(pair_edges),
        "alignments": frame_sha256(alignments),
        "relations": frame_sha256(observed_relations),
    }
    path_args = (
        nodes,
        local_lookup,
        alignment_lookup,
        pair_edges,
        data["adjudication"],
        data["shared_summary"],
        data["review_queue"],
    )
    paths_all = normalize_paths(
        data["paths_all"], "all_shared_pair_endpoints", "retrieval_only", *path_args
    )
    paths_focus = normalize_paths(
        data["paths_focus"], "focus_shared_node_pre_endpoint_gate", "retrieval_only", *path_args
    )
    paths_pass = normalize_paths(
        data["paths_pass"], "focus_endpoint_pass", "retrieval_only", *path_args
    )
    paths_quarantine = normalize_paths(
        data["paths_quarantine"],
        "focus_endpoint_quarantine",
        "quarantined_not_deleted",
        *path_args,
    )
    oriented, unordered = build_cross_endpoint_candidates(paths_pass)
    review_paths = paths_pass[paths_pass["review_selected"]].copy().sort_values(
        ["review_queue_order", "candidate_id"]
    )
    observed_hashes_after_candidates = {
        "nodes": frame_sha256(nodes),
        "pairs": frame_sha256(pair_edges),
        "alignments": frame_sha256(alignments),
        "relations": frame_sha256(observed_relations),
    }
    if observed_hashes_before_candidates != observed_hashes_after_candidates:
        raise RuntimeError("candidate materialization mutated observed graph frames")

    csv_outputs = {
        "graph_nodes.csv": nodes,
        "graph_pair_edges.csv": pair_edges,
        "graph_alignment_edges.csv": alignments,
        "graph_relation_candidate_edges.csv": relation_audit,
        "graph_observed_relation_edges.csv": observed_relations,
        "graph_candidate_paths_all.csv": paths_all,
        "graph_candidate_paths_focus_pre_gate.csv": paths_focus,
        "graph_candidate_paths_endpoint_pass.csv": paths_pass,
        "graph_candidate_paths_quarantine.csv": paths_quarantine,
        "graph_cross_endpoint_candidate_edges.csv": oriented,
        "graph_cross_endpoint_unordered_index.csv": unordered,
        "graph_review_queue_paths.csv": review_paths,
    }
    for filename, frame in csv_outputs.items():
        write_csv(frame, output_dir / filename)

    graphml_paths = build_observed_graphmls(
        output_dir,
        nodes,
        pair_edges,
        alignments,
        relation_audit,
        observed_relations,
    )
    input_hashes_after = {path.name: file_sha256(path) for path in input_files}
    qa = build_qa(
        data,
        upstream_contract,
        nodes,
        pair_edges,
        alignments,
        relation_audit,
        observed_relations,
        paths_all,
        paths_focus,
        paths_pass,
        paths_quarantine,
        oriented,
        unordered,
        review_paths,
        graphml_paths,
        input_hashes_before,
        input_hashes_after,
    )
    (output_dir / "graph_qa.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_readme(output_dir, qa["counts"])

    output_files = sorted(path for path in output_dir.iterdir() if path.is_file())
    manifest = {
        "contract": "cleanroom_evidence_graph_v1",
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "forbidden_legacy_inputs": [
            "ite_tg_complementarity/graph_analysis",
            "curated_program_bridge",
            "known/control identity fields",
        ],
        "input_sha256": input_hashes_before,
        "output_sha256": {
            path.name: file_sha256(path)
            for path in output_files
            if path.name != "graph_manifest.json"
        },
        "counts": qa["counts"],
        "all_checks_pass": qa["all_checks_pass"],
        "observed_graph_hashes_unchanged_by_candidate_generation": (
            observed_hashes_before_candidates == observed_hashes_after_candidates
        ),
        "candidate_evidence_audit_order_policy": (
            "identity-blind real-path grade then best-grade support; status bucket "
            "and hubness excluded; deterministic ID; no weighted score"
        ),
        "optional_discovery_queue_policy": (
            "within each explicit observation-status bucket only: evidence then "
            "lower shared-route hubness; never a global scientific rank"
        ),
    }
    (output_dir / "graph_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if not qa["all_checks_pass"]:
        raise RuntimeError(f"graph QA failed: {qa['failed_checks']}")
    print(json.dumps({"counts": qa["counts"], "all_checks_pass": True}, indent=2))


if __name__ == "__main__":
    main()
