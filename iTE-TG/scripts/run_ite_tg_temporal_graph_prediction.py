#!/usr/bin/env python3
"""Leakage-safe temporal graph prediction for iTE lever -> TG adoption.

Prediction unit
---------------
One cell is a transferable iTE lever x TG redox family.  At cutoff year t, a
cell enters the risk set only when the lever has at least two independent
eligible pure-iTE source papers, the TG family has at least two primary papers,
and the cell has not yet appeared in TG.  The one-year label is whether the
cell first appears in a primary TG paper in year t+1.

The output is a literature-adoption rank, not an experimental success
probability.  Program priority/status and curated hypothesis edges are never
used as model inputs or labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations, product
from pathlib import Path
from typing import Any, Iterable

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch, Rectangle
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from run_ite_tg_complementarity import (
    ABSTRACT_REVIEW_RE,
    LEVER_LABELS_CN,
    LEVER_PATTERNS,
    REDOX_LABELS_CN,
    REDOX_PATTERNS,
    TITLE_REVIEW_RE,
    bool_value,
    normalize_space,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "ite_tg_complementarity"
DEFAULT_OUTPUT = DEFAULT_INPUT / "graph_prediction"
PAPER_INDEX = ROOT / "final_concept_layer" / "final_paper_index.csv"
FORECAST_CUTOFF = 2025
MIN_SOURCE_PAPERS = 2
MIN_TARGET_PAPERS = 2
RANDOM_STATE = 41

TARGET_ORDER = [
    "ferri_ferrocyanide",
    "iodide_triiodide",
    "fe_ii_iii",
    "quinone_hydroquinone",
    "copper",
    "cobalt_complex",
    "ferrocene_ferrocenium",
    "polysulfide_or_sulfite",
    "metal_complex_other",
]

TARGET_SHORT_LABELS = {
    "ferri_ferrocyanide": "Ferri/Ferro",
    "iodide_triiodide": "I−/I3−",
    "fe_ii_iii": "Fe2+/Fe3+",
    "quinone_hydroquinone": "Q/HQ",
    "copper": "Cu redox",
    "cobalt_complex": "Co complex",
    "ferrocene_ferrocenium": "Fc/Fc+",
    "polysulfide_or_sulfite": "SO4/SO3",
    "metal_complex_other": "其他金属",
}

# The discovery ontology is intentionally broad.  Prediction needs a stricter,
# claim-level mechanism gate so generic words (for example, "electrode",
# "humidity", or "fatigue monitoring") do not become adoption edges.
STRICT_LEVER_PATTERNS: dict[str, re.Pattern[str]] = dict(LEVER_PATTERNS)
STRICT_LEVER_PATTERNS.update(
    {
        "self_healing_or_tough_gel": re.compile(
            r"self.?heal|fracture toughness|toughen|fatigue resistance|"
            r"crack resistance|mechanically robust .*gel|"
            r"stretchable .*network|dynamic .*network",
            re.I,
        ),
        "moisture_or_evaporation_gradient": re.compile(
            r"moisture gradient|water concentration gradient|water gradient|"
            r"coupled heat and moisture|humidity[- ](?:driven|dependent|gradient)|"
            r"evaporation[- ]driven|evaporative cooling|"
            r"evaporation (?:creates|induces|drives|changes)",
            re.I,
        ),
        "electrode_interface": re.compile(
            r"charge.?transfer|exchange current|electrocatal|redox kinetics|"
            r"electrode.?electrolyte interface|interfacial (?:ion|charge|electron)|"
            r"interface[- ]controlled",
            re.I,
        ),
        "ph_or_protonation_switch": re.compile(
            r"pH[- ](?:dependent|responsive|controlled|switch)|protonat|"
            r"deprotonat|acid.?base|zwitterion",
            re.I,
        ),
        "coordination_or_ion_pairing": re.compile(
            r"ion coordination|coordinate(?:s|d)? with|polymer coordination|"
            r"chelat|ion.?pair|complexation|ion.?dipole",
            re.I,
        ),
        "oriented_or_confined_channels": re.compile(
            r"nanochannel|nanopore|subnanometer|molecular channel|"
            r"oriented .*channel|aligned .*channel|confined ion transport|"
            r"ion confinement|reconstructed .*channel|oriented .*chain|"
            r"aligned .*cellulose|anisotropic (?:polymer )?network|"
            r"aligned ion transport pathways?",
            re.I,
        ),
        "hydration_and_solvation": re.compile(
            r"solvat|hydrat|hydrogen bond|water activity|water structure|"
            r"Hofmeister|chaotrop|deep eutectic|solvent[- ]sensitive|"
            r"solvent (?:identity|environment)|mixed solvent|"
            r"low[- ]dielectric .*solvent|bulky solvents?|ionic-liquid solvents?",
            re.I,
        ),
        "phase_or_species_transition": re.compile(
            r"phase transition|volume phase|thermoresponsive|LCST|UCST|"
            r"phase separation|salting.?out|micelli[sz]|"
            r"(?:ion|temperature|thermally|guanidinium)[- ]induced crystalli[sz]|"
            r"crystalli[sz]ation (?:drives|changes|controls|enhances|increases)|"
            r"precipitation (?:drives|changes|controls|enhances|increases)",
            re.I,
        ),
    }
)

GRAPH_LEVER_LABELS_CN = dict(LEVER_LABELS_CN)
GRAPH_LEVER_LABELS_CN.update(
    {
        "self_healing_or_tough_gel": "自修复/动态韧化网络",
        "hydration_and_solvation": "水合/氢键溶剂环境",
        "moisture_or_evaporation_gradient": "湿度响应/蒸发驱动",
        "ion_electron_coupling": "离子–电子协同输运",
        "electrode_interface": "界面电荷转移",
    }
)

GRAPH_TARGET_LABELS_CN = dict(REDOX_LABELS_CN)
GRAPH_TARGET_LABELS_CN["polysulfide_or_sulfite"] = (
    "SO4²−/SO3²−（本地语料）"
)

STRICT_TARGET_PATTERNS: dict[str, re.Pattern[str]] = {
    code: pattern for code, _, pattern in REDOX_PATTERNS
}
STRICT_TARGET_PATTERNS["copper"] = re.compile(
    r"Cu\s*/\s*Cu2|Cu\s*\(en\)|Cu\(I\).*Cu\(II\)|"
    r"Cu\(II\).*Cu\(I\)|Cu2\+.*(?:redox|thermogalvan)|"
    r"CuSO4|Cu\s*\(NO3\)2",
    re.I,
)

MODEL_FEATURES = [
    "common_neighbors",
    "jaccard",
    "adamic_adar",
    "resource_allocation",
    "preferential_attachment_log",
    "inverse_shortest_path",
    "same_component",
    "neighbor_adoption_fraction",
    "ite_source_papers_log",
    "ite_source_claims_log",
    "ite_recent_papers_log",
    "ite_growth",
    "tg_target_papers_log",
    "tg_recent_papers_log",
    "tg_growth",
    "lever_tg_degree",
    "target_lever_degree",
]

MODEL_ORDER = [
    "popularity_baseline",
    "fixed_graph_heuristic",
    "temporal_graph_logistic",
    "temporal_graph_random_forest",
]

MODEL_LABELS = {
    "popularity_baseline": "Degree+recency",
    "fixed_graph_heuristic": "Fixed graph",
    "temporal_graph_logistic": "Graph logistic",
    "temporal_graph_random_forest": "Graph RF",
}

MODEL_COLORS = {
    "popularity_baseline": "#A8A8A8",
    "fixed_graph_heuristic": "#7884B4",
    "temporal_graph_logistic": "#0F4D92",
    "temporal_graph_random_forest": "#42949E",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run temporal lever x TG-system graph prediction."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--paper-index", type=Path, default=PAPER_INDEX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--forecast-cutoff", type=int, default=FORECAST_CUTOFF)
    return parser.parse_args()


def require_columns(frame: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing columns: {missing}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def configure_figure_style() -> None:
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [
        "Arial Unicode MS",
        "Arial",
        "PingFang SC",
        "Hiragino Sans GB",
        "DejaVu Sans",
        "Liberation Sans",
    ]
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=400, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)


def load_data(
    input_dir: Path, paper_index_path: Path, freeze_year: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    inventory = pd.read_csv(input_dir / "ite_claim_inventory_with_levers.csv")
    programs = pd.read_csv(input_dir / "ite_tg_complementarity_programs.csv")
    priors = pd.read_csv(input_dir / "tg_prior_art_by_program.csv")
    papers = pd.read_csv(paper_index_path)
    require_columns(
        inventory,
        [
            "insight_id",
            "paper_id",
            "year",
            "insight_claim",
            "complementarity_candidate_eligible",
            "source_scope",
            "evidence_ready_for_primary_analysis",
            "explicit_TG_or_redox_coupling_cue",
        ],
        "ite_claim_inventory_with_levers.csv",
    )
    require_columns(
        papers,
        [
            "paper_id",
            "source_membership",
            "year",
            "title",
            "abstract",
            "material_raw",
            "mechanism_raw",
        ],
        "final_paper_index.csv",
    )
    papers["year"] = pd.to_numeric(papers["year"], errors="coerce")
    papers = papers[papers["year"].le(freeze_year)].copy()
    inventory["year"] = pd.to_numeric(inventory["year"], errors="coerce")
    inventory = inventory[inventory["year"].le(freeze_year)].copy()
    return inventory, programs, priors, papers


def build_source_records(
    inventory: pd.DataFrame, papers: pd.DataFrame
) -> pd.DataFrame:
    membership = papers.set_index("paper_id")["source_membership"].to_dict()
    eligible = inventory[
        inventory["complementarity_candidate_eligible"].map(bool_value)
        & inventory["paper_id"].map(membership).eq("iTE")
        & inventory["source_scope"].eq("core_iTE_evidenced_insight")
        & ~inventory["explicit_TG_or_redox_coupling_cue"].map(bool_value)
    ].copy()
    eligible["lever_code"] = eligible["insight_claim"].fillna("").map(
        lambda text: [
            code
            for code, pattern in STRICT_LEVER_PATTERNS.items()
            if pattern.search(normalize_space(text))
        ]
    )
    eligible = eligible.explode("lever_code")
    eligible = eligible[eligible["lever_code"].isin(GRAPH_LEVER_LABELS_CN)].copy()
    eligible["lever_label_cn"] = eligible["lever_code"].map(
        GRAPH_LEVER_LABELS_CN
    )
    eligible["source_gate"] = (
        "pure_iTE + core_iTE + A/B direct evidence + no_explicit_TG; "
        "strict claim-level mechanism match"
    )
    keep = [
        "insight_id",
        "paper_id",
        "year",
        "title",
        "doi",
        "insight_claim",
        "evidence_tier",
        "lever_code",
        "lever_label_cn",
        "source_gate",
    ]
    return eligible[keep].drop_duplicates(["insight_id", "lever_code"])


def is_review(row: pd.Series) -> bool:
    return bool(
        TITLE_REVIEW_RE.search(normalize_space(row.get("title", "")))
        or ABSTRACT_REVIEW_RE.search(normalize_space(row.get("abstract", "")))
    )


def pattern_hits(row: pd.Series, pattern: Any) -> tuple[list[str], list[str]]:
    fields: list[str] = []
    terms: list[str] = []
    for field in ["material_raw", "mechanism_raw"]:
        text = normalize_space(row.get(field, ""))
        matches = [match.group(0) for match in pattern.finditer(text)]
        if matches:
            fields.append(field)
            terms.extend(matches)
    return fields, sorted(set(terms), key=str.lower)


def strict_target_family_hits(row: pd.Series) -> dict[str, list[str]]:
    text = " ".join(
        normalize_space(row.get(field, ""))
        for field in ["title", "material_raw", "mechanism_raw"]
    )
    return {
        code: sorted(
            {match.group(0) for match in pattern.finditer(text)},
            key=str.lower,
        )
        for code, pattern in STRICT_TARGET_PATTERNS.items()
        if pattern.search(text)
    }


def build_tg_adoption_evidence(
    papers: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tg = papers[papers["source_membership"].isin(["TG", "iTE|TG"])].copy()
    tg["likely_review"] = tg.apply(is_review, axis=1)
    mapping_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    for _, row in tg.iterrows():
        target_hits = strict_target_family_hits(row)
        lever_hits: dict[str, tuple[list[str], list[str]]] = {}
        for lever_code, pattern in STRICT_LEVER_PATTERNS.items():
            fields, terms = pattern_hits(row, pattern)
            if not fields:
                continue
            lever_hits[lever_code] = (fields, terms)
        for target_code, target_terms in target_hits.items():
            for lever_code, (fields, terms) in lever_hits.items():
                evidence_rows.append(
                    {
                        "paper_id": row["paper_id"],
                        "source_membership": row["source_membership"],
                        "year": int(row["year"]),
                        "title": row["title"],
                        "doi": row["doi"],
                        "likely_review": bool(row["likely_review"]),
                        "target_redox_family": target_code,
                        "target_redox_system_cn": GRAPH_TARGET_LABELS_CN[
                            target_code
                        ],
                        "target_matched_terms": "; ".join(target_terms),
                        "lever_code": lever_code,
                        "lever_label_cn": GRAPH_LEVER_LABELS_CN[lever_code],
                        "lever_match_fields": "; ".join(fields),
                        "lever_matched_terms": "; ".join(terms),
                        "material_raw": row["material_raw"],
                        "mechanism_raw": row["mechanism_raw"],
                        "event_source": "strict_text_rule",
                        "event_eligible": bool(not row["likely_review"]),
                    }
                )
        mapping_rows.append(
            {
                "paper_id": row["paper_id"],
                "source_membership": row["source_membership"],
                "year": int(row["year"]),
                "title": row["title"],
                "doi": row["doi"],
                "likely_review": bool(row["likely_review"]),
                "matched_target_family_count": len(target_hits),
                "matched_target_families": "; ".join(target_hits),
                "matched_target_systems_cn": "; ".join(
                    GRAPH_TARGET_LABELS_CN[code] for code in target_hits
                ),
                "matched_lever_count": len(lever_hits),
                "matched_lever_codes": "; ".join(sorted(lever_hits)),
                "event_eligible": bool(
                    not row["likely_review"] and target_hits and lever_hits
                ),
            }
        )
    evidence = pd.DataFrame(evidence_rows)
    if not evidence.empty:
        evidence = evidence.sort_values(
            ["year", "paper_id", "target_redox_family", "lever_code"]
        )
    return evidence, pd.DataFrame(mapping_rows).sort_values(["year", "paper_id"])


def build_manual_prior_evidence(
    programs: pd.DataFrame, priors: pd.DataFrame
) -> pd.DataFrame:
    pair_map = programs[
        ["program_id", "source_lever_code", "target_redox_family"]
    ].drop_duplicates()
    direct = priors[priors["prior_art_relation"].eq("direct")].merge(
        pair_map,
        on="program_id",
        how="inner",
        suffixes=("_prior", ""),
    )
    direct = direct[
        direct["source_lever_code"].isin(GRAPH_LEVER_LABELS_CN)
        & direct["target_redox_family"].isin(TARGET_ORDER)
    ].copy()
    if direct.empty:
        return pd.DataFrame()
    rows = pd.DataFrame(
        {
            "paper_id": direct["TG_paper_id"],
            "source_membership": "TG",
            "year": pd.to_numeric(direct["TG_year"], errors="coerce").astype(int),
            "title": direct["TG_title"],
            "doi": direct["TG_doi"],
            "likely_review": False,
            "target_redox_family": direct["target_redox_family"],
            "target_redox_system_cn": direct["target_redox_family"].map(
                GRAPH_TARGET_LABELS_CN
            ),
            "target_matched_terms": "manual direct-prior audit",
            "lever_code": direct["source_lever_code"],
            "lever_label_cn": direct["source_lever_code"].map(
                GRAPH_LEVER_LABELS_CN
            ),
            "lever_match_fields": "manual direct-prior audit",
            "lever_matched_terms": "manual direct-prior audit",
            "material_raw": direct["TG_material"],
            "mechanism_raw": direct["TG_mechanism"],
            "event_source": "manual_direct_prior",
            "event_eligible": True,
        }
    )
    return rows.drop_duplicates(
        ["paper_id", "lever_code", "target_redox_family"]
    )


def first_adoption_lookup(evidence: pd.DataFrame) -> dict[tuple[str, str], int]:
    eligible = evidence[evidence["event_eligible"]].copy()
    if eligible.empty:
        return {}
    return {
        (lever, target): int(year)
        for (lever, target), year in eligible.groupby(
            ["lever_code", "target_redox_family"]
        )["year"].min().items()
    }


def target_paper_table(papers: pd.DataFrame) -> pd.DataFrame:
    tg = papers[papers["source_membership"].isin(["TG", "iTE|TG"])].copy()
    tg["likely_review"] = tg.apply(is_review, axis=1)
    tg["target_redox_family"] = tg.apply(
        lambda row: list(strict_target_family_hits(row)), axis=1
    )
    tg = tg.explode("target_redox_family")
    return tg[
        ~tg["likely_review"] & tg["target_redox_family"].isin(TARGET_ORDER)
    ][["paper_id", "source_membership", "year", "target_redox_family"]].drop_duplicates()


def rank01(values: pd.Series | np.ndarray) -> np.ndarray:
    series = pd.Series(values, dtype=float)
    if len(series) <= 1:
        return np.zeros(len(series), dtype=float)
    return ((series.rank(method="average") - 1) / (len(series) - 1)).to_numpy()


def build_snapshot(
    cutoff: int,
    outcomes_observed_through: int,
    source_records: pd.DataFrame,
    adoption_evidence: pd.DataFrame,
    target_papers: pd.DataFrame,
    first_adoption: dict[tuple[str, str], int],
) -> pd.DataFrame:
    source_history = source_records[source_records["year"].le(cutoff)].copy()
    source_counts = source_history.groupby("lever_code")["paper_id"].nunique()
    eligible_levers = sorted(source_counts[source_counts.ge(MIN_SOURCE_PAPERS)].index)
    target_history = target_papers[target_papers["year"].le(cutoff)].copy()
    target_counts = target_history.groupby("target_redox_family")["paper_id"].nunique()
    eligible_targets = [
        code
        for code in TARGET_ORDER
        if int(target_counts.get(code, 0)) >= MIN_TARGET_PAPERS
    ]
    adoption_history = adoption_evidence[
        adoption_evidence["event_eligible"]
        & adoption_evidence["year"].le(cutoff)
    ].copy()

    graph = nx.Graph()
    graph.add_nodes_from((f"lever:{code}", {"node_type": "lever"}) for code in eligible_levers)
    graph.add_nodes_from((f"target:{code}", {"node_type": "target"}) for code in eligible_targets)

    claim_levers = (
        source_history[source_history["lever_code"].isin(eligible_levers)]
        .groupby("insight_id")["lever_code"]
        .agg(lambda values: sorted(set(values)))
    )
    cooccurrence: Counter[tuple[str, str]] = Counter()
    for codes in claim_levers:
        for left, right in combinations(codes, 2):
            cooccurrence[tuple(sorted((left, right)))] += 1
    for (left, right), weight in cooccurrence.items():
        graph.add_edge(
            f"lever:{left}",
            f"lever:{right}",
            edge_type="iTE_claim_cooccurrence",
            weight=int(weight),
        )

    adoption_counts = adoption_history.groupby(
        ["lever_code", "target_redox_family"]
    )["paper_id"].nunique()
    for (lever, target), weight in adoption_counts.items():
        if lever in eligible_levers and target in eligible_targets:
            graph.add_edge(
                f"lever:{lever}",
                f"target:{target}",
                edge_type="historical_TG_adoption",
                weight=int(weight),
            )

    source_claim_counts = source_history.groupby("lever_code")["insight_id"].nunique()
    source_recent = (
        source_history[source_history["year"].between(cutoff - 2, cutoff)]
        .groupby("lever_code")["paper_id"]
        .nunique()
    )
    source_previous = (
        source_history[source_history["year"].between(cutoff - 5, cutoff - 3)]
        .groupby("lever_code")["paper_id"]
        .nunique()
    )
    target_recent = (
        target_history[target_history["year"].between(cutoff - 2, cutoff)]
        .groupby("target_redox_family")["paper_id"]
        .nunique()
    )
    target_previous = (
        target_history[target_history["year"].between(cutoff - 5, cutoff - 3)]
        .groupby("target_redox_family")["paper_id"]
        .nunique()
    )

    rows: list[dict[str, Any]] = []
    for lever, target in product(eligible_levers, eligible_targets):
        first_year = first_adoption.get((lever, target))
        if first_year is not None and first_year <= cutoff:
            continue
        lever_node = f"lever:{lever}"
        target_node = f"target:{target}"
        neighbors_lever = set(graph.neighbors(lever_node)) if lever_node in graph else set()
        neighbors_target = set(graph.neighbors(target_node)) if target_node in graph else set()
        common = neighbors_lever & neighbors_target
        union = neighbors_lever | neighbors_target
        adamic = sum(
            1.0 / math.log(max(2, graph.degree(node))) for node in common
        )
        resource = sum(1.0 / max(1, graph.degree(node)) for node in common)
        try:
            shortest = nx.shortest_path_length(graph, lever_node, target_node)
            same_component = 1
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            shortest = 9
            same_component = 0
        lever_tg_degree = sum(
            1
            for node in neighbors_lever
            if str(node).startswith("target:")
        )
        target_lever_degree = sum(
            1
            for node in neighbors_target
            if str(node).startswith("lever:")
        )
        source_papers = int(source_counts.get(lever, 0))
        source_claims = int(source_claim_counts.get(lever, 0))
        source_recent_count = int(source_recent.get(lever, 0))
        source_previous_count = int(source_previous.get(lever, 0))
        target_paper_count = int(target_counts.get(target, 0))
        target_recent_count = int(target_recent.get(target, 0))
        target_previous_count = int(target_previous.get(target, 0))
        row = {
            "pair_id": f"{lever}|{target}",
            "cutoff_year": cutoff,
            "outcome_year": cutoff + 1,
            "lever_code": lever,
            "lever_label_cn": GRAPH_LEVER_LABELS_CN[lever],
            "target_redox_family": target,
            "target_redox_system_cn": GRAPH_TARGET_LABELS_CN[target],
            "future_adoption_label": (
                int(first_year == cutoff + 1)
                if cutoff + 1 <= outcomes_observed_through
                else np.nan
            ),
            "label_available": bool(cutoff + 1 <= outcomes_observed_through),
            "first_adoption_year": first_year if first_year is not None else np.nan,
            "common_neighbors": int(len(common)),
            "common_neighbor_lever_codes": "; ".join(
                sorted(node.replace("lever:", "", 1) for node in common)
            ),
            "jaccard": len(common) / max(1, len(union)),
            "adamic_adar": float(adamic),
            "resource_allocation": float(resource),
            "preferential_attachment_log": math.log1p(
                graph.degree(lever_node) * graph.degree(target_node)
            ),
            "shortest_path": int(shortest),
            "inverse_shortest_path": 1.0 / (1.0 + shortest),
            "same_component": int(same_component),
            "neighbor_adoption_fraction": len(common)
            / max(
                1,
                sum(
                    1
                    for node in neighbors_lever
                    if str(node).startswith("lever:")
                ),
            ),
            "ite_source_papers": source_papers,
            "ite_source_claims": source_claims,
            "ite_recent_papers": source_recent_count,
            "ite_previous_papers": source_previous_count,
            "ite_growth": (source_recent_count - source_previous_count) / 3.0,
            "ite_source_papers_log": math.log1p(source_papers),
            "ite_source_claims_log": math.log1p(source_claims),
            "ite_recent_papers_log": math.log1p(source_recent_count),
            "tg_target_papers": target_paper_count,
            "tg_recent_papers": target_recent_count,
            "tg_previous_papers": target_previous_count,
            "tg_growth": (target_recent_count - target_previous_count) / 3.0,
            "tg_target_papers_log": math.log1p(target_paper_count),
            "tg_recent_papers_log": math.log1p(target_recent_count),
            "lever_tg_degree": int(lever_tg_degree),
            "target_lever_degree": int(target_lever_degree),
            "feature_max_year": cutoff,
            "label_window": f"{cutoff + 1}",
        }
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["popularity_baseline"] = (
        0.45 * rank01(frame["preferential_attachment_log"])
        + 0.25 * rank01(frame["ite_recent_papers_log"])
        + 0.20 * rank01(frame["tg_recent_papers_log"])
        + 0.10 * rank01(frame["ite_source_papers_log"])
    )
    frame["fixed_graph_heuristic"] = (
        0.22 * rank01(frame["resource_allocation"])
        + 0.16 * rank01(frame["adamic_adar"])
        + 0.14 * rank01(frame["common_neighbors"])
        + 0.10 * rank01(frame["jaccard"])
        + 0.10 * rank01(frame["inverse_shortest_path"])
        + 0.08 * rank01(frame["neighbor_adoption_fraction"])
        + 0.08 * rank01(frame["ite_recent_papers_log"])
        + 0.05 * rank01(frame["ite_source_papers_log"])
        + 0.04 * rank01(frame["tg_recent_papers_log"])
        + 0.03 * rank01(frame["preferential_attachment_log"])
    )
    return frame.sort_values(["lever_code", "target_redox_family"]).reset_index(drop=True)


def pair_block_weights(train: pd.DataFrame) -> np.ndarray:
    repetitions = train.groupby("pair_id")["pair_id"].transform("count")
    weights = 1.0 / repetitions.to_numpy(dtype=float)
    return weights * len(weights) / weights.sum()


def make_model(model_name: str) -> Any:
    if model_name == "temporal_graph_logistic":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=1.0,
                        class_weight="balanced",
                        max_iter=5000,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        )
    if model_name == "temporal_graph_random_forest":
        return RandomForestClassifier(
            n_estimators=600,
            max_depth=5,
            min_samples_leaf=3,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
    raise KeyError(model_name)


def trained_score(
    model_name: str, train: pd.DataFrame, test: pd.DataFrame
) -> np.ndarray:
    if model_name in {"popularity_baseline", "fixed_graph_heuristic"}:
        return test[model_name].to_numpy(dtype=float)
    if train.empty or train["future_adoption_label"].nunique() < 2:
        return test["fixed_graph_heuristic"].to_numpy(dtype=float)
    model = make_model(model_name)
    fit_params: dict[str, Any] = {}
    weights = pair_block_weights(train)
    if model_name == "temporal_graph_logistic":
        fit_params["model__sample_weight"] = weights
    else:
        fit_params["sample_weight"] = weights
    model.fit(
        train[MODEL_FEATURES].fillna(0),
        train["future_adoption_label"].astype(int),
        **fit_params,
    )
    return model.predict_proba(test[MODEL_FEATURES].fillna(0))[:, 1]


def precision_at(y: np.ndarray, score: np.ndarray, k: int) -> float:
    if not len(y):
        return float("nan")
    selected = np.argsort(score)[::-1][: min(k, len(y))]
    return float(y[selected].mean())


def hits_at(y: np.ndarray, score: np.ndarray, k: int) -> int:
    selected = np.argsort(score)[::-1][: min(k, len(y))]
    return int(y[selected].sum())


def ndcg_at(y: np.ndarray, score: np.ndarray, k: int) -> float:
    order = np.argsort(score)[::-1][: min(k, len(y))]
    gains = y[order]
    discounts = 1.0 / np.log2(np.arange(2, len(gains) + 2))
    dcg = float(np.sum(gains * discounts))
    ideal = np.sort(y)[::-1][: len(gains)]
    idcg = float(np.sum(ideal * discounts))
    return dcg / idcg if idcg else 0.0


def metric_row(
    frame: pd.DataFrame, score: np.ndarray, model_name: str, fold_role: str
) -> dict[str, Any]:
    y = frame["future_adoption_label"].astype(int).to_numpy()
    positive_rate = float(y.mean()) if len(y) else float("nan")
    return {
        "test_cutoff": int(frame["cutoff_year"].iloc[0]),
        "outcome_year": int(frame["outcome_year"].iloc[0]),
        "fold_role": fold_role,
        "model": model_name,
        "model_label": MODEL_LABELS[model_name],
        "n_candidates": int(len(frame)),
        "n_positive": int(y.sum()),
        "positive_rate": positive_rate,
        "average_precision": float(average_precision_score(y, score))
        if y.sum()
        else float("nan"),
        "roc_auc": float(roc_auc_score(y, score))
        if 0 < y.sum() < len(y)
        else float("nan"),
        "precision_at_5": precision_at(y, score, 5),
        "hits_at_5": hits_at(y, score, 5),
        "precision_at_10": precision_at(y, score, 10),
        "hits_at_10": hits_at(y, score, 10),
        "ndcg_at_10": ndcg_at(y, score, 10),
        "ap_lift_over_prevalence": (
            float(average_precision_score(y, score) / positive_rate)
            if y.sum() and positive_rate
            else float("nan")
        ),
    }


def rolling_backtest(
    snapshots: dict[int, pd.DataFrame],
    selection_cutoffs: list[int],
    holdout_cutoff: int,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    prediction_rows: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    for cutoff in selection_cutoffs + [holdout_cutoff]:
        test = snapshots[cutoff].copy()
        train = pd.concat(
            [
                frame
                for year, frame in snapshots.items()
                if year < cutoff
            ],
            ignore_index=True,
        )
        role = "model_selection" if cutoff in selection_cutoffs else "locked_holdout"
        for model_name in MODEL_ORDER:
            score = trained_score(model_name, train, test)
            metric_rows.append(metric_row(test, score, model_name, role))
            scored = test[
                [
                    "pair_id",
                    "cutoff_year",
                    "outcome_year",
                    "lever_code",
                    "lever_label_cn",
                    "target_redox_family",
                    "target_redox_system_cn",
                    "future_adoption_label",
                ]
            ].copy()
            scored["fold_role"] = role
            scored["model"] = model_name
            scored["raw_score"] = score
            scored["rank_score_0_100"] = 100 * rank01(score)
            prediction_rows.append(scored)
    metrics = pd.DataFrame(metric_rows)
    selection = metrics[metrics["fold_role"].eq("model_selection")]
    selected_model = (
        selection.groupby("model")["average_precision"]
        .mean()
        .sort_values(ascending=False)
        .index[0]
    )
    return metrics, pd.concat(prediction_rows, ignore_index=True), selected_model


def final_forecast(
    snapshots: dict[int, pd.DataFrame], forecast_cutoff: int, selected_model: str
) -> pd.DataFrame:
    train = pd.concat(
        [frame for year, frame in snapshots.items() if year < forecast_cutoff],
        ignore_index=True,
    )
    forecast = snapshots[forecast_cutoff].copy()
    raw_score = trained_score(selected_model, train, forecast)
    forecast["selected_model"] = selected_model
    forecast["selected_model_label"] = MODEL_LABELS[selected_model]
    forecast["raw_model_score"] = raw_score
    forecast["adoption_rank_score_0_100"] = 100 * rank01(raw_score)
    forecast["within_target_rank_score_0_100"] = forecast.groupby(
        "target_redox_family"
    )["raw_model_score"].transform(lambda values: 100 * rank01(values))
    forecast["cold_start_extrapolation"] = forecast["lever_tg_degree"].eq(0)
    forecast["graph_support_tier"] = np.select(
        [
            forecast["common_neighbors"].ge(2)
            & forecast["ite_source_papers"].ge(5)
            & forecast["tg_target_papers"].ge(5),
            forecast["common_neighbors"].ge(1)
            & forecast["ite_source_papers"].ge(MIN_SOURCE_PAPERS)
            & forecast["tg_target_papers"].ge(MIN_TARGET_PAPERS),
        ],
        ["A_connected", "B_thin_support"],
        default="C_cold_or_sparse",
    )
    return forecast.sort_values(
        ["adoption_rank_score_0_100", "ite_source_papers"],
        ascending=[False, False],
    ).reset_index(drop=True)


def manual_prior_overlay(
    programs: pd.DataFrame, priors: pd.DataFrame
) -> pd.DataFrame:
    program_pairs = programs[
        [
            "program_id",
            "program_title_cn",
            "source_lever_code",
            "target_redox_family",
            "candidate_status",
            "positive_control",
        ]
    ].drop_duplicates()
    direct = priors[priors["prior_art_relation"].eq("direct")].copy()
    direct_summary = (
        direct.groupby("program_id")
        .agg(
            manual_direct_prior_count=("TG_paper_id", "nunique"),
            manual_direct_prior_earliest_year=("TG_year", "min"),
            manual_direct_prior_paper_ids=(
                "TG_paper_id",
                lambda values: "; ".join(sorted(set(map(str, values)))),
            ),
        )
        .reset_index()
    )
    merged = program_pairs.merge(direct_summary, on="program_id", how="left")
    merged["manual_direct_prior_count"] = (
        merged["manual_direct_prior_count"].fillna(0).astype(int)
    )
    return merged


def build_matrix_long(
    forecast: pd.DataFrame,
    source_records: pd.DataFrame,
    target_papers: pd.DataFrame,
    first_adoption: dict[tuple[str, str], int],
    strict_first_adoption: dict[tuple[str, str], int],
    overlay: pd.DataFrame,
    cutoff: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    source_counts = (
        source_records[source_records["year"].le(cutoff)]
        .groupby("lever_code")["paper_id"]
        .nunique()
        .to_dict()
    )
    target_counts = (
        target_papers[target_papers["year"].le(cutoff)]
        .groupby("target_redox_family")["paper_id"]
        .nunique()
        .to_dict()
    )
    forecast_lookup = forecast.set_index(
        ["lever_code", "target_redox_family"]
    ).to_dict("index")
    overlay_groups = {
        key: group
        for key, group in overlay.groupby(
            ["source_lever_code", "target_redox_family"]
        )
    }
    rows: list[dict[str, Any]] = []
    for lever, target in product(GRAPH_LEVER_LABELS_CN, TARGET_ORDER):
        source_count = int(source_counts.get(lever, 0))
        target_count = int(target_counts.get(target, 0))
        composite_first = first_adoption.get((lever, target))
        strict_first = strict_first_adoption.get((lever, target))
        group = overlay_groups.get((lever, target))
        manual_count = (
            int(group["manual_direct_prior_count"].max()) if group is not None else 0
        )
        manual_year_values = (
            pd.to_numeric(
                group["manual_direct_prior_earliest_year"], errors="coerce"
            ).dropna()
            if group is not None
            else pd.Series(dtype=float)
        )
        manual_year = (
            int(manual_year_values.min()) if len(manual_year_values) else np.nan
        )
        program_ids = (
            "; ".join(sorted(group["program_id"].astype(str).unique()))
            if group is not None
            else ""
        )
        program_titles = (
            " | ".join(sorted(group["program_title_cn"].astype(str).unique()))
            if group is not None
            else ""
        )
        predicted = forecast_lookup.get((lever, target), {})
        if strict_first is not None and strict_first <= cutoff:
            state = "observed_in_strict_TG_graph"
            observed_year = strict_first
        elif composite_first is not None and composite_first <= cutoff:
            state = "observed_in_manual_direct_prior_audit"
            observed_year = composite_first
        elif source_count < MIN_SOURCE_PAPERS and target_count < MIN_TARGET_PAPERS:
            state = "insufficient_source_and_target_history"
            observed_year = np.nan
        elif source_count < MIN_SOURCE_PAPERS:
            state = "insufficient_iTE_source_history"
            observed_year = np.nan
        elif target_count < MIN_TARGET_PAPERS:
            state = "insufficient_TG_target_history"
            observed_year = np.nan
        else:
            state = "forecast_candidate"
            observed_year = np.nan
        rows.append(
            {
                "lever_code": lever,
                "lever_label_cn": GRAPH_LEVER_LABELS_CN[lever],
                "target_redox_family": target,
                "target_redox_system_cn": GRAPH_TARGET_LABELS_CN[target],
                "cell_state": state,
                "observed_first_year": observed_year,
                "strict_regex_first_year": strict_first
                if strict_first is not None
                else np.nan,
                "composite_proxy_first_year": composite_first
                if composite_first is not None
                else np.nan,
                "manual_direct_prior_count": manual_count,
                "manual_direct_prior_earliest_year": manual_year,
                "ite_source_paper_count_at_cutoff": source_count,
                "TG_target_paper_count_at_cutoff": target_count,
                "adoption_rank_score_0_100": predicted.get(
                    "adoption_rank_score_0_100", np.nan
                ),
                "within_target_rank_score_0_100": predicted.get(
                    "within_target_rank_score_0_100", np.nan
                ),
                "raw_model_score": predicted.get("raw_model_score", np.nan),
                "common_neighbors": predicted.get("common_neighbors", np.nan),
                "common_neighbor_lever_codes": predicted.get(
                    "common_neighbor_lever_codes", ""
                ),
                "graph_support_tier": predicted.get(
                    "graph_support_tier", ""
                ),
                "cold_start_extrapolation": predicted.get(
                    "cold_start_extrapolation", np.nan
                ),
                "curated_program_ids": program_ids,
                "curated_program_titles_cn": program_titles,
                "curated_program_overlay": bool(program_ids),
                "interpretation": (
                    "historically observed by the local-corpus transfer proxy"
                    if state.startswith("observed")
                    else (
                        "eligible one-year transfer-proxy forecast; not experimental success probability"
                        if state == "forecast_candidate"
                        else "not scored because the historical risk-set gate is not met"
                    )
                ),
            }
        )
    matrix = pd.DataFrame(rows)
    candidate_max = (
        matrix[matrix["cell_state"].eq("forecast_candidate")]
        .groupby("lever_code")["adoption_rank_score_0_100"]
        .max()
        .to_dict()
    )
    source_order = {
        lever: index
        for index, lever in enumerate(
            sorted(
                GRAPH_LEVER_LABELS_CN,
                key=lambda code: (
                    -candidate_max.get(code, -1),
                    -source_counts.get(code, 0),
                    GRAPH_LEVER_LABELS_CN[code],
                ),
            )
        )
    }
    matrix["row_order"] = matrix["lever_code"].map(source_order)
    matrix["column_order"] = matrix["target_redox_family"].map(
        {code: index for index, code in enumerate(TARGET_ORDER)}
    )
    matrix = matrix.sort_values(["row_order", "column_order"])
    wide = matrix.pivot(
        index="lever_label_cn",
        columns="target_redox_system_cn",
        values="adoption_rank_score_0_100",
    )
    row_labels = (
        matrix[["lever_label_cn", "row_order"]]
        .drop_duplicates()
        .sort_values("row_order")["lever_label_cn"]
        .tolist()
    )
    col_labels = [GRAPH_TARGET_LABELS_CN[code] for code in TARGET_ORDER]
    wide = wide.reindex(index=row_labels, columns=col_labels)
    return matrix, wide


def plot_backtest(metrics: pd.DataFrame, output_dir: Path, selected_model: str) -> None:
    holdout = metrics[metrics["fold_role"].eq("locked_holdout")]
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), constrained_layout=True)
    cutoffs = sorted(metrics["test_cutoff"].unique())
    positions = np.arange(len(cutoffs))
    for model in MODEL_ORDER:
        subset = metrics[metrics["model"].eq(model)].set_index("test_cutoff")
        values = [subset.loc[cutoff, "average_precision"] for cutoff in cutoffs]
        axes[0].plot(
            positions,
            values,
            marker="o",
            ms=3.2,
            lw=1.15,
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
        )
    prevalence = (
        metrics[metrics["model"].eq("popularity_baseline")]
        .set_index("test_cutoff")["positive_rate"]
        .reindex(cutoffs)
        .to_numpy()
    )
    axes[0].plot(
        positions,
        prevalence,
        color="#B64342",
        marker="o",
        ms=3.2,
        lw=1.0,
        ls="--",
        label="Prevalence",
    )
    axes[0].set_xticks(
        positions,
        [str(year + 1) for year in cutoffs],
        rotation=35,
        ha="right",
    )
    axes[0].set_xlabel("结果年份")
    axes[0].set_ylabel("平均精确率（AP）")
    axes[0].set_title("a  逐年前向回测", loc="left", weight="bold")
    axes[0].legend(fontsize=6, ncol=2)

    x = np.arange(len(MODEL_ORDER))
    holdout = holdout.set_index("model").reindex(MODEL_ORDER)
    axes[1].bar(
        x - 0.16,
        holdout["average_precision"],
        width=0.32,
        color=[MODEL_COLORS[model] for model in MODEL_ORDER],
    )
    axes[1].bar(
        x + 0.16,
        holdout["precision_at_5"],
        width=0.32,
        color=[MODEL_COLORS[model] for model in MODEL_ORDER],
        alpha=0.48,
        hatch="///",
    )
    axes[1].axhline(
        float(holdout["positive_rate"].iloc[0]),
        color="#B64342",
        lw=1.0,
        ls="--",
    )
    axes[1].set_xticks(x, [MODEL_LABELS[model] for model in MODEL_ORDER], rotation=30, ha="right")
    axes[1].set_ylabel("指标值")
    axes[1].set_title(
        f"b  时间留出 {int(holdout['outcome_year'].iloc[0])}\n实色=AP；斜纹=P@5",
        loc="left",
        weight="bold",
    )
    figure.suptitle(
        f"时间图模型审计（矩阵模型：{MODEL_LABELS[selected_model]}）",
        x=0.01,
        ha="left",
        fontsize=9,
        weight="bold",
    )
    save_figure(figure, output_dir / "temporal_graph_backtest")


def plot_prediction_matrix(
    matrix: pd.DataFrame, output_dir: Path, selected_model: str, cutoff: int
) -> None:
    row_info = (
        matrix[["lever_code", "lever_label_cn", "row_order"]]
        .drop_duplicates()
        .sort_values("row_order")
    )
    row_codes = row_info["lever_code"].tolist()
    row_labels = row_info["lever_label_cn"].tolist()
    col_codes = TARGET_ORDER
    col_labels = [TARGET_SHORT_LABELS[code] for code in col_codes]
    lookup = matrix.set_index(["lever_code", "target_redox_family"])
    values = np.full((len(row_codes), len(col_codes)), np.nan)
    states: list[list[str]] = [["" for _ in col_codes] for _ in row_codes]
    observed_years = np.full_like(values, np.nan)
    program_overlay = np.zeros_like(values, dtype=bool)
    for i, lever in enumerate(row_codes):
        for j, target in enumerate(col_codes):
            row = lookup.loc[(lever, target)]
            states[i][j] = row["cell_state"]
            observed_years[i, j] = row["observed_first_year"]
            program_overlay[i, j] = bool(row["curated_program_overlay"])
            if row["cell_state"] == "forecast_candidate":
                values[i, j] = row["adoption_rank_score_0_100"]

    cmap = LinearSegmentedColormap.from_list(
        "graph_rank", ["#F4F6F7", "#B4C0E4", "#3775BA", "#0F4D92"]
    )
    figure, axis = plt.subplots(figsize=(7.2, 8.6), constrained_layout=True)
    image = axis.imshow(values, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i in range(len(row_codes)):
        for j in range(len(col_codes)):
            state = states[i][j]
            if state.startswith("observed"):
                axis.add_patch(
                    Rectangle(
                        (j - 0.5, i - 0.5),
                        1,
                        1,
                        facecolor="#CFCECE",
                        edgecolor="white",
                        linewidth=0.8,
                        hatch="///" if "manual" in state else None,
                    )
                )
                year = observed_years[i, j]
                text = "已见" if pd.isna(year) else f"已见\n{int(year)}"
                axis.text(j, i, text, ha="center", va="center", fontsize=5.8, color="#4D4D4D")
            elif state != "forecast_candidate":
                axis.add_patch(
                    Rectangle(
                        (j - 0.5, i - 0.5),
                        1,
                        1,
                        facecolor="white",
                        edgecolor="#E1E4E7",
                        linewidth=0.8,
                    )
                )
                axis.text(j, i, "—", ha="center", va="center", fontsize=6, color="#A8A8A8")
            else:
                score = values[i, j]
                axis.text(
                    j,
                    i,
                    f"{score:.0f}",
                    ha="center",
                    va="center",
                    fontsize=6.2,
                    color="white" if score >= 58 else "#272727",
                )
            if program_overlay[i, j]:
                axis.add_patch(
                    Rectangle(
                        (j - 0.46, i - 0.46),
                        0.92,
                        0.92,
                        fill=False,
                        edgecolor="#B64342",
                        linewidth=1.4,
                    )
                )
    axis.set_xticks(range(len(col_labels)), col_labels, rotation=38, ha="right", rotation_mode="anchor")
    axis.set_yticks(range(len(row_labels)), row_labels)
    axis.tick_params(length=0)
    axis.set_xlabel("TG 红氧体系")
    axis.set_ylabel("iTE 可迁移机制")
    axis.set_title(
        f"iTE 可迁移机制 × TG 红氧体系：{cutoff + 1} 迁移代理排名\n"
        f"{MODEL_LABELS[selected_model]}；数字为风险集内百分位，不是成功概率",
        loc="left",
        fontsize=11,
        weight="bold",
        pad=14,
    )
    colorbar = figure.colorbar(image, ax=axis, fraction=0.025, pad=0.02)
    colorbar.set_label("迁移代理排名分数（0–100）")
    axis.legend(
        handles=[
            Patch(facecolor="#CFCECE", label="截止期前已观察"),
            Patch(facecolor="#CFCECE", hatch="///", label="由人工 direct-prior 补证"),
            Patch(facecolor="white", edgecolor="#B64342", linewidth=1.4, label="当前实验程序"),
            Patch(facecolor="white", edgecolor="#E1E4E7", label="历史不足 / 不评分"),
        ],
        loc="upper left",
        bbox_to_anchor=(0, -0.08),
        ncol=2,
        fontsize=7,
    )
    save_figure(figure, output_dir / "ite_tg_graph_prediction_matrix")


def report_cn(
    metrics: pd.DataFrame,
    selected_model: str,
    forecast: pd.DataFrame,
    matrix: pd.DataFrame,
    evidence: pd.DataFrame,
    source_records: pd.DataFrame,
    cutoff: int,
) -> str:
    selection = metrics[metrics["fold_role"].eq("model_selection")]
    selection_mean = selection.groupby("model")["average_precision"].mean()
    holdout = metrics[
        metrics["fold_role"].eq("locked_holdout")
        & metrics["model"].eq(selected_model)
    ].iloc[0]
    holdout_popularity = metrics[
        metrics["fold_role"].eq("locked_holdout")
        & metrics["model"].eq("popularity_baseline")
    ].iloc[0]
    selection_years = sorted(selection["outcome_year"].unique())
    selection_year_text = "、".join(map(str, selection_years))
    selection_positive_total = int(
        selection.drop_duplicates(["test_cutoff", "outcome_year"])[
            "n_positive"
        ].sum()
    )
    candidates = matrix[matrix["cell_state"].eq("forecast_candidate")].sort_values(
        ["adoption_rank_score_0_100", "ite_source_paper_count_at_cutoff"],
        ascending=[False, False],
    )
    observed = matrix[matrix["cell_state"].str.startswith("observed")]
    unavailable = matrix[~matrix["cell_state"].isin(["forecast_candidate"]) & ~matrix["cell_state"].str.startswith("observed")]
    program_candidates = candidates[candidates["curated_program_overlay"]]
    strict_event_papers = evidence.loc[
        evidence["event_eligible"]
        & evidence["event_source"].eq("strict_text_rule"),
        "paper_id",
    ].nunique()
    manual_event_papers = evidence.loc[
        evidence["event_eligible"]
        & evidence["event_source"].eq("manual_direct_prior"),
        "paper_id",
    ].nunique()
    lines = [
        "# iTE → TG temporal graph prediction",
        "",
        "## 结论",
        "",
        f"已完成按年份切分的 `iTE lever × TG redox family` 图预测。它预测的是 **{cutoff + 1} 年本地 TG 语料中首次出现该机制–红氧组合的迁移代理排名**，不是实验成功率，也不是声称论文已经真正完成机制迁移。",
        "",
        f"- 选择模型：`{MODEL_LABELS[selected_model]}`。它是固定权重、无权图的局部邻近排序，只看 cutoff 前的共同邻居、路径、度数及两端累计/近 3 年活跃度。",
        f"- 模型比较使用 {len(selection_years)} 个有新增事件的前向年份（{selection_year_text}，共 {selection_positive_total} 个新增代理事件），按 mean AP 选型；图邻近模型平均 AP={selection_mean[selected_model]:.3f}，同期 degree+recency 基线={selection_mean['popularity_baseline']:.3f}。",
        f"- 未参与选型的时间留出测试：{int(holdout['test_cutoff'])}→{int(holdout['outcome_year'])}，候选 {int(holdout['n_candidates'])}、下一年新增代理事件 {int(holdout['n_positive'])}；图邻近模型 AP={holdout['average_precision']:.3f}，随机排序参考={holdout['positive_rate']:.3f}，P@5={holdout['precision_at_5']:.3f}，NDCG@10={holdout['ndcg_at_10']:.3f}。",
        f"- 诚实对照：同一时间留出上，degree+recency 基线 AP={holdout_popularity['average_precision']:.3f}，高于图邻近模型 {holdout['average_precision']:.3f}；因此现在只能说图有排序信号，不能说高阶图结构已经稳定增加预测力。",
        "",
        "## 预测矩阵怎么读",
        "",
        f"- 总格子：{len(matrix)}；可预测 {len(candidates)}；已在 TG 出现 {len(observed)}；历史不足不评分 {len(unavailable)}。",
        "- 蓝色数字：当前风险集内的 0–100 排名；它不是校准概率。",
        "- 点选/CSV 中另有支撑等级：A=至少 2 个共同邻居且两端各有 ≥5 篇；B=至少 1 个共同邻居；C=冷启动或历史稀疏。等级不参与图分数，只提示证据厚度。",
        "- 灰格：本地 TG 语料已经出现，不应再次称为未来迁移。斜纹灰格表示严格文本规则漏掉、但人工 direct-prior 审计已确认。",
        "- 红框：当前 complementarity workflow 中已有具体实验程序；程序优先级/状态不进入模型，但已人工确认的 direct prior 会作为历史证据进入风险集。",
        "",
        "## 最高的未观察候选组合",
        "",
    ]
    for index, row in enumerate(candidates.head(12).itertuples(index=False), start=1):
        program_note = "；当前已有实验程序" if row.curated_program_overlay else ""
        bridge_codes = [
            code.strip()
            for code in str(row.common_neighbor_lever_codes).split(";")
            if code.strip()
        ][:3]
        bridge_labels = [
            GRAPH_LEVER_LABELS_CN.get(code, code) for code in bridge_codes
        ]
        bridge_note = (
            f"；图中共同邻居示例：{'、'.join(bridge_labels)}"
            if bridge_labels
            else "；图中没有共同邻居，主要由两端历史活跃度排序"
        )
        support_note = {
            "A_connected": "A（连接充分）",
            "B_thin_support": "B（薄支撑）",
            "C_cold_or_sparse": "C（冷启动/稀疏）",
        }.get(str(row.graph_support_tier), str(row.graph_support_tier))
        cold_note = (
            "；冷启动外推（该 lever 尚无历史 TG 代理边）"
            if bool(row.cold_start_extrapolation)
            else ""
        )
        lines.append(
            f"{index}. **{row.lever_label_cn} → {row.target_redox_system_cn}**：rank={row.adoption_rank_score_0_100:.1f}，支撑={support_note}，iTE source={row.ite_source_paper_count_at_cutoff} 篇，TG target={row.TG_target_paper_count_at_cutoff} 篇{bridge_note}{cold_note}{program_note}。"
        )
    lines.extend(
        [
            "",
            "## 当前实验程序在预测图里的位置",
            "",
        ]
    )
    if program_candidates.empty:
        lines.append("当前红框程序全部已有 TG 先例或历史支持不足，因此没有进入未来风险集。")
    else:
        for row in program_candidates.sort_values("adoption_rank_score_0_100", ascending=False).itertuples(index=False):
            support_note = {
                "A_connected": "A",
                "B_thin_support": "B",
                "C_cold_or_sparse": "C",
            }.get(str(row.graph_support_tier), str(row.graph_support_tier))
            lines.append(
                f"- **{row.curated_program_titles_cn}**：{row.lever_label_cn} → {row.target_redox_system_cn}，rank={row.adoption_rank_score_0_100:.1f}，支撑={support_note}。"
            )
    lines.extend(
        [
            "",
            "## 训练口径",
            "",
            f"- 数据冻结到 {cutoff}，完全排除不完整的 2026 文献。",
            f"- iTE source 只使用 pure-iTE、core-iTE、A/B 直接证据、且没有显式 TG/redox 耦合的 claim，再做 claim-level 严格机制匹配；当前共有 {source_records['paper_id'].nunique()} 篇独立 source paper。",
            f"- TG 代理事件使用非 review 论文中 `material_raw` 或 `mechanism_raw` 的严格 lever 命中，并允许一篇多 redox family；有 {strict_event_papers} 篇规则证据论文，另把 {manual_event_papers} 篇人工 direct-prior 证据按年份并入历史图和风险集。",
            "- 每个 cutoff 都重新建图；`feature_max_year <= cutoff`，标签只看下一年。",
            "- 风险集要求 lever 至少 2 篇独立 iTE 来源、TG family 至少 2 篇历史论文，且组合此前未出现。",
            "- 未使用 semantic similarity、program priority、candidate status、supports_hypothesis 或人工程序边。",
            "",
            "## 限制",
            "",
            "历史标签仍是规则字段与人工 direct-prior 组成的迁移代理，可能漏掉不同术语，也可能把相邻机制误判为采用。当前图模型也是固定权重、二值无权的局部邻近启发式；在唯一时间留出年份是否超过 degree+recency 基线必须以实际指标为准。因此这是小样本 temporal graph pilot，适合排序和找值得人工复核的格子，不适合声称高阶图结构已有稳定增益、采用概率或因果成功。",
            "",
            "## 文件",
            "",
            "- `ite_tg_graph_prediction_matrix.svg`：主预测矩阵。",
            "- `temporal_graph_backtest.svg`：逐年前向回测与时间留出测试。",
            "- `future_lever_tg_predictions.csv`：所有可预测格及图特征。",
            "- `lever_tg_prediction_matrix_long.csv`：216 个格子的状态、分数、先例和 program overlay。",
            "- `temporal_risk_snapshots.csv` / `rolling_backtest_predictions.csv`：完整训练与回测数据。",
            "- `tg_lever_adoption_evidence.csv`：TG 采用标签的逐篇证据。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    paper_index_path = args.paper_index.resolve()
    output_dir = args.output_dir.resolve()
    cutoff = int(args.forecast_cutoff)
    output_dir.mkdir(parents=True, exist_ok=True)
    configure_figure_style()

    inventory, programs, priors, papers = load_data(
        input_dir, paper_index_path, cutoff
    )
    source_records = build_source_records(inventory, papers)
    strict_adoption_evidence, tg_mapping_audit = build_tg_adoption_evidence(
        papers
    )
    manual_adoption_evidence = build_manual_prior_evidence(programs, priors)
    adoption_evidence = pd.concat(
        [strict_adoption_evidence, manual_adoption_evidence],
        ignore_index=True,
    ).drop_duplicates(
        ["paper_id", "lever_code", "target_redox_family", "event_source"]
    )
    adoption_evidence = adoption_evidence.sort_values(
        ["year", "paper_id", "target_redox_family", "lever_code"]
    )
    target_papers = target_paper_table(papers)
    first_adoption = first_adoption_lookup(adoption_evidence)
    strict_first_adoption = first_adoption_lookup(strict_adoption_evidence)

    snapshots: dict[int, pd.DataFrame] = {}
    for year in range(2014, cutoff + 1):
        snapshot = build_snapshot(
            year,
            cutoff,
            source_records,
            adoption_evidence,
            target_papers,
            first_adoption,
        )
        if not snapshot.empty:
            snapshots[year] = snapshot
    required_cutoffs = [2022, 2023, 2024, cutoff]
    missing = [year for year in required_cutoffs if year not in snapshots]
    if missing:
        raise RuntimeError(f"Missing required temporal snapshots: {missing}")

    holdout_cutoff = 2024
    selection_cutoffs = [
        year
        for year, snapshot in sorted(snapshots.items())
        if year < holdout_cutoff
        and snapshot["future_adoption_label"].sum() > 0
    ]
    metrics, backtest_predictions, selected_model = rolling_backtest(
        snapshots,
        selection_cutoffs=selection_cutoffs,
        holdout_cutoff=holdout_cutoff,
    )
    forecast = final_forecast(snapshots, cutoff, selected_model)
    overlay = manual_prior_overlay(programs, priors)
    manual_observed_pairs = set(
        overlay.loc[
            overlay["manual_direct_prior_count"].gt(0),
            ["source_lever_code", "target_redox_family"],
        ].itertuples(index=False, name=None)
    )
    forecast = forecast[
        ~forecast[["lever_code", "target_redox_family"]]
        .apply(tuple, axis=1)
        .isin(manual_observed_pairs)
    ].copy()
    forecast["adoption_rank_score_0_100"] = 100 * rank01(
        forecast["raw_model_score"]
    )
    forecast["within_target_rank_score_0_100"] = forecast.groupby(
        "target_redox_family"
    )["raw_model_score"].transform(lambda values: 100 * rank01(values))
    forecast = forecast.sort_values(
        ["adoption_rank_score_0_100", "ite_source_papers"],
        ascending=[False, False],
    ).reset_index(drop=True)
    forecast["forecast_rank"] = np.arange(1, len(forecast) + 1)
    forecast["forecast_interpretation"] = (
        "one-year local-corpus transfer-proxy rank; not experimental success probability"
    )
    matrix, matrix_wide = build_matrix_long(
        forecast,
        source_records,
        target_papers,
        first_adoption,
        strict_first_adoption,
        overlay,
        cutoff,
    )

    all_snapshots = pd.concat(snapshots.values(), ignore_index=True)
    assert all(
        all_snapshots["feature_max_year"].eq(all_snapshots["cutoff_year"])
    )
    positives = all_snapshots[all_snapshots["future_adoption_label"].eq(1)]
    assert all(
        positives["first_adoption_year"].eq(positives["cutoff_year"] + 1)
    )
    forbidden = {
        "priority_score",
        "candidate_status",
        "positive_control",
        "supports_hypothesis",
        "adapted_into",
        "semantic_similarity",
    }
    assert not (forbidden & set(MODEL_FEATURES))
    assert len(matrix) == len(GRAPH_LEVER_LABELS_CN) * len(TARGET_ORDER)
    assert all_snapshots.loc[
        all_snapshots["cutoff_year"].eq(cutoff), "future_adoption_label"
    ].isna().all()
    assert not all_snapshots.loc[
        all_snapshots["cutoff_year"].eq(cutoff), "label_available"
    ].any()

    source_records.to_csv(output_dir / "ite_source_lever_records.csv", index=False)
    adoption_evidence.to_csv(output_dir / "tg_lever_adoption_evidence.csv", index=False)
    strict_adoption_evidence.to_csv(
        output_dir / "strict_tg_lever_adoption_evidence.csv", index=False
    )
    manual_adoption_evidence.to_csv(
        output_dir / "manual_prior_adoption_evidence.csv", index=False
    )
    tg_mapping_audit.to_csv(output_dir / "tg_paper_mapping_audit.csv", index=False)
    all_snapshots.to_csv(output_dir / "temporal_risk_snapshots.csv", index=False)
    metrics.to_csv(output_dir / "rolling_backtest_metrics.csv", index=False)
    backtest_predictions.to_csv(output_dir / "rolling_backtest_predictions.csv", index=False)
    forecast.to_csv(output_dir / "future_lever_tg_predictions.csv", index=False)
    forecast.head(30).to_csv(output_dir / "future_lever_tg_top30.csv", index=False)
    matrix.to_csv(output_dir / "lever_tg_prediction_matrix_long.csv", index=False)
    matrix_wide.to_csv(output_dir / "lever_tg_prediction_matrix_scores.csv")
    overlay.to_csv(output_dir / "curated_program_matrix_overlay.csv", index=False)

    plot_backtest(metrics, output_dir, selected_model)
    plot_prediction_matrix(matrix, output_dir, selected_model, cutoff)

    report = report_cn(
        metrics,
        selected_model,
        forecast,
        matrix,
        adoption_evidence,
        source_records,
        cutoff,
    )
    (output_dir / "PREDICTION_RESULTS_CN.md").write_text(
        report, encoding="utf-8"
    )

    input_paths = [
        input_dir / "ite_claim_inventory_with_levers.csv",
        input_dir / "ite_tg_complementarity_programs.csv",
        input_dir / "tg_prior_art_by_program.csv",
        paper_index_path,
    ]
    output_paths = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "prediction_manifest.json"
    )
    holdout = metrics[
        metrics["fold_role"].eq("locked_holdout")
        & metrics["model"].eq(selected_model)
    ].iloc[0]
    holdout_popularity = metrics[
        metrics["fold_role"].eq("locked_holdout")
        & metrics["model"].eq("popularity_baseline")
    ].iloc[0]
    manifest = {
        "analysis": "temporal_iTE_lever_to_TG_redox_link_prediction",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "forecast_cutoff": cutoff,
        "forecast_year": cutoff + 1,
        "incomplete_2026_excluded_from_training": True,
        "forecast_labels_available": False,
        "source_gate": {
            "pure_iTE_only": True,
            "eligible_claim_only": True,
            "core_iTE_scope_only": True,
            "direct_evidence_tiers": [
                "A_direct_evidence_ready",
                "B_direct_needs_evidence_repair",
            ],
            "explicit_TG_or_redox_source_excluded": True,
            "strict_claim_level_mechanism_match": True,
            "minimum_independent_papers": MIN_SOURCE_PAPERS,
        },
        "target_gate": {
            "review_excluded": True,
            "lever_match_fields": ["material_raw", "mechanism_raw"],
            "strict_lever_patterns": True,
            "multi_redox_family_per_paper_allowed": True,
            "minimum_independent_TG_papers": MIN_TARGET_PAPERS,
        },
        "label": (
            "first composite transfer-proxy edge in cutoff+1: strict TG "
            "mechanism/redox rule or manually audited direct prior"
        ),
        "selected_model": selected_model,
        "selected_model_label": MODEL_LABELS[selected_model],
        "selection_cutoffs": selection_cutoffs,
        "locked_holdout_cutoff": holdout_cutoff,
        "locked_holdout_outcome_year": 2025,
        "locked_holdout_metrics": {
            key: (
                int(holdout[key])
                if key in {"n_candidates", "n_positive", "hits_at_5", "hits_at_10"}
                else float(holdout[key])
            )
            for key in [
                "n_candidates",
                "n_positive",
                "positive_rate",
                "average_precision",
                "roc_auc",
                "precision_at_5",
                "hits_at_5",
                "precision_at_10",
                "hits_at_10",
                "ndcg_at_10",
                "ap_lift_over_prevalence",
            ]
        },
        "locked_holdout_popularity_baseline": {
            "average_precision": float(
                holdout_popularity["average_precision"]
            ),
            "precision_at_5": float(holdout_popularity["precision_at_5"]),
            "ndcg_at_10": float(holdout_popularity["ndcg_at_10"]),
        },
        "counts": {
            "lever_count": len(GRAPH_LEVER_LABELS_CN),
            "target_family_count": len(TARGET_ORDER),
            "matrix_cells": int(len(matrix)),
            "forecast_candidates": int(
                matrix["cell_state"].eq("forecast_candidate").sum()
            ),
            "observed_cells": int(
                matrix["cell_state"].str.startswith("observed").sum()
            ),
            "unscored_cells": int(
                (~matrix["cell_state"].eq("forecast_candidate") & ~matrix["cell_state"].str.startswith("observed")).sum()
            ),
            "qualified_pure_iTE_source_papers": int(
                source_records["paper_id"].nunique()
            ),
            "strict_TG_event_papers": int(
                strict_adoption_evidence.loc[
                    strict_adoption_evidence["event_eligible"], "paper_id"
                ].nunique()
            ),
            "manual_prior_event_papers": int(
                manual_adoption_evidence.loc[
                    manual_adoption_evidence["event_eligible"], "paper_id"
                ].nunique()
            ),
            "composite_event_papers": int(
                adoption_evidence.loc[
                    adoption_evidence["event_eligible"], "paper_id"
                ].nunique()
            ),
        },
        "label_policy": {
            "experimental_success_target": False,
            "program_edges_used": False,
            "manual_direct_prior_evidence_used": True,
            "priority_score_used": False,
            "semantic_similarity_used": False,
            "missing_edges_called_true_negatives": False,
            "output_is_calibrated_probability": False,
        },
        "output_rows": {
            "ite_source_lever_records.csv": int(len(source_records)),
            "strict_tg_lever_adoption_evidence.csv": int(
                len(strict_adoption_evidence)
            ),
            "manual_prior_adoption_evidence.csv": int(
                len(manual_adoption_evidence)
            ),
            "tg_lever_adoption_evidence.csv": int(len(adoption_evidence)),
            "temporal_risk_snapshots.csv": int(len(all_snapshots)),
            "future_lever_tg_predictions.csv": int(len(forecast)),
            "lever_tg_prediction_matrix_long.csv": int(len(matrix)),
        },
        "input_sha256": {path.name: sha256_file(path) for path in input_paths},
        "output_sha256": {path.name: sha256_file(path) for path in output_paths},
    }
    write_json(output_dir / "prediction_manifest.json", manifest)
    print(
        json.dumps(
            {
                "selected_model": selected_model,
                "holdout_AP": manifest["locked_holdout_metrics"][
                    "average_precision"
                ],
                "holdout_prevalence": manifest["locked_holdout_metrics"][
                    "positive_rate"
                ],
                **manifest["counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
