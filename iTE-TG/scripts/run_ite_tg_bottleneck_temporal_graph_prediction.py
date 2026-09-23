#!/usr/bin/env python3
"""Temporal graph pilot for iTE mechanism -> TG bottleneck adoption.

This is deliberately separate from the legacy mechanism x redox-family model.
Redox chemistry is retained only as paper context.  The prediction target is
the first qualifying TG paper that connects a transferable iTE mechanism to a
specific TG bottleneck.  Scores rank literature-adoption opportunities; they
are not calibrated experimental-success probabilities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations, product
from pathlib import Path
from typing import Any, Iterable

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from run_ite_tg_complementarity import normalize_space
from run_ite_tg_temporal_graph_prediction import (
    GRAPH_LEVER_LABELS_CN,
    STRICT_LEVER_PATTERNS,
    build_source_records,
    is_review,
    load_data,
    strict_target_family_hits,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "ite_tg_complementarity"
DEFAULT_OUTPUT = DEFAULT_INPUT / "bottleneck_graph_prediction"
DEFAULT_PAPER_INDEX = ROOT / "final_concept_layer" / "final_paper_index.csv"
DEFAULT_TG_CLAIMS = ROOT / "ite_insight_transfer" / "tg_reference_claim_units.csv"
FORECAST_CUTOFF = 2025
MIN_SOURCE_PAPERS = 2
MIN_BOTTLENECK_PAPERS = 2
RANDOM_STATE = 73


BOTTLENECK_ORDER = [
    "thermodynamic_voltage",
    "mass_transport_selectivity",
    "kinetics_internal_resistance",
    "mechano_transport_tradeoff",
    "operational_stability",
    "thermal_device_utilization",
]

BOTTLENECK_LABELS_CN = {
    "thermodynamic_voltage": "热力学电压/极性",
    "mass_transport_selectivity": "传质与物种选择性",
    "kinetics_internal_resistance": "动力学与内阻",
    "mechano_transport_tradeoff": "力学–传输兼容",
    "operational_stability": "环境与运行稳定性",
    "thermal_device_utilization": "温差与器件利用",
}

# These patterns identify a *specific bottleneck mechanism* in the curated
# mechanism statement.  Generic words such as power, Seebeck, wearable,
# electrode, or stable are intentionally excluded from this first gate.
BOTTLENECK_PATTERNS: dict[str, re.Pattern[str]] = {
    "thermodynamic_voltage": re.compile(
        r"redox (?:reaction )?entropy|entropy (?:difference|change)|"
        r"solvation entropy|configurational entropy|activity coefficient|"
        r"redox potential|Nernst|solvation shell|selective solvation|"
        r"solvation structure|hydration shell|hydrogen bond(?:ing)?|"
        r"temperature[- ]dependent (?:binding|equilibrium|complexation)|"
        r"thermodynamic equilibrium|proton activity|pH[- ](?:dependent|"
        r"responsive|gradient)|protonat|speciation",
        re.I,
    ),
    "mass_transport_selectivity": re.compile(
        r"mass transport|redox (?:ion|species) transport|diffusion|diffusivity|"
        r"convection|concentration polarization|concentration gradient|"
        r"crossover|shuttle|permeab|selective (?:transport|membrane|capture|"
        r"binding)|ion[- ]selectiv|limiting current|transport pathway|"
        r"nanochannel|nanopore|confined ion transport|thermodiffusion|Soret",
        re.I,
    ),
    "kinetics_internal_resistance": re.compile(
        r"charge[- ]transfer|redox kinetics|reaction kinetics|exchange current|"
        r"electrocatal|overpotential|interfacial (?:resistance|kinetics|charge)|"
        r"internal resistance|solution resistance|diffusion resistance|"
        r"impedance|\bRct\b|porous electrode|electrode architecture|"
        r"electron(?:ic)? transport|ionic conductivity|electronic conductivity",
        re.I,
    ),
    "mechano_transport_tradeoff": re.compile(
        r"mechanical (?:strength|robustness|properties|toughness)|"
        r"mutually exclusive|toughness|stretchability|fracture|fatigue "
        r"(?:resistance|life|cycles)|self[- ]healing|crack resistance|"
        r"deformation[- ]stable|mechanically robust|double[- ]network|"
        r"interpenetrating network|dynamic crosslink|mechanical lifetime",
        re.I,
    ),
    "operational_stability": re.compile(
        r"anti[- ]?freez|non[- ]?freez|subzero|low[- ]temperature operation|"
        r"wide[- ]temperature|non[- ]?drying|anti[- ]?drying|dehydration|"
        r"water retention|low volatility|nonvolatile|evaporation loss|"
        r"cycling stability|cycle life|long[- ]term stability|chemical stability|"
        r"output retention|power retention|leakage prevention|all[- ]weather",
        re.I,
    ),
    "thermal_device_utilization": re.compile(
        r"thermal management|thermal resistance|heat localization|heat flux|"
        r"photothermal|solar[- ]thermal|radiative cooling|evaporative cooling|"
        r"self[- ]supplying temperature difference|maintain(?:s|ing)? (?:the )?"
        r"temperature gradient|continuous (?:power|output|operation|electricity)|"
        r"regeneration|self[- ]cycling|series[- ]connect|module voltage|"
        r"device architecture|net energy|electrochemical refrigeration",
        re.I,
    ),
}


OUTCOME_PATTERNS: dict[str, re.Pattern[str]] = {
    "thermodynamic_voltage": re.compile(
        r"(?:mV|uV|µV|μV)\s*(?:K|K-1|K\^-1)|temperature coefficient|"
        r"Seebeck coefficient|thermopower|thermovoltage|open[- ]circuit voltage|"
        r"redox entropy|entropy change|p[- ]type|n[- ]type|polarity",
        re.I,
    ),
    "mass_transport_selectivity": re.compile(
        r"diffusion coefficient|diffusivity|mass[- ]transfer coefficient|"
        r"limiting current|steady[- ]state current|flux|permeability|crossover|"
        r"concentration profile|ionic conductivity|transport resistance|"
        r"concentration gradient",
        re.I,
    ),
    "kinetics_internal_resistance": re.compile(
        r"charge[- ]transfer resistance|\bRct\b|impedance|EIS|exchange current|"
        r"overpotential|reaction rate|redox kinetics|internal resistance|"
        r"current density|power density|ionic conductivity|electronic conductivity",
        re.I,
    ),
    "mechano_transport_tradeoff": re.compile(
        r"(?:MPa|kPa|MJ\s*m|%\s*(?:strain|elongation)|toughness|strength|"
        r"modulus|elongation|healing efficiency|fatigue cycles|power retention|"
        r"conductivity|diffusion|resistance)",
        re.I,
    ),
    "operational_stability": re.compile(
        r"-?\d+(?:\.\d+)?\s*(?:degrees?\s*C|°C|days?|hours?|cycles?)|"
        r"temperature range|retention|no (?:obvious )?degradation|anti[- ]?freez|"
        r"non[- ]?drying|water retention|mass loss|cycle life|long[- ]term|"
        r"wide temperature|all[- ]weather",
        re.I,
    ),
    "thermal_device_utilization": re.compile(
        r"temperature difference|\bdelta\s*T\b|ΔT|heat flux|thermal resistance|"
        r"continuous(?:ly)?|net energy|energy density|power density|efficiency|"
        r"module voltage|cooling power|coefficient of performance|COP|"
        r"regeneration",
        re.I,
    ),
}

# A bottleneck may be expressed by the measured consequence rather than by the
# word "bottleneck" in the normalized mechanism sentence.  These inference
# rules are intentionally narrower than OUTCOME_PATTERNS.  Inference is only
# accepted when the paper also has a causal mechanism sentence containing the
# transferable lever.
INFERRED_BOTTLENECK_PATTERNS: dict[str, re.Pattern[str]] = {
    "thermodynamic_voltage": re.compile(
        r"(?:mV|uV|µV|μV)\s*(?:K|K-1|K\^-1)|temperature coefficient|"
        r"Seebeck coefficient|thermopower|thermovoltage|redox entropy|"
        r"p[- ]type|n[- ]type|polarity",
        re.I,
    ),
    "mass_transport_selectivity": re.compile(
        r"diffusion coefficient|diffusivity|mass[- ]transfer coefficient|"
        r"limiting current|steady[- ]state current|\bflux\b|permeability|"
        r"crossover|concentration profile|transport resistance",
        re.I,
    ),
    "kinetics_internal_resistance": re.compile(
        r"charge[- ]transfer resistance|\bRct\b|impedance|\bEIS\b|"
        r"exchange current|overpotential|redox kinetics|internal resistance",
        re.I,
    ),
    "mechano_transport_tradeoff": re.compile(
        r"(?:MPa|MJ\s*m|toughness|mechanical strength|elongation|"
        r"healing efficiency|fatigue cycles).*(?:conductivity|diffusion|"
        r"resistance|power|thermopower)|(?:conductivity|diffusion|resistance|"
        r"power|thermopower).*(?:MPa|MJ\s*m|toughness|mechanical strength|"
        r"elongation|healing efficiency|fatigue cycles)",
        re.I,
    ),
    "operational_stability": re.compile(
        r"-?\d+(?:\.\d+)?\s*(?:degrees?\s*C|°C).*(?:conduct|power|output|"
        r"thermoelectric)|(?:conduct|power|output|thermoelectric).*"
        r"-?\d+(?:\.\d+)?\s*(?:degrees?\s*C|°C)|"
        r"(?:days?|hours?|cycles?).*(?:retention|degradation|stable)|"
        r"(?:retention|degradation|stable).*(?:days?|hours?|cycles?)|"
        r"anti[- ]?freez|non[- ]?drying|water retention|mass loss|all[- ]weather",
        re.I,
    ),
    "thermal_device_utilization": re.compile(
        r"self[- ]supplying temperature difference|maintain(?:s|ing)? (?:the )?"
        r"temperature gradient|heat flux|thermal resistance|radiative cooling|"
        r"evaporative cooling|continuous(?:ly)? (?:generate|output|operate|"
        r"electricity|power)|net energy|module voltage|cooling power|"
        r"coefficient of performance|regeneration efficiency",
        re.I,
    ),
}


OFF_DOMAIN_RE = re.compile(
    r"thermal runaway|lithium[- ]ion batter|corrosion rate|magnetic field "
    r"corrosion|solid[- ]state thermoelectric|electronic thermoelectric",
    re.I,
)
THEORY_RE = re.compile(
    r"\b(theoretical|numerical|simulation|computational|sensitivity analysis|"
    r"modeling study|modelling study)\b",
    re.I,
)
TG_DOMAIN_RE = re.compile(
    r"thermogalvanic|thermocell|thermoelectrochem|thermal[- ]to[- ]electric "
    r"converter|temperature gradient.*redox|redox.*temperature gradient|"
    r"electrochemical refrigeration",
    re.I,
)


MODEL_FEATURES = [
    "ll_bridge_score",
    "bb_bridge_score",
    "redox_bridge_count",
    "inverse_shortest_path",
    "lever_prior_bottleneck_degree",
    "bottleneck_prior_lever_degree",
    "ite_source_papers_log",
    "ite_recent_papers_log",
    "tg_recent_papers_log",
]

MODEL_ORDER = ["degree_recency_baseline", "fixed_graph", "graph_logistic"]
MODEL_LABELS = {
    "degree_recency_baseline": "Degree+recency",
    "fixed_graph": "Fixed graph",
    "graph_logistic": "Graph logistic",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--paper-index", type=Path, default=DEFAULT_PAPER_INDEX)
    parser.add_argument("--tg-claims", type=Path, default=DEFAULT_TG_CLAIMS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--forecast-cutoff", type=int, default=FORECAST_CUTOFF)
    return parser.parse_args()


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return normalize_space(value).lower() in {"1", "true", "yes", "y"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def matched_terms(pattern: re.Pattern[str], text: str) -> list[str]:
    return sorted({m.group(0) for m in pattern.finditer(text)}, key=str.lower)


def stable_join(values: Iterable[Any]) -> str:
    cleaned = {normalize_space(value) for value in values if normalize_space(value)}
    return "; ".join(sorted(cleaned))


def redox_contexts(row: pd.Series) -> list[str]:
    proxy = pd.Series(
        {
            "title": row.get("title", ""),
            "material_raw": row.get("material_raw", ""),
            "mechanism_raw": row.get("mechanism_raw_full", row.get("mechanism_raw", "")),
        }
    )
    contexts = sorted(strict_target_family_hits(proxy))
    return contexts or ["unspecified_or_other"]


def load_claims(path: Path, cutoff: int) -> pd.DataFrame:
    claims = pd.read_csv(path)
    required = {
        "paper_id",
        "year",
        "title",
        "abstract",
        "material_raw",
        "mechanism_raw_full",
        "insight_claim",
        "mechanism_evidence_sentence",
        "outcome_evidence_sentence",
        "likely_review",
        "selected_outcome_has_quantitative_detail",
        "abstract_contains_causal_cue",
    }
    missing = sorted(required - set(claims.columns))
    if missing:
        raise ValueError(f"TG claim table missing columns: {missing}")
    claims["year"] = pd.to_numeric(claims["year"], errors="coerce")
    return claims[claims["year"].le(cutoff)].copy()


def claim_domain_flags(row: pd.Series) -> tuple[bool, bool, bool]:
    text = " ".join(
        normalize_space(row.get(field, ""))
        for field in ["title", "abstract", "mechanism_raw_full", "insight_claim"]
    )
    review = boolish(row.get("likely_review")) or is_review(
        pd.Series({"title": row.get("title", ""), "abstract": row.get("abstract", "")})
    )
    domain = bool(TG_DOMAIN_RE.search(text)) and not bool(OFF_DOMAIN_RE.search(text))
    theory_only = bool(THEORY_RE.search(normalize_space(row.get("title", "")))) and not (
        boolish(row.get("selected_outcome_has_quantitative_detail"))
        and boolish(row.get("abstract_contains_causal_cue"))
    )
    return review, domain, theory_only


def build_tg_bottleneck_evidence(
    claims: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    evidence_rows: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    bottleneck_paper_rows: list[dict[str, Any]] = []

    for _, row in claims.iterrows():
        review, domain, theory_only = claim_domain_flags(row)
        mechanism_sentence = normalize_space(row.get("mechanism_evidence_sentence", ""))
        mechanism_full = normalize_space(row.get("mechanism_raw_full", ""))
        claim_text = normalize_space(row.get("insight_claim", ""))
        mechanism_text = " ".join(
            text for text in [mechanism_sentence, mechanism_full, claim_text] if text
        )
        outcome_text = " ".join(
            [
                normalize_space(row.get("outcome_evidence_sentence", "")),
                normalize_space(row.get("abstract", "")),
                mechanism_sentence,
            ]
        )
        lever_hits = {
            code: matched_terms(pattern, mechanism_text)
            for code, pattern in STRICT_LEVER_PATTERNS.items()
            if pattern.search(mechanism_text)
        }
        bottleneck_hits: dict[str, list[str]] = {}
        bottleneck_inferred: dict[str, bool] = {}
        for code, pattern in BOTTLENECK_PATTERNS.items():
            seed_terms = matched_terms(pattern, mechanism_text)
            inferred_terms = matched_terms(
                INFERRED_BOTTLENECK_PATTERNS[code], outcome_text
            )
            if not seed_terms and not inferred_terms:
                continue
            bottleneck_hits[code] = seed_terms or inferred_terms
            bottleneck_inferred[code] = bool(not seed_terms and inferred_terms)
        redox = redox_contexts(row)

        for bottleneck_code, terms in bottleneck_hits.items():
            out_terms = matched_terms(OUTCOME_PATTERNS[bottleneck_code], outcome_text)
            if not out_terms:
                continue
            bottleneck_paper_rows.append(
                {
                    "paper_id": row["paper_id"],
                    "year": int(row["year"]),
                    "bottleneck_code": bottleneck_code,
                    "bottleneck_label_cn": BOTTLENECK_LABELS_CN[bottleneck_code],
                    "redox_contexts": "; ".join(redox),
                    "bottleneck_terms": "; ".join(terms),
                    "outcome_terms": "; ".join(out_terms),
                    "bottleneck_inferred_from_outcome": bottleneck_inferred[
                        bottleneck_code
                    ],
                    "eligible_primary_TG": bool(not review and domain and not theory_only),
                }
            )
            for lever_code, lever_terms in lever_hits.items():
                quantitative = boolish(
                    row.get("selected_outcome_has_quantitative_detail")
                )
                causal = boolish(row.get("abstract_contains_causal_cue"))
                if quantitative and causal:
                    tier = "A_quantitative_improvement"
                elif causal:
                    tier = "B_directional_adoption"
                else:
                    tier = "C_text_proxy"
                eligible = bool(
                    not review
                    and domain
                    and not theory_only
                    and tier in {"A_quantitative_improvement", "B_directional_adoption"}
                )
                evidence_rows.append(
                    {
                        "paper_id": row["paper_id"],
                        "year": int(row["year"]),
                        "title": row.get("title", ""),
                        "doi": row.get("doi", ""),
                        "lever_code": lever_code,
                        "lever_label_cn": GRAPH_LEVER_LABELS_CN.get(lever_code, lever_code),
                        "bottleneck_code": bottleneck_code,
                        "bottleneck_label_cn": BOTTLENECK_LABELS_CN[bottleneck_code],
                        "redox_contexts": "; ".join(redox),
                        "lever_terms": "; ".join(lever_terms),
                        "bottleneck_terms": "; ".join(terms),
                        "outcome_terms": "; ".join(out_terms),
                        "bottleneck_inferred_from_outcome": bottleneck_inferred[
                            bottleneck_code
                        ],
                        "mechanism_evidence_span": mechanism_sentence or mechanism_full,
                        "outcome_evidence_span": normalize_space(
                            row.get("outcome_evidence_sentence", "")
                        ),
                        "event_tier": tier,
                        "likely_review": review,
                        "tg_domain_flag": domain,
                        "theory_only_flag": theory_only,
                        "event_eligible": eligible,
                    }
                )

        mapping_rows.append(
            {
                "paper_id": row["paper_id"],
                "year": int(row["year"]),
                "title": row.get("title", ""),
                "likely_review": review,
                "tg_domain_flag": domain,
                "theory_only_flag": theory_only,
                "lever_codes": "; ".join(sorted(lever_hits)),
                "bottleneck_codes": "; ".join(sorted(bottleneck_hits)),
                "redox_contexts": "; ".join(redox),
            }
        )

    evidence = pd.DataFrame(evidence_rows)
    if not evidence.empty:
        evidence = (
            evidence.sort_values(
                ["year", "paper_id", "lever_code", "bottleneck_code", "event_tier"]
            )
            .drop_duplicates(["paper_id", "lever_code", "bottleneck_code"], keep="first")
            .reset_index(drop=True)
        )
    bottleneck_papers = pd.DataFrame(bottleneck_paper_rows)
    if not bottleneck_papers.empty:
        bottleneck_papers = (
            bottleneck_papers.sort_values(["year", "paper_id", "bottleneck_code"])
            .drop_duplicates(["paper_id", "bottleneck_code"])
            .reset_index(drop=True)
        )
    mapping = pd.DataFrame(mapping_rows).drop_duplicates("paper_id")
    return evidence, bottleneck_papers, mapping


def first_event_lookup(evidence: pd.DataFrame) -> dict[tuple[str, str], int]:
    eligible = evidence[evidence["event_eligible"]].copy()
    return {
        (lever, bottleneck): int(year)
        for (lever, bottleneck), year in eligible.groupby(
            ["lever_code", "bottleneck_code"]
        )["year"].min().items()
    }


def rank01(values: pd.Series | np.ndarray) -> np.ndarray:
    series = pd.Series(values, dtype=float)
    if len(series) <= 1:
        return np.zeros(len(series), dtype=float)
    return ((series.rank(method="average") - 1) / (len(series) - 1)).to_numpy()


def normalized_pair_weight(count: float, left_total: float, right_total: float) -> float:
    return float(count / math.sqrt(max(1.0, left_total * right_total)))


def build_snapshot(
    cutoff: int,
    observed_through: int,
    source_records: pd.DataFrame,
    evidence: pd.DataFrame,
    bottleneck_papers: pd.DataFrame,
    first_event: dict[tuple[str, str], int],
) -> pd.DataFrame:
    source_hist = source_records[source_records["year"].le(cutoff)].copy()
    source_counts = source_hist.groupby("lever_code")["paper_id"].nunique()
    eligible_levers = sorted(source_counts[source_counts.ge(MIN_SOURCE_PAPERS)].index)

    bp_hist = bottleneck_papers[
        bottleneck_papers["year"].le(cutoff)
        & bottleneck_papers["eligible_primary_TG"]
    ].copy()
    b_counts = bp_hist.groupby("bottleneck_code")["paper_id"].nunique()
    eligible_bottlenecks = [
        code
        for code in BOTTLENECK_ORDER
        if int(b_counts.get(code, 0)) >= MIN_BOTTLENECK_PAPERS
    ]
    event_hist = evidence[
        evidence["event_eligible"] & evidence["year"].le(cutoff)
    ].copy()

    source_by_paper = (
        source_hist[source_hist["lever_code"].isin(eligible_levers)]
        .groupby("paper_id")["lever_code"]
        .agg(lambda x: sorted(set(x)))
    )
    ll_counts: Counter[tuple[str, str]] = Counter()
    lever_doc_counts = Counter()
    for codes in source_by_paper:
        for code in codes:
            lever_doc_counts[code] += 1
        for left, right in combinations(codes, 2):
            ll_counts[tuple(sorted((left, right)))] += 1

    b_by_paper = (
        bp_hist[bp_hist["bottleneck_code"].isin(eligible_bottlenecks)]
        .groupby("paper_id")["bottleneck_code"]
        .agg(lambda x: sorted(set(x)))
    )
    bb_counts: Counter[tuple[str, str]] = Counter()
    bottleneck_doc_counts = Counter()
    for codes in b_by_paper:
        for code in codes:
            bottleneck_doc_counts[code] += 1
        for left, right in combinations(codes, 2):
            bb_counts[tuple(sorted((left, right)))] += 1

    adoption_counts = event_hist.groupby(["lever_code", "bottleneck_code"])[
        "paper_id"
    ].nunique()
    lever_to_b: dict[str, set[str]] = defaultdict(set)
    b_to_lever: dict[str, set[str]] = defaultdict(set)
    for (lever, bottleneck), count in adoption_counts.items():
        if count and lever in eligible_levers and bottleneck in eligible_bottlenecks:
            lever_to_b[lever].add(bottleneck)
            b_to_lever[bottleneck].add(lever)

    graph = nx.Graph()
    graph.add_nodes_from(f"M:{x}" for x in eligible_levers)
    graph.add_nodes_from(f"B:{x}" for x in eligible_bottlenecks)
    for (left, right), count in ll_counts.items():
        weight = normalized_pair_weight(
            count, lever_doc_counts[left], lever_doc_counts[right]
        )
        graph.add_edge(f"M:{left}", f"M:{right}", weight=weight, edge_type="MM")
    for (left, right), count in bb_counts.items():
        weight = normalized_pair_weight(
            count, bottleneck_doc_counts[left], bottleneck_doc_counts[right]
        )
        graph.add_edge(f"B:{left}", f"B:{right}", weight=weight, edge_type="BB")
    for (lever, bottleneck), count in adoption_counts.items():
        if lever in eligible_levers and bottleneck in eligible_bottlenecks:
            graph.add_edge(
                f"M:{lever}",
                f"B:{bottleneck}",
                weight=float(math.log1p(count)),
                edge_type="MB",
            )

    source_recent = (
        source_hist[source_hist["year"].between(cutoff - 2, cutoff)]
        .groupby("lever_code")["paper_id"]
        .nunique()
    )
    b_recent = (
        bp_hist[bp_hist["year"].between(cutoff - 2, cutoff)]
        .groupby("bottleneck_code")["paper_id"]
        .nunique()
    )
    lever_redox: dict[str, set[str]] = defaultdict(set)
    bottleneck_redox: dict[str, set[str]] = defaultdict(set)
    for row in event_hist.itertuples(index=False):
        contexts = {x.strip() for x in str(row.redox_contexts).split(";") if x.strip()}
        lever_redox[row.lever_code].update(contexts)
        bottleneck_redox[row.bottleneck_code].update(contexts)

    rows: list[dict[str, Any]] = []
    for lever, bottleneck in product(eligible_levers, eligible_bottlenecks):
        first_year = first_event.get((lever, bottleneck))
        if first_year is not None and first_year <= cutoff:
            continue

        ll_bridge = 0.0
        ll_bridge_codes: list[str] = []
        for other in b_to_lever.get(bottleneck, set()):
            key = tuple(sorted((lever, other)))
            count = ll_counts.get(key, 0)
            if count:
                value = normalized_pair_weight(
                    count, lever_doc_counts[lever], lever_doc_counts[other]
                )
                ll_bridge += value
                ll_bridge_codes.append(other)

        bb_bridge = 0.0
        bb_bridge_codes: list[str] = []
        for other in lever_to_b.get(lever, set()):
            key = tuple(sorted((bottleneck, other)))
            count = bb_counts.get(key, 0)
            if count:
                value = normalized_pair_weight(
                    count,
                    bottleneck_doc_counts[bottleneck],
                    bottleneck_doc_counts[other],
                )
                bb_bridge += value
                bb_bridge_codes.append(other)

        left, right = f"M:{lever}", f"B:{bottleneck}"
        try:
            shortest = nx.shortest_path_length(graph, left, right)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            shortest = 9
        redox_common = lever_redox.get(lever, set()) & bottleneck_redox.get(
            bottleneck, set()
        )
        source_n = int(source_counts.get(lever, 0))
        b_n = int(b_counts.get(bottleneck, 0))
        source_recent_n = int(source_recent.get(lever, 0))
        b_recent_n = int(b_recent.get(bottleneck, 0))
        l_degree = len(lever_to_b.get(lever, set()))
        b_degree = len(b_to_lever.get(bottleneck, set()))
        rows.append(
            {
                "pair_id": f"{lever}|{bottleneck}",
                "cutoff_year": cutoff,
                "outcome_year": cutoff + 1,
                "lever_code": lever,
                "lever_label_cn": GRAPH_LEVER_LABELS_CN.get(lever, lever),
                "bottleneck_code": bottleneck,
                "bottleneck_label_cn": BOTTLENECK_LABELS_CN[bottleneck],
                "future_event_label": (
                    int(first_year == cutoff + 1)
                    if cutoff + 1 <= observed_through
                    else np.nan
                ),
                "first_event_year": first_year if first_year is not None else np.nan,
                "ll_bridge_score": ll_bridge,
                "bb_bridge_score": bb_bridge,
                "ll_bridge_codes": "; ".join(sorted(ll_bridge_codes)),
                "bb_bridge_codes": "; ".join(sorted(bb_bridge_codes)),
                "redox_bridge_count": len(redox_common),
                "redox_bridge_contexts": "; ".join(sorted(redox_common)),
                "shortest_path": shortest,
                "inverse_shortest_path": 1.0 / (1.0 + shortest),
                "lever_prior_bottleneck_degree": l_degree,
                "bottleneck_prior_lever_degree": b_degree,
                "ite_source_papers": source_n,
                "ite_recent_papers": source_recent_n,
                "tg_bottleneck_papers": b_n,
                "tg_recent_papers": b_recent_n,
                "ite_source_papers_log": math.log1p(source_n),
                "ite_recent_papers_log": math.log1p(source_recent_n),
                "tg_bottleneck_papers_log": math.log1p(b_n),
                "tg_recent_papers_log": math.log1p(b_recent_n),
                "preferential_attachment_log": math.log1p(l_degree * b_degree),
                "feature_max_year": cutoff,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["degree_recency_baseline"] = (
        0.40 * rank01(frame["preferential_attachment_log"])
        + 0.20 * rank01(frame["ite_recent_papers_log"])
        + 0.20 * rank01(frame["tg_recent_papers_log"])
        + 0.10 * rank01(frame["ite_source_papers_log"])
        + 0.10 * rank01(frame["tg_bottleneck_papers_log"])
    )
    frame["fixed_graph"] = (
        0.30 * rank01(frame["ll_bridge_score"])
        + 0.22 * rank01(frame["bb_bridge_score"])
        + 0.14 * rank01(frame["redox_bridge_count"])
        + 0.12 * rank01(frame["inverse_shortest_path"])
        + 0.08 * rank01(frame["ite_recent_papers_log"])
        + 0.06 * rank01(frame["tg_recent_papers_log"])
        + 0.05 * rank01(frame["ite_source_papers_log"])
        + 0.03 * rank01(frame["preferential_attachment_log"])
    )
    return frame.sort_values("pair_id").reset_index(drop=True)


def pair_block_weights(train: pd.DataFrame) -> np.ndarray:
    repeats = train.groupby("pair_id")["pair_id"].transform("count")
    values = 1.0 / repeats.to_numpy(dtype=float)
    return values * len(values) / values.sum()


def score_model(model_name: str, train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    if model_name in {"degree_recency_baseline", "fixed_graph"}:
        return test[model_name].to_numpy(dtype=float)
    if train.empty or train["future_event_label"].nunique() < 2:
        return test["fixed_graph"].to_numpy(dtype=float)
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=0.25,
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    model.fit(
        train[MODEL_FEATURES].fillna(0),
        train["future_event_label"].astype(int),
        model__sample_weight=pair_block_weights(train),
    )
    return model.predict_proba(test[MODEL_FEATURES].fillna(0))[:, 1]


def stable_order(frame: pd.DataFrame, score: np.ndarray) -> np.ndarray:
    helper = pd.DataFrame({"score": score, "pair_id": frame["pair_id"].astype(str)})
    return helper.sort_values(["score", "pair_id"], ascending=[False, True]).index.to_numpy()


def topk_stats(frame: pd.DataFrame, score: np.ndarray, k: int) -> tuple[float, float, float]:
    if len(frame) < k:
        return float("nan"), float("nan"), float("nan")
    y = frame["future_event_label"].astype(int).to_numpy()
    order = stable_order(frame.reset_index(drop=True), score)[:k]
    hits = float(y[order].sum())
    recall = hits / y.sum() if y.sum() else float("nan")
    return hits / k, hits, recall


def ndcg_at(frame: pd.DataFrame, score: np.ndarray, k: int) -> float:
    if len(frame) < k:
        return float("nan")
    y = frame["future_event_label"].astype(int).to_numpy()
    order = stable_order(frame.reset_index(drop=True), score)[:k]
    gains = y[order]
    discounts = 1.0 / np.log2(np.arange(2, k + 2))
    dcg = float(np.sum(gains * discounts))
    ideal = np.sort(y)[::-1][:k]
    idcg = float(np.sum(ideal * discounts))
    return dcg / idcg if idcg else 0.0


def metric_row(frame: pd.DataFrame, score: np.ndarray, model_name: str) -> dict[str, Any]:
    y = frame["future_event_label"].astype(int).to_numpy()
    result: dict[str, Any] = {
        "test_cutoff": int(frame["cutoff_year"].iloc[0]),
        "outcome_year": int(frame["outcome_year"].iloc[0]),
        "model": model_name,
        "model_label": MODEL_LABELS[model_name],
        "n_candidates": len(frame),
        "n_positive": int(y.sum()),
        "positive_rate": float(y.mean()),
        "average_precision": float(average_precision_score(y, score)) if y.sum() else np.nan,
        "roc_auc": float(roc_auc_score(y, score)) if 0 < y.sum() < len(y) else np.nan,
    }
    for k in [5, 10, 25]:
        precision, hits, recall = topk_stats(frame, score, k)
        result[f"precision_at_{k}"] = precision
        result[f"hits_at_{k}"] = hits
        result[f"recall_at_{k}"] = recall
    result["ndcg_at_10"] = ndcg_at(frame, score, 10)
    result["ndcg_at_25"] = ndcg_at(frame, score, 25)
    return result


def run_backtest(
    snapshots: dict[int, pd.DataFrame], report_cutoffs: list[int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics: list[dict[str, Any]] = []
    predictions: list[pd.DataFrame] = []
    for cutoff in report_cutoffs:
        test = snapshots[cutoff].reset_index(drop=True)
        train_parts = [x for year, x in snapshots.items() if year < cutoff]
        train = pd.concat(train_parts, ignore_index=True) if train_parts else pd.DataFrame()
        for model_name in MODEL_ORDER:
            score = score_model(model_name, train, test)
            metrics.append(metric_row(test, score, model_name))
            out = test[
                [
                    "pair_id",
                    "cutoff_year",
                    "outcome_year",
                    "lever_code",
                    "lever_label_cn",
                    "bottleneck_code",
                    "bottleneck_label_cn",
                    "future_event_label",
                ]
            ].copy()
            out["model"] = model_name
            out["raw_score"] = score
            out["rank_score_0_100"] = 100 * rank01(score)
            predictions.append(out)
    return pd.DataFrame(metrics), pd.concat(predictions, ignore_index=True)


def select_graph_model(metrics: pd.DataFrame) -> str:
    early = metrics[metrics["test_cutoff"].lt(2022)]
    graph_only = early[early["model"].isin(["fixed_graph", "graph_logistic"])]
    if graph_only.empty or graph_only["average_precision"].dropna().empty:
        return "fixed_graph"
    return (
        graph_only.groupby("model")["average_precision"]
        .mean()
        .sort_values(ascending=False)
        .index[0]
    )


def final_forecast(
    snapshots: dict[int, pd.DataFrame], cutoff: int, graph_model: str
) -> pd.DataFrame:
    test = snapshots[cutoff].reset_index(drop=True)
    train = pd.concat(
        [x for year, x in snapshots.items() if year < cutoff], ignore_index=True
    )
    graph_score = score_model(graph_model, train, test)
    baseline_score = score_model("degree_recency_baseline", train, test)
    test["graph_model"] = graph_model
    test["graph_model_label"] = MODEL_LABELS[graph_model]
    test["graph_raw_score"] = graph_score
    test["graph_rank_score_0_100"] = 100 * rank01(graph_score)
    test["baseline_raw_score"] = baseline_score
    test["baseline_rank_score_0_100"] = 100 * rank01(baseline_score)
    test = test.sort_values(
        ["graph_raw_score", "pair_id"], ascending=[False, True]
    ).reset_index(drop=True)
    test["graph_forecast_rank"] = np.arange(1, len(test) + 1)
    return test


def build_matrix(
    forecast: pd.DataFrame,
    source_records: pd.DataFrame,
    bottleneck_papers: pd.DataFrame,
    first_event: dict[tuple[str, str], int],
    cutoff: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    source_counts = (
        source_records[source_records["year"].le(cutoff)]
        .groupby("lever_code")["paper_id"]
        .nunique()
        .to_dict()
    )
    b_counts = (
        bottleneck_papers[
            bottleneck_papers["year"].le(cutoff)
            & bottleneck_papers["eligible_primary_TG"]
        ]
        .groupby("bottleneck_code")["paper_id"]
        .nunique()
        .to_dict()
    )
    lookup = forecast.set_index(["lever_code", "bottleneck_code"]).to_dict("index")
    rows: list[dict[str, Any]] = []
    for lever, bottleneck in product(GRAPH_LEVER_LABELS_CN, BOTTLENECK_ORDER):
        source_n = int(source_counts.get(lever, 0))
        b_n = int(b_counts.get(bottleneck, 0))
        observed = first_event.get((lever, bottleneck))
        pred = lookup.get((lever, bottleneck), {})
        if observed is not None and observed <= cutoff:
            state = "observed"
        elif source_n < MIN_SOURCE_PAPERS:
            state = "insufficient_iTE_source"
        elif b_n < MIN_BOTTLENECK_PAPERS:
            state = "insufficient_TG_bottleneck"
        else:
            state = "forecast_candidate"
        rows.append(
            {
                "lever_code": lever,
                "lever_label_cn": GRAPH_LEVER_LABELS_CN[lever],
                "bottleneck_code": bottleneck,
                "bottleneck_label_cn": BOTTLENECK_LABELS_CN[bottleneck],
                "cell_state": state,
                "observed_first_year": observed if observed is not None else np.nan,
                "ite_source_papers": source_n,
                "tg_bottleneck_papers": b_n,
                "graph_rank_score_0_100": pred.get("graph_rank_score_0_100", np.nan),
                "baseline_rank_score_0_100": pred.get("baseline_rank_score_0_100", np.nan),
                "ll_bridge_codes": pred.get("ll_bridge_codes", ""),
                "bb_bridge_codes": pred.get("bb_bridge_codes", ""),
                "redox_bridge_contexts": pred.get("redox_bridge_contexts", ""),
            }
        )
    matrix = pd.DataFrame(rows)
    wide = matrix.pivot(
        index="lever_label_cn", columns="bottleneck_label_cn", values="graph_rank_score_0_100"
    )
    return matrix, wide


def write_manifest(
    path: Path,
    inputs: list[Path],
    source_records: pd.DataFrame,
    evidence: pd.DataFrame,
    bottleneck_papers: pd.DataFrame,
    matrix: pd.DataFrame,
    metrics: pd.DataFrame,
    graph_model: str,
    cutoff: int,
) -> None:
    recent = metrics[metrics["test_cutoff"].isin([2022, 2023, 2024])].copy()
    manifest = {
        "analysis": "temporal_iTE_mechanism_to_TG_bottleneck_link_prediction_pilot",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_cutoff": cutoff,
        "forecast_year": cutoff + 1,
        "prediction_target": "first qualifying mechanism-bottleneck adoption in TG literature",
        "experimental_success_probability": False,
        "redox_is_context_not_target": True,
        "ontology_designed_with_2025_visible": True,
        "backtest_status": "retrospective_temporal_backtest_not_untouched_holdout",
        "prospective_holdout": "freeze this taxonomy/rules and evaluate on complete 2026/2027 corpora",
        "selected_graph_model": graph_model,
        "selected_graph_model_label": MODEL_LABELS[graph_model],
        "counts": {
            "strict_source_papers": int(source_records["paper_id"].nunique()),
            "eligible_event_papers": int(
                evidence.loc[evidence["event_eligible"], "paper_id"].nunique()
            ),
            "eligible_event_pairs": int(
                evidence.loc[evidence["event_eligible"], ["lever_code", "bottleneck_code"]]
                .drop_duplicates()
                .shape[0]
            ),
            "eligible_bottleneck_papers": int(
                bottleneck_papers.loc[
                    bottleneck_papers["eligible_primary_TG"], "paper_id"
                ].nunique()
            ),
            "matrix_cells": int(len(matrix)),
            "forecast_candidates": int(matrix["cell_state"].eq("forecast_candidate").sum()),
            "observed_cells": int(matrix["cell_state"].eq("observed").sum()),
        },
        "recent_backtest_metrics": recent.to_dict("records"),
        "input_sha256": {str(p.relative_to(ROOT)): file_sha256(p) for p in inputs},
        "script_sha256": file_sha256(Path(__file__).resolve()),
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    paper_index = args.paper_index.resolve()
    claim_path = args.tg_claims.resolve()
    output_dir = args.output_dir.resolve()
    cutoff = int(args.forecast_cutoff)
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory, _, _, papers = load_data(input_dir, paper_index, cutoff)
    source_records = build_source_records(inventory, papers)
    claims = load_claims(claim_path, cutoff)
    evidence, bottleneck_papers, mapping = build_tg_bottleneck_evidence(claims)
    first_event = first_event_lookup(evidence)

    snapshots: dict[int, pd.DataFrame] = {}
    for year in range(2014, cutoff + 1):
        snapshot = build_snapshot(
            year, cutoff, source_records, evidence, bottleneck_papers, first_event
        )
        if not snapshot.empty:
            snapshots[year] = snapshot
    report_cutoffs = [
        year
        for year, frame in snapshots.items()
        if year < cutoff and frame["future_event_label"].sum() > 0
    ]
    metrics, backtest_predictions = run_backtest(snapshots, report_cutoffs)
    graph_model = select_graph_model(metrics)
    forecast = final_forecast(snapshots, cutoff, graph_model)
    matrix, matrix_wide = build_matrix(
        forecast, source_records, bottleneck_papers, first_event, cutoff
    )

    all_snapshots = pd.concat(snapshots.values(), ignore_index=True)
    assert all(all_snapshots["feature_max_year"].eq(all_snapshots["cutoff_year"]))
    assert all_snapshots.loc[
        all_snapshots["cutoff_year"].eq(cutoff), "future_event_label"
    ].isna().all()
    assert len(matrix) == len(GRAPH_LEVER_LABELS_CN) * len(BOTTLENECK_ORDER)

    source_records.to_csv(output_dir / "ite_source_mechanism_records.csv", index=False)
    evidence.to_csv(output_dir / "tg_mechanism_bottleneck_evidence.csv", index=False)
    bottleneck_papers.to_csv(output_dir / "tg_bottleneck_paper_records.csv", index=False)
    mapping.to_csv(output_dir / "tg_bottleneck_mapping_audit.csv", index=False)
    all_snapshots.to_csv(output_dir / "temporal_bottleneck_risk_snapshots.csv", index=False)
    metrics.to_csv(output_dir / "rolling_backtest_metrics.csv", index=False)
    backtest_predictions.to_csv(output_dir / "rolling_backtest_predictions.csv", index=False)
    forecast.to_csv(output_dir / "future_mechanism_bottleneck_predictions.csv", index=False)
    raw_top10 = forecast.head(10).copy()
    raw_top10["output_status"] = (
        "raw_graph_rank_requires_prior_art_and_causal_evidence_audit"
    )
    raw_top10.to_csv(output_dir / "raw_graph_top10_for_audit.csv", index=False)
    matrix.to_csv(output_dir / "mechanism_bottleneck_matrix_long.csv", index=False)
    matrix_wide.to_csv(output_dir / "mechanism_bottleneck_matrix_scores.csv")
    write_manifest(
        output_dir / "prediction_manifest.json",
        [
            input_dir / "ite_claim_inventory_with_levers.csv",
            paper_index,
            claim_path,
        ],
        source_records,
        evidence,
        bottleneck_papers,
        matrix,
        metrics,
        graph_model,
        cutoff,
    )
    print(
        json.dumps(
            {
                "selected_graph_model": graph_model,
                "event_papers": int(evidence.loc[evidence.event_eligible, "paper_id"].nunique()),
                "event_pairs": int(
                    evidence.loc[evidence.event_eligible, ["lever_code", "bottleneck_code"]]
                    .drop_duplicates()
                    .shape[0]
                ),
                "forecast_candidates": len(forecast),
                "top10": forecast.head(10)[
                    [
                        "lever_label_cn",
                        "bottleneck_label_cn",
                        "graph_rank_score_0_100",
                        "baseline_rank_score_0_100",
                    ]
                ].to_dict("records"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
