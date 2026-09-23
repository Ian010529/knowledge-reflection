"""Project observed TG concept pairs into the global iTE pair space.

The unit of comparison is an observed typed pair, not an isolated keyword.
TG pairs remain in a separate layer.  Cross-layer links record direct pair
overlap, an exact/family endpoint bridge, or an explicitly curated transfer
program; no TG edge is written into the historical iTE graph.
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
from pathlib import Path
from html import escape
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "task_typed_concept_layer"
OUT = ROOT / "pair_projection"

CONCEPTS = LAYER / "paper_typed_concepts.csv"
RELATIONS = LAYER / "paper_typed_relations.csv"
VOCABULARY = LAYER / "typed_concept_vocabulary.csv"
OVERLAP_AUDIT = LAYER / "typed_node_overlap_audit.csv"
PAPERS = ROOT / "final_concept_layer" / "final_paper_qc.csv"
PROGRAMS = ROOT / "ite_tg_complementarity" / "ite_tg_complementarity_programs.csv"
CARDS = ROOT / "ite_tg_complementarity" / "ite_mechanism_cards_v2.csv"


ROLE_ORDER = {
    "material_system": 0,
    "intervention": 1,
    "structure_state": 2,
    "mechanism": 3,
    "outcome_property": 4,
    "device_context": 5,
    "evidence_method": 6,
}

PAIR_ROLE_WHITELIST = {
    frozenset(("material_system", "intervention")),
    frozenset(("material_system", "structure_state")),
    frozenset(("material_system", "mechanism")),
    frozenset(("intervention", "structure_state")),
    frozenset(("intervention", "mechanism")),
    frozenset(("structure_state", "mechanism")),
}

BASE_SCORE_BY_LINK = {
    "direct_pair_overlap": 0.92,
    "shared_mechanism_completion": 0.82,
    "shared_intervention_transfer": 0.80,
    "shared_structure_extension": 0.74,
    "shared_material_context": 0.62,
    "shared_outcome_only": 0.32,
    "family_mechanism_completion": 0.66,
    "family_intervention_transfer": 0.63,
    "family_structure_extension": 0.58,
    "family_material_context": 0.48,
    "family_outcome_only": 0.24,
}

NON_ACTIONABLE_NOVELTY = {
    "exact_TG_pair_overlap",
    "known_TG_positive_control",
}


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def stable_id(prefix: str, *values: object) -> str:
    payload = "\x1f".join(clean(value).casefold() for value in values)
    return f"{prefix}_{sha1(payload.encode('utf-8')).hexdigest()[:12]}"


def joined(values: pd.Series, limit: int = 12) -> str:
    ordered = list(dict.fromkeys(clean(value) for value in values if clean(value)))
    return "; ".join(ordered[:limit])


def has_layer(value: object, layer: str) -> bool:
    return layer in clean(value).split("|")


def pair_type(role_a: str, role_b: str) -> str:
    roles = sorted((role_a, role_b), key=lambda role: ROLE_ORDER.get(role, 99))
    return f"{roles[0]}__{roles[1]}"


def split_terms(value: object) -> list[str]:
    return [clean(part) for part in re.split(r"\s*;\s*", clean(value)) if clean(part)]


def strict_paper_node_assignments(
    concepts: pd.DataFrame, cards: pd.DataFrame
) -> set[tuple[str, str]]:
    """Keep audited nodes plus claim nodes from the strict evidence-ready lane."""
    audited = concepts[concepts["provenance"].eq("audited_paper_concept_map")]
    allowed = set(zip(audited["paper_id"], audited["node_id"]))

    eligible = cards[
        cards["source_analysis_included"].fillna(False).astype(bool)
        & cards["evidence_ready_for_primary_analysis"].fillna(False).astype(bool)
        & ~cards["already_TG_or_coupled_at_source"].fillna(False).astype(bool)
        & ~cards["likely_review"].fillna(False).astype(bool)
    ]
    for card in eligible.itertuples(index=False):
        for label in split_terms(card.mechanism_concepts):
            allowed.add((card.paper_id, stable_id("TC", "mechanism", label)))
        for code in split_terms(card.transferable_lever_codes):
            allowed.add((card.paper_id, stable_id("TC", "intervention", code)))
    return allowed


def build_pair_bank(
    relations: pd.DataFrame,
    concepts: pd.DataFrame,
    papers: pd.DataFrame,
    vocabulary: pd.DataFrame,
    layer_name: str,
    allowed_assignments: set[tuple[str, str]],
) -> pd.DataFrame:
    node_lookup = vocabulary.set_index("node_id")
    paper_meta = papers.set_index("paper_id")
    if layer_name == "TG":
        # TG is the reference corpus: papers found by both searches belong to
        # TG for querying, while remaining excluded from the iTE source layer.
        domain_papers = {
            paper_id
            for paper_id, membership in paper_meta["source_membership"].items()
            if has_layer(membership, "TG")
        }
    else:
        domain_papers = {
            paper_id
            for paper_id, membership in paper_meta["source_membership"].items()
            if clean(membership) == layer_name
        }
    frame = relations[relations["paper_id"].isin(domain_papers)].copy()
    role_keys = frame.apply(
        lambda row: frozenset((row["source_role"], row["target_role"])), axis=1
    )
    frame = frame[role_keys.isin(PAIR_ROLE_WHITELIST)].copy()
    frame = frame[
        frame.apply(
            lambda row: (row["paper_id"], row["source_node_id"]) in allowed_assignments
            and (row["paper_id"], row["target_node_id"]) in allowed_assignments,
            axis=1,
        )
    ].copy()
    if frame.empty:
        return frame

    frame["source_membership"] = frame["paper_id"].map(
        paper_meta["source_membership"]
    )
    frame["doi"] = frame["paper_id"].map(paper_meta["doi"])
    frame["title"] = frame["paper_id"].map(paper_meta["title"])
    frame["node_a_label"] = frame["source_node_id"].map(node_lookup["node_label"])
    frame["node_b_label"] = frame["target_node_id"].map(node_lookup["node_label"])
    frame["pair_type"] = frame.apply(
        lambda row: pair_type(row["source_role"], row["target_role"]), axis=1
    )
    frame["pair_key"] = frame["source_node_id"] + "::" + frame["target_node_id"]
    frame["is_shared_corpus_paper"] = frame["source_membership"].eq("iTE|TG")
    frame["is_exclusive_layer_paper"] = frame["source_membership"].eq(layer_name)

    bank = (
        frame.groupby(
            [
                "pair_key",
                "source_node_id",
                "source_role",
                "node_a_label",
                "target_node_id",
                "target_role",
                "node_b_label",
                "pair_type",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            paper_count=("paper_id", "nunique"),
            exclusive_layer_paper_count=("is_exclusive_layer_paper", "sum"),
            shared_corpus_paper_count=("is_shared_corpus_paper", "sum"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            supporting_paper_ids=("paper_id", lambda values: joined(values, limit=1000)),
            supporting_dois=("doi", lambda values: joined(values, limit=1000)),
            supporting_titles=("title", lambda values: joined(values, limit=5)),
        )
    )
    prefix = "IP" if layer_name == "iTE" else "TP"
    bank.insert(
        0,
        "pair_id",
        [stable_id(prefix, key) for key in bank["pair_key"]],
    )
    bank.insert(1, "domain_layer", layer_name)

    domain_df = (
        concepts[concepts["paper_id"].isin(domain_papers)]
        .groupby("node_id")["paper_id"]
        .nunique()
    )
    bank["node_a_domain_df"] = bank["source_node_id"].map(domain_df).fillna(0).astype(int)
    bank["node_b_domain_df"] = bank["target_node_id"].map(domain_df).fillna(0).astype(int)
    bank["historical_graph_eligible"] = (
        (bank["node_a_domain_df"] >= 2) & (bank["node_b_domain_df"] >= 2)
    )
    bank["pair_evidence_strength"] = bank["paper_count"].map(
        lambda count: round(min(1.0, math.log1p(count) / math.log(6)), 4)
    )
    return bank.sort_values(
        ["paper_count", "first_year", "pair_type"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def other_endpoint(pair: pd.Series, shared_node_id: str) -> tuple[str, str, str]:
    if pair["source_node_id"] == shared_node_id:
        return pair["target_node_id"], pair["node_b_label"], pair["target_role"]
    return pair["source_node_id"], pair["node_a_label"], pair["source_role"]


def exact_link_type(shared_role: str, same_pair: bool) -> str:
    if same_pair:
        return "direct_pair_overlap"
    return {
        "mechanism": "shared_mechanism_completion",
        "intervention": "shared_intervention_transfer",
        "structure_state": "shared_structure_extension",
        "material_system": "shared_material_context",
        "outcome_property": "shared_outcome_only",
    }.get(shared_role, "shared_outcome_only")


def family_link_type(role: str) -> str:
    return {
        "mechanism": "family_mechanism_completion",
        "intervention": "family_intervention_transfer",
        "structure_state": "family_structure_extension",
        "material_system": "family_material_context",
        "outcome_property": "family_outcome_only",
    }.get(role, "family_outcome_only")


def bridge_score(
    link_type: str,
    ite_pair_support: float,
    tg_pair_support: float,
    endpoint_df: int,
    similarity: float = 1.0,
) -> float:
    base = BASE_SCORE_BY_LINK[link_type]
    specificity = 1.0 / (1.0 + math.log10(max(endpoint_df, 1)))
    score = (
        base
        + 0.035 * ite_pair_support
        + 0.025 * tg_pair_support
        + 0.035 * specificity
    )
    if link_type.startswith("family_"):
        score *= 0.88 + 0.12 * similarity
    return round(min(score, 0.99), 4)


def exact_and_family_links(
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    audit: pd.DataFrame,
) -> pd.DataFrame:
    ite_records = ite.to_dict("records")
    tg_records = tg.to_dict("records")
    ite_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pair in ite_records:
        ite_by_node[pair["source_node_id"]].append(pair)
        ite_by_node[pair["target_node_id"]].append(pair)

    family_neighbors: dict[str, list[tuple[str, float]]] = defaultdict(list)
    valid_audit = audit[audit["audit_type"].isin(["nested_same_role", "near_duplicate_same_role"])]
    for item in valid_audit.itertuples(index=False):
        family_neighbors[item.left_node_id].append((item.right_node_id, item.string_similarity))
        family_neighbors[item.right_node_id].append((item.left_node_id, item.string_similarity))

    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for tg_pair in tg_records:
        for tg_node_id, tg_label, tg_role, tg_df in [
            (
                tg_pair["source_node_id"],
                tg_pair["node_a_label"],
                tg_pair["source_role"],
                tg_pair["node_a_domain_df"],
            ),
            (
                tg_pair["target_node_id"],
                tg_pair["node_b_label"],
                tg_pair["target_role"],
                tg_pair["node_b_domain_df"],
            ),
        ]:
            candidates = [(tg_node_id, 1.0, True)]
            candidates.extend(
                (neighbor, similarity, False)
                for neighbor, similarity in family_neighbors.get(tg_node_id, [])
            )
            for ite_node_id, similarity, exact in candidates:
                for ite_pair in ite_by_node.get(ite_node_id, []):
                    same_pair = ite_pair["pair_key"] == tg_pair["pair_key"]
                    link_type = (
                        exact_link_type(tg_role, same_pair)
                        if exact
                        else family_link_type(tg_role)
                    )
                    anchor_key = "__full_pair__" if same_pair else tg_node_id
                    key = (
                        tg_pair["pair_id"],
                        ite_pair["pair_id"],
                        link_type,
                        anchor_key,
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    ite_other_id, ite_other_label, ite_other_role = other_endpoint(
                        pd.Series(ite_pair), ite_node_id
                    )
                    tg_other_id, tg_other_label, tg_other_role = other_endpoint(
                        pd.Series(tg_pair), tg_node_id
                    )
                    score = bridge_score(
                        link_type,
                        ite_pair["pair_evidence_strength"],
                        tg_pair["pair_evidence_strength"],
                        int(tg_df),
                        similarity,
                    )
                    rows.append(
                        {
                            "link_id": stable_id(
                                "XL",
                                tg_pair["pair_id"],
                                ite_pair["pair_id"],
                                link_type,
                                anchor_key,
                            ),
                            "tg_pair_id": tg_pair["pair_id"],
                            "ite_pair_id": ite_pair["pair_id"],
                            "link_type": link_type,
                            "bridge_score": score,
                            "shared_or_family_tg_node_id": tg_node_id,
                            "shared_or_family_tg_label": tg_label,
                            "shared_or_family_ite_node_id": ite_node_id,
                            "shared_or_family_ite_label": (
                                tg_label
                                if exact
                                else next(
                                    label
                                    for node_id, label in [
                                        (ite_pair["source_node_id"], ite_pair["node_a_label"]),
                                        (ite_pair["target_node_id"], ite_pair["node_b_label"]),
                                    ]
                                    if node_id == ite_node_id
                                )
                            ),
                            "bridge_role": tg_role,
                            "shared_endpoint_tg_df": int(tg_df),
                            "endpoint_match": "exact" if exact else "audited_family",
                            "endpoint_string_similarity": similarity,
                            "ite_other_node_id": ite_other_id,
                            "ite_other_label": ite_other_label,
                            "ite_other_role": ite_other_role,
                            "tg_other_node_id": tg_other_id,
                            "tg_other_label": tg_other_label,
                            "tg_other_role": tg_other_role,
                            "ite_pair_type": ite_pair["pair_type"],
                            "tg_pair_type": tg_pair["pair_type"],
                            "ite_pair_paper_count": ite_pair["paper_count"],
                            "tg_pair_paper_count": tg_pair["paper_count"],
                            "ite_supporting_paper_ids": ite_pair["supporting_paper_ids"],
                            "tg_supporting_paper_ids": tg_pair["supporting_paper_ids"],
                            "program_id": "",
                            "program_title_cn": "",
                            "program_candidate_status": "",
                            "target_redox_family": "",
                            "program_source_paper_ids": "",
                            "ite_aligned_supporting_paper_ids": "",
                            "ite_source_alignment": "not_applicable",
                            "evidence_scope": (
                                "observed_pair_overlap"
                                if same_pair
                                else "retrieval_bridge_requires_mechanistic_review"
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def contains_paper(pair_row: pd.Series, paper_id: str) -> bool:
    return paper_id in clean(pair_row["supporting_paper_ids"]).split("; ")


def supporting_paper_ids(pair: object) -> set[str]:
    return set(split_terms(pair["supporting_paper_ids"]))


TARGET_FAMILY_PATTERNS = {
    "ferri_ferrocyanide": re.compile(r"ferri/?ferrocyanide|\[?fe\(cn\)6", re.I),
    "iodide_triiodide": re.compile(r"iodide/?triiodide|\bi3[-−]?\b", re.I),
    "quinone_hydroquinone": re.compile(r"hydroquinone|benzoquinone|quinone|hq/bq|q/hq", re.I),
    "copper": re.compile(r"\bcopper\b|\bcu(?:\+|2\+|/cu)", re.I),
    "fe_ii_iii": re.compile(r"fe2\+/?fe3\+|fe\(ii\)/?fe\(iii\)|iron.*redox", re.I),
    "cobalt_complex": re.compile(r"\bcobalt\b|\bco(?:2\+|3\+|\(ii\)|\(iii\))", re.I),
}


def target_family_match(pair: pd.Series, family: str) -> bool:
    if family == "any_tg":
        return True
    pattern = TARGET_FAMILY_PATTERNS.get(family)
    if pattern is None:
        return False
    combined = f"{clean(pair['node_a_label'])} {clean(pair['node_b_label'])}"
    return bool(pattern.search(combined))


def program_pair_candidates(
    program: object,
    ite_by_node: dict[str, list[dict[str, object]]],
    tg: pd.DataFrame,
    intervention_lookup: dict[str, str],
) -> dict[str, object]:
    """Resolve the auditable iTE source lane and TG grounding lane for a program."""
    lever_label = clean(program.source_lever_code).replace("_", " ")
    lever_node_id = intervention_lookup.get(lever_label, "")
    source_paper_ids = set(split_terms(program.top5_source_supporting_paper_ids))
    top_source_paper_id = clean(program.top_iTE_paper_id)
    if top_source_paper_id:
        source_paper_ids.add(top_source_paper_id)

    ite_candidates = [
        pair
        for pair in ite_by_node.get(lever_node_id, [])
        if supporting_paper_ids(pair) & source_paper_ids
    ]
    tg_family_candidates = [
        pair
        for _, pair in tg.iterrows()
        if contains_paper(pair, clean(program.TG_baseline_paper_id))
        and target_family_match(pair, clean(program.target_redox_family))
    ]
    tg_grounding_candidates = [
        pair
        for pair in tg_family_candidates
        if "material_system" in {pair["source_role"], pair["target_role"]}
        and {"mechanism", "structure_state"}
        & {pair["source_role"], pair["target_role"]}
    ]
    return {
        "lever_label": lever_label,
        "lever_node_id": lever_node_id,
        "source_paper_ids": source_paper_ids,
        "ite_candidates": ite_candidates,
        "tg_family_candidates": tg_family_candidates,
        "tg_grounding_candidates": tg_grounding_candidates,
    }


def curated_program_links(
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    vocabulary: pd.DataFrame,
    programs: pd.DataFrame,
) -> pd.DataFrame:
    intervention_lookup = {
        clean(row.node_label): row.node_id
        for row in vocabulary[vocabulary["node_role"].eq("intervention")].itertuples(index=False)
    }
    ite_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pair in ite.to_dict("records"):
        ite_by_node[pair["source_node_id"]].append(pair)
        ite_by_node[pair["target_node_id"]].append(pair)

    rows: list[dict[str, object]] = []
    for program in programs.sort_values("priority_score", ascending=False).itertuples(index=False):
        candidates = program_pair_candidates(
            program, ite_by_node, tg, intervention_lookup
        )
        lever_label = candidates["lever_label"]
        lever_node_id = candidates["lever_node_id"]
        source_paper_ids = candidates["source_paper_ids"]
        if not lever_node_id or not source_paper_ids:
            continue
        ite_candidates = candidates["ite_candidates"]
        tg_candidates = candidates["tg_grounding_candidates"]
        local: list[dict[str, object]] = []
        for ite_pair in ite_candidates:
            aligned_source_ids = sorted(
                supporting_paper_ids(ite_pair) & source_paper_ids
            )
            ite_other_id, ite_other_label, ite_other_role = other_endpoint(
                pd.Series(ite_pair), lever_node_id
            )
            ite_role_bonus = {
                "mechanism": 0.075,
                "structure_state": 0.065,
                "material_system": 0.050,
                "outcome_property": 0.025,
            }.get(ite_other_role, 0.0)
            for tg_pair in tg_candidates:
                tg_roles = {tg_pair["source_role"], tg_pair["target_role"]}
                if "material_system" not in tg_roles or not (
                    {"mechanism", "structure_state"} & tg_roles
                ):
                    continue
                tg_role_bonus = 0.075 if "mechanism" in tg_roles else 0.070
                score = min(
                    0.99,
                    0.79
                    + ite_role_bonus
                    + tg_role_bonus
                    + 0.025 * ite_pair["pair_evidence_strength"]
                    + 0.015 * tg_pair["pair_evidence_strength"],
                )
                local.append(
                    {
                        "link_id": stable_id(
                            "XL", program.program_id, tg_pair["pair_id"], ite_pair["pair_id"]
                        ),
                        "tg_pair_id": tg_pair["pair_id"],
                        "ite_pair_id": ite_pair["pair_id"],
                        "link_type": "curated_program_bridge",
                        "bridge_score": round(score, 4),
                        "shared_or_family_tg_node_id": "",
                        "shared_or_family_tg_label": "",
                        "shared_or_family_ite_node_id": lever_node_id,
                        "shared_or_family_ite_label": lever_label,
                        "bridge_role": "intervention_to_TG_pair",
                        "shared_endpoint_tg_df": "",
                        "endpoint_match": "curated_transfer_rule",
                        "endpoint_string_similarity": "",
                        "ite_other_node_id": ite_other_id,
                        "ite_other_label": ite_other_label,
                        "ite_other_role": ite_other_role,
                        "tg_other_node_id": "",
                        "tg_other_label": "",
                        "tg_other_role": "",
                        "ite_pair_type": ite_pair["pair_type"],
                        "tg_pair_type": tg_pair["pair_type"],
                        "ite_pair_paper_count": ite_pair["paper_count"],
                        "tg_pair_paper_count": tg_pair["paper_count"],
                        "ite_supporting_paper_ids": ite_pair["supporting_paper_ids"],
                        "tg_supporting_paper_ids": tg_pair["supporting_paper_ids"],
                        "program_id": program.program_id,
                        "program_title_cn": program.program_title_cn,
                        "program_candidate_status": program.candidate_status,
                        "target_redox_family": program.target_redox_family,
                        "program_source_paper_ids": "; ".join(sorted(source_paper_ids)),
                        "ite_aligned_supporting_paper_ids": "; ".join(aligned_source_ids),
                        "ite_source_alignment": "program_source_paper_intersection",
                        "evidence_scope": "curated_hypothesis_link_not_observed_causality",
                    }
                )
        local = sorted(
            local,
            key=lambda row: (
                row["bridge_score"],
                row["ite_pair_paper_count"],
                row["tg_pair_paper_count"],
            ),
            reverse=True,
        )[:20]
        rows.extend(local)
    return pd.DataFrame(rows)


def attach_pair_labels(
    links: pd.DataFrame, ite: pd.DataFrame, tg: pd.DataFrame
) -> pd.DataFrame:
    ite_lookup = ite.set_index("pair_id")
    tg_lookup = tg.set_index("pair_id")
    links = links.copy()
    for prefix, lookup, id_column in [
        ("ite", ite_lookup, "ite_pair_id"),
        ("tg", tg_lookup, "tg_pair_id"),
    ]:
        links[f"{prefix}_node_a_label"] = links[id_column].map(lookup["node_a_label"])
        links[f"{prefix}_node_a_role"] = links[id_column].map(lookup["source_role"])
        links[f"{prefix}_node_b_label"] = links[id_column].map(lookup["node_b_label"])
        links[f"{prefix}_node_b_role"] = links[id_column].map(lookup["target_role"])
        links[f"{prefix}_first_year"] = links[id_column].map(lookup["first_year"])
        links[f"{prefix}_supporting_titles"] = links[id_column].map(lookup["supporting_titles"])
    links["ite_pair_label"] = (
        links["ite_node_a_label"] + "  +  " + links["ite_node_b_label"]
    )
    links["tg_pair_label"] = (
        links["tg_node_a_label"] + "  +  " + links["tg_node_b_label"]
    )
    return links


def independent_support_points(count: object) -> int:
    value = int(count)
    if value >= 5:
        return 5
    if value >= 3:
        return 4
    if value == 2:
        return 2
    return 1


def add_transfer_score(links: pd.DataFrame, tg_paper_count: int) -> pd.DataFrame:
    """Transparent 0-100 retrieval score; never interpreted as success probability."""
    rows = []
    for item in links.to_dict("records"):
        link_type = item["link_type"]
        curated = link_type == "curated_program_bridge"
        overlap = link_type == "direct_pair_overlap"
        c1 = 24 if curated else 30
        if curated:
            c2 = 12 if item.get("target_redox_family") == "any_tg" else 25
            ite_roles = {item["ite_node_a_role"], item["ite_node_b_role"]}
            tg_roles = {item["tg_node_a_role"], item["tg_node_b_role"]}
            c3 = (
                15
                if "intervention" in ite_roles
                and ({"mechanism", "structure_state"} & ite_roles)
                and "material_system" in tg_roles
                and ({"mechanism", "structure_state"} & tg_roles)
                else 10
            )
            c4 = 15 if "intervention" in ite_roles else 10
        else:
            c2 = 0
            c3 = {
                "mechanism": 15,
                "intervention": 15,
                "structure_state": 10,
                "material_system": 5,
            }.get(item.get("bridge_role"), 0)
            c4 = 7
        c5 = 4
        c6 = independent_support_points(item["ite_pair_paper_count"])

        hub_penalty = 0
        shared_df = pd.to_numeric(item.get("shared_endpoint_tg_df"), errors="coerce")
        if not curated and not pd.isna(shared_df):
            prevalence = float(shared_df) / float(tg_paper_count)
            if prevalence > 0.20:
                hub_penalty = 12
            elif prevalence > 0.10:
                hub_penalty = 8
            elif prevalence > 0.05:
                hub_penalty = 4

        raw = c1 + c2 + c3 + c4 + c5 + c6 - hub_penalty
        cap_reason = ""
        if overlap:
            transfer_score = 0
            cap_reason = "exact_pair_overlap_is_precedent"
        elif not curated:
            transfer_score = min(raw, 59)
            cap_reason = "topological_hinge_without_directional_rule"
        elif item.get("target_redox_family") == "any_tg":
            transfer_score = min(raw, 69)
            cap_reason = "broad_any_tg_rule"
        else:
            transfer_score = min(raw, 100)

        if overlap:
            inference_status = "precedent_or_positive_control"
            novelty_status = "exact_TG_pair_overlap"
        elif curated and "positive_control" in clean(item.get("program_candidate_status")):
            inference_status = "known_positive_control"
            novelty_status = "known_TG_positive_control"
        elif curated and transfer_score >= 75 and c2 == 25:
            inference_status = "mechanistic_transfer_candidate"
            status = clean(item.get("program_candidate_status"))
            novelty_status = (
                "direct_TG_prior_art_upgrade_candidate"
                if status == "direct_TG_precedent_upgrade_candidate"
                else "white_space_in_frozen_local_corpus"
            )
        elif curated:
            inference_status = "rule_bridge_needs_review"
            novelty_status = "curated_status_requires_review"
        else:
            inference_status = "topological_retrieval_only"
            novelty_status = "not_assessed"

        item.update(
            {
                "C1_anchor": c1,
                "C2_directional_rule": c2,
                "C3_role_logic": c3,
                "C4_ite_evidence": c4,
                "C5_tg_grounding": c5,
                "C6_independent_support": c6,
                "hub_penalty": hub_penalty,
                "transfer_score": transfer_score,
                "score_cap_reason": cap_reason,
                "inference_status": inference_status,
                "novelty_status": novelty_status,
            }
        )
        rows.append(item)
    return pd.DataFrame(rows)


def add_closure_fields(links: pd.DataFrame) -> pd.DataFrame:
    links = links.copy()
    closure_source = []
    closure_source_role = []
    closure_target = []
    closure_target_role = []
    temporal = []
    for row in links.itertuples(index=False):
        if row.link_type == "direct_pair_overlap":
            closure_source.append("")
            closure_source_role.append("")
            closure_target.append("")
            closure_target_role.append("")
        elif row.link_type == "curated_program_bridge":
            closure_source.append(row.shared_or_family_ite_label)
            closure_source_role.append("intervention")
            if row.tg_node_a_role == "material_system":
                closure_target.append(row.tg_node_a_label)
                closure_target_role.append(row.tg_node_a_role)
            else:
                closure_target.append(row.tg_node_b_label)
                closure_target_role.append(row.tg_node_b_role)
        else:
            closure_source.append(row.ite_other_label)
            closure_source_role.append(row.ite_other_role)
            closure_target.append(row.tg_other_label)
            closure_target_role.append(row.tg_other_role)
        ite_year = pd.to_numeric(row.ite_first_year, errors="coerce")
        tg_year = pd.to_numeric(row.tg_first_year, errors="coerce")
        temporal.append(
            "unknown"
            if pd.isna(ite_year) or pd.isna(tg_year)
            else (
                "iTE_precedes_or_same_year"
                if ite_year <= tg_year
                else "iTE_observed_after_TG_pair"
            )
        )
    links["proposed_closure_source_label"] = closure_source
    links["proposed_closure_source_role"] = closure_source_role
    links["proposed_closure_target_label"] = closure_target
    links["proposed_closure_target_role"] = closure_target_role
    links["temporal_alignment"] = temporal
    return links


def build_program_level_results(
    programs: pd.DataFrame,
    links: pd.DataFrame,
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    vocabulary: pd.DataFrame,
) -> pd.DataFrame:
    """One auditable row per curated program, including strict misses."""
    curated = links[links["link_type"].eq("curated_program_bridge")].copy()
    intervention_lookup = {
        clean(row.node_label): row.node_id
        for row in vocabulary[vocabulary["node_role"].eq("intervention")].itertuples(
            index=False
        )
    }
    ite_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pair in ite.to_dict("records"):
        ite_by_node[pair["source_node_id"]].append(pair)
        ite_by_node[pair["target_node_id"]].append(pair)
    rows: list[dict[str, object]] = []
    for program in programs.sort_values("priority_score", ascending=False).itertuples(
        index=False
    ):
        local = curated[curated["program_id"].eq(program.program_id)].copy()
        candidates = program_pair_candidates(
            program, ite_by_node, tg, intervention_lookup
        )
        source_pair_count = len(candidates["ite_candidates"])
        target_family_pair_count = len(candidates["tg_family_candidates"])
        target_grounding_pair_count = len(candidates["tg_grounding_candidates"])
        if not local.empty:
            strict_pair_status = "source_aligned_hit"
        elif not candidates["lever_node_id"]:
            strict_pair_status = "missing_lever_node"
        elif not candidates["source_paper_ids"]:
            strict_pair_status = "missing_declared_source_paper"
        elif source_pair_count == 0:
            strict_pair_status = "no_iTE_source_pair"
        elif target_grounding_pair_count == 0:
            strict_pair_status = "no_TG_grounding_pair"
        else:
            strict_pair_status = "no_compatible_bridge"
        representative: dict[str, object] = {}
        if not local.empty:
            local["ite_role_priority"] = local["ite_other_role"].map(
                {"mechanism": 3, "structure_state": 2, "material_system": 1}
            ).fillna(0)
            local["tg_role_priority"] = local.apply(
                lambda row: 2
                if "mechanism" in {row["tg_node_a_role"], row["tg_node_b_role"]}
                else 1,
                axis=1,
            )
            local = local.sort_values(
                [
                    "transfer_score",
                    "ite_role_priority",
                    "tg_role_priority",
                    "tg_pair_paper_count",
                    "ite_pair_paper_count",
                ],
                ascending=[False, False, False, True, False],
            )
            representative = local.iloc[0].to_dict()

        positive_control = bool(program.positive_control)
        rows.append(
            {
                "program_id": program.program_id,
                "program_group": (
                    "positive_control" if positive_control else "new_scheme"
                ),
                "positive_control": positive_control,
                "priority_score": program.priority_score,
                "candidate_status": program.candidate_status,
                "candidate_status_cn": program.candidate_status_cn,
                "program_title_cn": program.program_title_cn,
                "source_lever_code": program.source_lever_code,
                "source_lever_cn": program.source_lever_cn,
                "expected_source_paper_ids": program.top5_source_supporting_paper_ids,
                "top_iTE_paper_id": program.top_iTE_paper_id,
                "top_iTE_title": program.top_iTE_title,
                "target_redox_family": program.target_redox_family,
                "target_redox_system_cn": program.target_redox_system_cn,
                "TG_baseline_paper_id": program.TG_baseline_paper_id,
                "TG_baseline_title": program.TG_baseline_title,
                "strict_pair_status": strict_pair_status,
                "strict_bridge_count": len(local),
                "source_aligned_ite_pair_count": source_pair_count,
                "target_family_tg_pair_count": target_family_pair_count,
                "target_grounding_tg_pair_count": target_grounding_pair_count,
                "representative_link_id": representative.get("link_id", ""),
                "representative_transfer_score": representative.get(
                    "transfer_score", ""
                ),
                "representative_ite_pair_label": representative.get(
                    "ite_pair_label", ""
                ),
                "representative_tg_pair_label": representative.get(
                    "tg_pair_label", ""
                ),
                "representative_ite_supporting_paper_ids": representative.get(
                    "ite_supporting_paper_ids", ""
                ),
                "representative_ite_aligned_paper_ids": representative.get(
                    "ite_aligned_supporting_paper_ids", ""
                ),
                "representative_tg_supporting_paper_ids": representative.get(
                    "tg_supporting_paper_ids", ""
                ),
                "first_decisive_test_cn": program.first_decisive_test_cn,
                "go_no_go_criterion_cn": program.go_no_go_criterion_cn,
                "failure_modes_cn": program.failure_modes_cn,
            }
        )
    return pd.DataFrame(rows)


def select_top_bridges(links: pd.DataFrame) -> pd.DataFrame:
    useful = links[
        ~links["link_type"].isin(["direct_pair_overlap", "shared_outcome_only", "family_outcome_only"])
        & ~links["novelty_status"].isin(NON_ACTIONABLE_NOVELTY)
    ].copy()
    useful["curated_priority"] = useful["link_type"].eq("curated_program_bridge").astype(int)
    useful = useful.sort_values(
        ["curated_priority", "transfer_score", "ite_pair_paper_count", "tg_pair_paper_count"],
        ascending=[False, False, False, False],
    )
    useful = useful.drop_duplicates(["tg_pair_id", "ite_pair_id"], keep="first")
    useful["rank_within_tg_pair"] = useful.groupby("tg_pair_id").cumcount() + 1
    useful["global_rank"] = range(1, len(useful) + 1)
    return useful.head(500).drop(columns="curated_priority")


def representative_bridges(
    links: pd.DataFrame, programs: pd.DataFrame, limit: int = 6
) -> pd.DataFrame:
    curated = links[
        links["link_type"].eq("curated_program_bridge")
        & ~links["novelty_status"].isin(NON_ACTIONABLE_NOVELTY)
    ].copy()
    priority = programs.set_index("program_id")["priority_score"]
    curated["program_priority"] = curated["program_id"].map(priority).fillna(0)
    curated = curated.sort_values(
        ["program_priority", "transfer_score", "ite_pair_paper_count", "tg_pair_paper_count"],
        ascending=False,
    )
    chosen = curated.drop_duplicates("program_id").head(limit).copy()
    if len(chosen) < limit:
        fallback = links[
            links["link_type"].isin(
                ["shared_mechanism_completion", "shared_intervention_transfer"]
            )
        ].sort_values("transfer_score", ascending=False)
        fallback = fallback[~fallback["link_id"].isin(chosen["link_id"])]
        chosen = pd.concat([chosen, fallback.head(limit - len(chosen))], ignore_index=True)
    return chosen.reset_index(drop=True)


def wrap_label(label: str, width: int = 34, max_lines: int = 3) -> str:
    words = clean(label).split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if len(" ".join(current + [word])) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "…"
    return "\n".join(lines)


def svg_text_lines(label: str, x: float, y: float, width: int, max_lines: int) -> str:
    lines = wrap_label(label, width=width, max_lines=max_lines).split("\n")
    start_y = y - (len(lines) - 1) * 8
    tspans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else 18
        tspans.append(
            f'<tspan x="{x}" y="{start_y if index == 0 else start_y + index * 18}">{escape(line)}</tspan>'
        )
    return "".join(tspans)


def draw_representative_paths(frame: pd.DataFrame) -> None:
    if frame.empty:
        return
    n = len(frame)
    width, row_height, top = 1400, 172, 58
    height = top + row_height * n + 24
    boxes = {
        "ite": (34, 370, "#DCEEFF"),
        "bridge": (495, 350, "#FFF0C2"),
        "tg": (936, 370, "#DFF3E4"),
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans CJK SC","PingFang SC",Arial,sans-serif;fill:#20323D}.head{font-size:16px;font-weight:600}.boxhead{font-size:12px;font-weight:600;letter-spacing:.5px}.body{font-size:13px}.score{font-size:13px;font-weight:600}.arrow{stroke:#506572;stroke-width:1.6;fill:none}</style>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#506572"/></marker></defs>',
        '<text class="head" x="34" y="28">Observed iTE pair</text>',
        '<text class="head" x="495" y="28">Cross-layer bridge</text>',
        '<text class="head" x="936" y="28">Observed TG query pair</text>',
        '<text class="head" x="1364" y="28" text-anchor="end">Score</text>',
    ]
    for index, row in frame.iterrows():
        y = top + index * row_height
        mid_y = y + 62
        labels = {
            "ite": row["ite_pair_label"],
            "bridge": (
                row["program_title_cn"]
                if clean(row["program_title_cn"])
                else row["link_type"].replace("_", " ")
            ),
            "tg": row["tg_pair_label"],
        }
        for key, (x, box_width, fill) in boxes.items():
            parts.append(
                f'<rect x="{x}" y="{y}" width="{box_width}" height="124" rx="12" fill="{fill}" stroke="#506572" stroke-width="1"/>'
            )
            heading = {"ite": "iTE PAIR", "bridge": "PAIR BRIDGE", "tg": "TG PAIR"}[key]
            parts.append(
                f'<text class="boxhead" x="{x + 18}" y="{y + 25}">{heading}</text>'
            )
            parts.append(
                f'<text class="body" x="{x + box_width / 2}" y="{y + 57}" text-anchor="middle">'
                + svg_text_lines(labels[key], x + box_width / 2, y + 65, 38 if key != "bridge" else 30, 3)
                + "</text>"
            )
        parts.append(
            f'<path class="arrow" d="M404,{mid_y} L489,{mid_y}" marker-end="url(#arrow)"/>'
        )
        parts.append(
            f'<path class="arrow" d="M845,{mid_y} L930,{mid_y}" marker-end="url(#arrow)"/>'
        )
        parts.append(
            f'<text class="score" x="1364" y="{mid_y + 5}" text-anchor="end">{int(row["transfer_score"])}</text>'
        )
    parts.append("</svg>")
    (OUT / "representative_pair_projection.svg").write_text(
        "\n".join(parts), encoding="utf-8"
    )


def write_readme(
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    links: pd.DataFrame,
    top: pd.DataFrame,
    representative: pd.DataFrame,
    source_overlaps: pd.DataFrame,
    excluded_overlap_controls: pd.DataFrame,
    program_results: pd.DataFrame,
) -> None:
    counts = links["link_type"].value_counts()
    controls = program_results[program_results["positive_control"]].copy()
    schemes = program_results[~program_results["positive_control"]].copy()
    miss_counts = program_results.loc[
        ~program_results["strict_pair_status"].eq("source_aligned_hit"),
        "strict_pair_status",
    ].value_counts()
    lines = [
        "# Cross-layer pair projection",
        "",
        "Observed TG pairs are projected into an independent iTE pair bank. TG",
        "edges are never inserted into the historical iTE graph.",
        "",
        "## Results",
        "",
        f"- Observed typed iTE pairs: {len(ite):,}",
        f"- Observed typed TG query pairs: {len(tg):,}",
        f"- Papers found by both searches, assigned to TG, and removed from iTE: {len(source_overlaps):,}",
        f"- Cross-layer pair links: {len(links):,}",
        f"- Exact-overlap/known-positive-control links held out from ranked results: {len(excluded_overlap_controls):,}",
        f"- Positive-control programs recovered with source alignment: {(controls['strict_pair_status'] == 'source_aligned_hit').sum():,}/{len(controls):,}",
        f"- New-scheme programs recovered with source alignment: {(schemes['strict_pair_status'] == 'source_aligned_hit').sum():,}/{len(schemes):,}",
        f"- Programs missing a source-aligned iTE pair: {miss_counts.get('no_iTE_source_pair', 0):,}",
        f"- Programs missing a qualified TG grounding pair: {miss_counts.get('no_TG_grounding_pair', 0):,}",
        f"- Reviewable top bridges exported: {len(top):,}",
        f"- Representative paths visualized: {len(representative):,}",
        "",
        "### Link types",
        "",
    ]
    lines.extend(f"- `{name}`: {count:,}" for name, count in counts.items())
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `direct_pair_overlap` is precedent, not novelty.",
            "- Papers retrieved by both searches are labeled `iTE|TG`, included in TG queries, and excluded from iTE evidence.",
            "- Known TG positive controls are kept only in the audit export and omitted from ranked/representative results.",
            "- Every curated program bridge must intersect that program's declared iTE source-paper set; lever-only matches are rejected.",
            "- Source alignment is applied before the per-program top-20 export cap; 20 is a display ceiling, not a full candidate count.",
            "- Program-level misses distinguish an absent source-supported iTE pair from an absent TG grounding pair.",
            "- No concept label or mechanism assignment is rewritten by this overlap filter.",
            "- Exact/family endpoint links are retrieval evidence and require a mechanism check.",
            "- `curated_program_bridge` is a designed transfer hypothesis, not observed causality.",
            "- Outcome-only bridges are retained in the complete file but excluded from the top list.",
            "- Transfer scores are transparent 0-100 retrieval priorities, not probabilities of success.",
            "",
            "## Main files",
            "",
            "- `RESULTS_CN.md`: Chinese interpretation of counts, representative closures, and limits.",
            "- `ite_pair_bank.csv`: observed iTE typed pairs with temporal and paper support.",
            "- `tg_pair_queries.csv`: observed TG typed pairs kept in a separate layer.",
            "- `cross_layer_pair_links.csv`: every exact, audited-family, and curated bridge.",
            "- `source_overlap_papers.csv`: papers retrieved by both searches, assigned to TG, and excluded from iTE evidence.",
            "- `excluded_overlap_controls.csv`: exact pair overlaps and known TG positive controls omitted from ranked results.",
            "- `exact_pair_overlaps.csv`: one row per unique exact pair overlap.",
            "- `program_level_results.csv`: all 20 programs, including strict source-aligned misses.",
            "- `positive_control_program_results.csv`: all positive controls at program level.",
            "- `new_scheme_program_results.csv`: all new/upgrade schemes at program level.",
            "- `positive_control_bridges.csv`: source-aligned positive-control pair links.",
            "- `new_scheme_bridges.csv`: source-aligned new/upgrade pair links.",
            "- `top_pair_bridges.csv`: high-value review queue excluding overlaps, positive controls, and outcome-only links.",
            "- `representative_pair_bridges.csv`: paths used in the visual result.",
            "- `representative_pair_projection.svg`: static vector visualization.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    concepts = pd.read_csv(CONCEPTS)
    relations = pd.read_csv(RELATIONS)
    vocabulary = pd.read_csv(VOCABULARY)
    audit = pd.read_csv(OVERLAP_AUDIT)
    papers = pd.read_csv(PAPERS)
    programs = pd.read_csv(PROGRAMS)
    cards = pd.read_csv(CARDS)
    allowed_assignments = strict_paper_node_assignments(concepts, cards)

    ite = build_pair_bank(
        relations, concepts, papers, vocabulary, "iTE", allowed_assignments
    )
    tg = build_pair_bank(
        relations, concepts, papers, vocabulary, "TG", allowed_assignments
    )
    coupled = build_pair_bank(
        relations, concepts, papers, vocabulary, "iTE|TG", allowed_assignments
    )
    # The overlap table is an automated audit queue, not a controlled family
    # crosswalk.  It is therefore not used to generate scientific bridges.
    exact_family = exact_and_family_links(ite, tg, audit.iloc[0:0])
    curated = curated_program_links(ite, tg, vocabulary, programs)
    links = pd.concat([exact_family, curated], ignore_index=True)
    links = attach_pair_labels(links, ite, tg)
    links = add_closure_fields(links)
    tg_paper_count = int(
        papers["source_membership"].map(lambda value: has_layer(value, "TG")).sum()
    )
    links = add_transfer_score(links, tg_paper_count)
    links = links.sort_values(
        ["transfer_score", "link_type", "tg_pair_id", "ite_pair_id"],
        ascending=[False, True, True, True],
    ).drop_duplicates("link_id")
    program_results = build_program_level_results(
        programs, links, ite, tg, vocabulary
    )
    exact_pair_overlaps = links[links["link_type"].eq("direct_pair_overlap")].copy()
    positive_program_ids = set(
        programs.loc[programs["positive_control"].fillna(False), "program_id"]
    )
    positive_control_bridges = links[
        links["link_type"].eq("curated_program_bridge")
        & links["program_id"].isin(positive_program_ids)
    ].copy()
    new_scheme_bridges = links[
        links["link_type"].eq("curated_program_bridge")
        & ~links["program_id"].isin(positive_program_ids)
    ].copy()
    source_overlaps = papers[papers["source_membership"].eq("iTE|TG")].copy()
    source_overlaps.insert(2, "dedupe_basis", "normalized_doi_exact_match")
    source_overlaps.insert(3, "analysis_assignment", "TG")
    source_overlaps.insert(4, "excluded_from_iTE", True)
    excluded_overlap_controls = links[
        links["novelty_status"].isin(NON_ACTIONABLE_NOVELTY)
    ].copy()
    top = select_top_bridges(links)
    representative = representative_bridges(links, programs)

    ite.to_csv(OUT / "ite_pair_bank.csv", index=False)
    tg.to_csv(OUT / "tg_pair_queries.csv", index=False)
    coupled.to_csv(OUT / "coupled_positive_control_pairs.csv", index=False)
    links.to_csv(OUT / "cross_layer_pair_links.csv", index=False)
    exact_pair_overlaps.to_csv(OUT / "exact_pair_overlaps.csv", index=False)
    program_results.to_csv(OUT / "program_level_results.csv", index=False)
    program_results[program_results["positive_control"]].to_csv(
        OUT / "positive_control_program_results.csv", index=False
    )
    program_results[~program_results["positive_control"]].to_csv(
        OUT / "new_scheme_program_results.csv", index=False
    )
    positive_control_bridges.to_csv(
        OUT / "positive_control_bridges.csv", index=False
    )
    new_scheme_bridges.to_csv(OUT / "new_scheme_bridges.csv", index=False)
    source_overlaps.to_csv(OUT / "source_overlap_papers.csv", index=False)
    excluded_overlap_controls.to_csv(OUT / "excluded_overlap_controls.csv", index=False)
    top.to_csv(OUT / "top_pair_bridges.csv", index=False)
    representative.to_csv(OUT / "representative_pair_bridges.csv", index=False)
    draw_representative_paths(representative)
    write_readme(
        ite,
        tg,
        links,
        top,
        representative,
        source_overlaps,
        excluded_overlap_controls,
        program_results,
    )

    print((OUT / "README.md").read_text(encoding="utf-8"))
    print("\nRepresentative bridges")
    print(
        representative[
            [
                "program_id",
                "transfer_score",
                "ite_pair_label",
                "tg_pair_label",
                "program_title_cn",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
