"""Build a task-specific typed concept layer for iTE -> TG transfer.

This deliberately does not reproduce NMI's homogeneous key-phrase graph.
It reuses the audited paper/concept map and claim evidence, separates observed
source concepts from curated transfer targets, and records only typed
co-reporting at paper level (not inferred causality).
"""

from __future__ import annotations

from hashlib import sha1
from pathlib import Path
from difflib import SequenceMatcher
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "task_typed_concept_layer"

PAPERS = ROOT / "final_concept_layer" / "final_paper_qc.csv"
PAPER_CONCEPTS = ROOT / "final_concept_layer" / "final_paper_concept_map.csv"
CARDS = ROOT / "ite_tg_complementarity" / "ite_mechanism_cards_v2.csv"
PROGRAMS = ROOT / "ite_tg_complementarity" / "ite_tg_complementarity_programs.csv"


ROLE_BY_CONCEPT_TYPE = {
    "material_entity": "material_system",
    "material_system": "material_system",
    "gel_microstructure": "structure_state",
    "transport_mechanism": "mechanism",
    "redox_chemistry": "mechanism",
    "solvation_entropy": "mechanism",
    "electrode_interface": "mechanism",
    "solid_state_mechanism": "mechanism",
    "device_mechanism": "mechanism",
    "phase_or_species_transition": "mechanism",
    "property_metric": "outcome_property",
    "device_function": "device_context",
    "characterization_method": "evidence_method",
    "computational_method": "evidence_method",
}

RECOMMENDATION_ROLES = {
    "material_system",
    "intervention",
    "structure_state",
    "mechanism",
}

ROLE_ORDER = {
    "material_system": 0,
    "intervention": 1,
    "structure_state": 2,
    "mechanism": 3,
    "outcome_property": 4,
    "device_context": 5,
    "evidence_method": 6,
}


def text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def split_terms(value: object) -> list[str]:
    return [text(part) for part in re.split(r"\s*;\s*", text(value)) if text(part)]


def stable_id(prefix: str, *values: object) -> str:
    payload = "\x1f".join(text(value).casefold() for value in values)
    return f"{prefix}_{sha1(payload.encode('utf-8')).hexdigest()[:12]}"


def source_concepts(papers: pd.DataFrame, mapped: pd.DataFrame) -> pd.DataFrame:
    metadata = papers.set_index("paper_id")
    rows: list[dict[str, object]] = []
    for item in mapped.itertuples(index=False):
        role = ROLE_BY_CONCEPT_TYPE.get(text(item.concept_type))
        if not role or item.paper_id not in metadata.index:
            continue
        paper = metadata.loc[item.paper_id]
        label = text(item.canonical_concept)
        if not label:
            continue
        rows.append(
            {
                "paper_id": item.paper_id,
                "source_membership": paper.source_membership,
                "year": paper.year,
                "title": paper.title,
                "doi": paper.doi,
                "node_id": stable_id("TC", role, label),
                "node_label": label,
                "node_role": role,
                "node_subtype": text(item.concept_subtype),
                "source_concept_type": text(item.concept_type),
                "provenance": "audited_paper_concept_map",
                "evidence_text": text(item.evidence_text),
                "evidence_status": text(item.extraction_method),
                "confidence": item.confidence,
                "observed_in_source": True,
            }
        )
    return pd.DataFrame(rows)


def claim_nodes(papers: pd.DataFrame, cards: pd.DataFrame) -> pd.DataFrame:
    metadata = papers.set_index("paper_id")
    specs = [
        ("mechanism_concepts", "mechanism", "claim_mechanism_concept"),
        ("outcome_metric_concepts", "outcome_property", "claim_outcome_concept"),
        ("device_context_concepts", "device_context", "claim_device_context"),
    ]
    rows: list[dict[str, object]] = []
    for card in cards.itertuples(index=False):
        if card.paper_id not in metadata.index:
            continue
        paper = metadata.loc[card.paper_id]
        for column, role, provenance in specs:
            for label in split_terms(getattr(card, column)):
                rows.append(
                    {
                        "paper_id": card.paper_id,
                        "source_membership": paper.source_membership,
                        "year": paper.year,
                        "title": paper.title,
                        "doi": paper.doi,
                        "node_id": stable_id("TC", role, label),
                        "node_label": label,
                        "node_role": role,
                        "node_subtype": provenance,
                        "source_concept_type": provenance,
                        "provenance": provenance,
                        "evidence_text": text(card.exact_abstract_evidence_bundle)
                        or text(card.insight_claim),
                        "evidence_status": text(card.evidence_tier),
                        "confidence": card.source_evidence_score,
                        "observed_in_source": True,
                    }
                )

        lever_evidence = (
            text(card.intervention_evidence_sentence)
            or text(card.mechanism_evidence_sentence)
            or text(card.insight_claim)
        )
        for code in split_terms(card.transferable_lever_codes):
            label = code.replace("_", " ")
            rows.append(
                {
                    "paper_id": card.paper_id,
                    "source_membership": paper.source_membership,
                    "year": paper.year,
                    "title": paper.title,
                    "doi": paper.doi,
                    "node_id": stable_id("TC", "intervention", code),
                    "node_label": label,
                    "node_role": "intervention",
                    "node_subtype": "transferable_lever",
                    "source_concept_type": "transferable_lever",
                    "provenance": "curated_transferable_lever_assignment",
                    "evidence_text": lever_evidence,
                    "evidence_status": text(card.evidence_tier),
                    "confidence": card.source_evidence_score,
                    "observed_in_source": True,
                }
            )
    return pd.DataFrame(rows)


def deduplicate_paper_nodes(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["confidence_numeric"] = pd.to_numeric(frame["confidence"], errors="coerce")
    frame["evidence_length"] = frame["evidence_text"].fillna("").str.len()
    frame = frame.sort_values(
        ["paper_id", "node_id", "confidence_numeric", "evidence_length"],
        ascending=[True, True, False, False],
        na_position="last",
    )
    frame = frame.drop_duplicates(["paper_id", "node_id"], keep="first")
    return frame.drop(columns=["confidence_numeric", "evidence_length"])


def add_graph_flags(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    stats = (
        frame.groupby(["node_id", "node_label", "node_role"], as_index=False)
        .agg(
            document_frequency=("paper_id", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            source_memberships=(
                "source_membership",
                lambda values: "; ".join(sorted(set(map(text, values)))),
            ),
            provenance=("provenance", lambda values: "; ".join(sorted(set(map(text, values))))),
        )
    )
    # Unlike NMI, one-word controlled materials (for example, ionogel) remain valid.
    stats["historical_graph_eligible"] = stats["document_frequency"] >= 2
    stats["recommendation_target_eligible"] = (
        stats["historical_graph_eligible"]
        & stats["node_role"].isin(RECOMMENDATION_ROLES)
    )
    flags = stats[["node_id", "document_frequency", "historical_graph_eligible", "recommendation_target_eligible"]]
    return frame.merge(flags, on="node_id", how="left"), stats


def paper_relations(frame: pd.DataFrame) -> pd.DataFrame:
    """Create typed co-reporting edges without asserting a causal direction."""
    rows: list[dict[str, object]] = []
    for paper_id, group in frame.groupby("paper_id", sort=False):
        nodes = group.sort_values(
            "node_role", key=lambda col: col.map(ROLE_ORDER).fillna(99)
        ).to_dict("records")
        for i, left in enumerate(nodes):
            for right in nodes[i + 1 :]:
                if left["node_role"] == right["node_role"]:
                    continue
                source, target = left, right
                if ROLE_ORDER.get(source["node_role"], 99) > ROLE_ORDER.get(target["node_role"], 99):
                    source, target = target, source
                rows.append(
                    {
                        "relation_id": stable_id("TR", paper_id, source["node_id"], target["node_id"]),
                        "paper_id": paper_id,
                        "year": source["year"],
                        "source_node_id": source["node_id"],
                        "source_role": source["node_role"],
                        "relation_type": "typed_co_reported_in_abstract",
                        "target_node_id": target["node_id"],
                        "target_role": target["node_role"],
                        "evidence_scope": "same_paper_not_causal",
                    }
                )
    return pd.DataFrame(rows).drop_duplicates("relation_id")


def curated_targets(programs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for item in programs.itertuples(index=False):
        values = [
            ("intervention", item.source_lever_code, item.source_lever_cn),
            ("material_system", item.target_redox_family, item.target_redox_system_cn),
            ("bottleneck", item.program_rule_code, item.TG_bottleneck_cn),
            ("proposed_design", item.program_id, item.concrete_iTE_plus_TG_design_cn),
        ]
        for role, code, label in values:
            rows.append(
                {
                    "program_id": item.program_id,
                    "program_rule_code": item.program_rule_code,
                    "node_id": stable_id("TT", role, code),
                    "node_role": role,
                    "node_code": text(code),
                    "node_label": text(label),
                    "status": "curated_transfer_target_not_observed_source_fact",
                    "priority_score": item.priority_score,
                    "candidate_status": item.candidate_status,
                }
            )
    return pd.DataFrame(rows).drop_duplicates(["program_id", "node_role", "node_id"])


def normalized_tokens(label: object) -> tuple[str, ...]:
    normalized = re.sub(r"[^a-z0-9+/-]+", " ", text(label).casefold())
    return tuple(token for token in normalized.split() if token)


def node_overlap_audit(vocabulary: pd.DataFrame) -> pd.DataFrame:
    """Flag similar labels for review; never merge them automatically."""
    rows: list[dict[str, object]] = []
    records = vocabulary.to_dict("records")

    # Exact label reused in different scientific roles.
    by_label: dict[str, list[dict[str, object]]] = {}
    for record in records:
        by_label.setdefault(text(record["node_label"]).casefold(), []).append(record)
    for label_records in by_label.values():
        roles = {record["node_role"] for record in label_records}
        if len(roles) < 2:
            continue
        for i, left in enumerate(label_records):
            for right in label_records[i + 1 :]:
                if left["node_role"] == right["node_role"]:
                    continue
                rows.append(
                    {
                        "audit_type": "same_label_different_role",
                        "left_node_id": left["node_id"],
                        "left_role": left["node_role"],
                        "left_label": left["node_label"],
                        "left_document_frequency": left["document_frequency"],
                        "right_node_id": right["node_id"],
                        "right_role": right["node_role"],
                        "right_label": right["node_label"],
                        "right_document_frequency": right["document_frequency"],
                        "string_similarity": 1.0,
                        "recommended_action": "retain_role_specific_nodes_review_typing",
                    }
                )

    # Nested or near-identical labels inside a role.
    for role, group in vocabulary.groupby("node_role", sort=False):
        role_records = group.to_dict("records")
        token_sets = [set(normalized_tokens(record["node_label"])) for record in role_records]
        for i, left in enumerate(role_records):
            left_tokens = token_sets[i]
            if not left_tokens:
                continue
            for j in range(i + 1, len(role_records)):
                right = role_records[j]
                right_tokens = token_sets[j]
                if not right_tokens:
                    continue
                nested = left_tokens < right_tokens or right_tokens < left_tokens
                similarity = SequenceMatcher(
                    None,
                    text(left["node_label"]).casefold(),
                    text(right["node_label"]).casefold(),
                ).ratio()
                if not nested and similarity < 0.88:
                    continue
                rows.append(
                    {
                        "audit_type": "nested_same_role" if nested else "near_duplicate_same_role",
                        "left_node_id": left["node_id"],
                        "left_role": role,
                        "left_label": left["node_label"],
                        "left_document_frequency": left["document_frequency"],
                        "right_node_id": right["node_id"],
                        "right_role": role,
                        "right_label": right["node_label"],
                        "right_document_frequency": right["document_frequency"],
                        "string_similarity": round(similarity, 4),
                        "recommended_action": "retain_both_until_semantic_role_review",
                    }
                )
    return pd.DataFrame(rows).drop_duplicates(
        ["audit_type", "left_node_id", "right_node_id"]
    )


def paper_overlap_audit(concepts: pd.DataFrame) -> pd.DataFrame:
    """Find nested same-role concepts that co-occur in a single paper."""
    rows: list[dict[str, object]] = []
    for (paper_id, role), group in concepts.groupby(["paper_id", "node_role"], sort=False):
        records = group[["node_id", "node_label", "title", "doi"]].to_dict("records")
        token_sets = [set(normalized_tokens(record["node_label"])) for record in records]
        for i, left in enumerate(records):
            for j in range(i + 1, len(records)):
                right = records[j]
                if not token_sets[i] or not token_sets[j]:
                    continue
                if not (token_sets[i] < token_sets[j] or token_sets[j] < token_sets[i]):
                    continue
                rows.append(
                    {
                        "paper_id": paper_id,
                        "title": left["title"],
                        "doi": left["doi"],
                        "node_role": role,
                        "left_node_id": left["node_id"],
                        "left_label": left["node_label"],
                        "right_node_id": right["node_id"],
                        "right_label": right["node_label"],
                        "review_status": "retained_not_auto_merged",
                    }
                )
    return pd.DataFrame(rows)


def write_summary(
    papers: pd.DataFrame,
    concepts: pd.DataFrame,
    vocabulary: pd.DataFrame,
    relations: pd.DataFrame,
    targets: pd.DataFrame,
    overlap_audit: pd.DataFrame,
    paper_overlap: pd.DataFrame,
    missing_papers: pd.DataFrame,
) -> None:
    observed = concepts.groupby("node_role", as_index=False).agg(
        paper_concept_rows=("node_id", "size"),
        papers=("paper_id", "nunique"),
        unique_nodes=("node_id", "nunique"),
    )
    eligible = (
        vocabulary[vocabulary["historical_graph_eligible"]]
        .groupby("node_role", as_index=False)
        .agg(graph_eligible_nodes=("node_id", "nunique"))
    )
    role_summary = (
        observed.merge(eligible, on="node_role", how="left")
        .fillna({"graph_eligible_nodes": 0})
        .sort_values("paper_concept_rows", ascending=False)
    )
    role_summary["graph_eligible_nodes"] = role_summary["graph_eligible_nodes"].astype(int)
    role_summary.to_csv(OUT / "typed_role_summary.csv", index=False)

    covered = concepts["paper_id"].nunique()
    lines = [
        "# Task-specific typed concept layer",
        "",
        "This layer supports iTE-to-TG mechanism transfer. It is not a clone of",
        "NMI's homogeneous key-phrase graph.",
        "",
        "## Contract",
        "",
        "- Source facts and curated transfer targets are stored separately.",
        "- A paper may contain many typed nodes.",
        "- Paper-level edges mean typed co-reporting only; they do not assert causality.",
        "- One-word controlled materials are allowed, unlike NMI's two-word graph filter.",
        "- Historical graph eligibility currently requires occurrence in at least two papers.",
        "- Recommendation targets exclude outcome, device-context, and method nodes.",
        "",
        "## Current build",
        "",
        f"- Deduplicated papers available: {len(papers):,}",
        f"- Papers with at least one typed node: {covered:,}",
        f"- Paper-node records: {len(concepts):,}",
        f"- Unique typed nodes: {len(vocabulary):,}",
        f"- Typed paper-level co-reporting relations: {len(relations):,}",
        f"- Curated transfer-target records: {len(targets):,}",
        f"- Vocabulary overlap pairs retained for review: {len(overlap_audit):,}",
        f"- Within-paper nested pairs retained for review: {len(paper_overlap):,}",
        f"- Papers queued for missing-node review: {len(missing_papers):,}",
        "",
        "## Files",
        "",
        "- `paper_typed_concepts.csv`: observed or audited paper-node assignments with evidence.",
        "- `typed_concept_vocabulary.csv`: global node statistics and eligibility flags.",
        "- `paper_typed_relations.csv`: non-causal typed co-reporting edges.",
        "- `curated_transfer_targets.csv`: hypothesis/decision nodes kept separate from source facts.",
        "- `typed_role_summary.csv`: coverage by node role.",
        "- `typed_node_overlap_audit.csv`: nested, near-duplicate, or cross-role labels; no automatic merge.",
        "- `paper_nested_concept_audit.csv`: similar same-role concepts retained within individual papers.",
        "- `missing_typed_node_review_queue.csv`: papers requiring a later evidence-grounded extraction pass.",
        "",
        "## Important limitation",
        "",
        "This is a restructuring of the existing audited concept and claim layers, not a",
        "fresh open-ended LLM extraction from every abstract. Missing typed concepts should",
        "be added in a later evidence-grounded extraction pass without replacing this layer.",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    papers = pd.read_csv(PAPERS)
    mapped = pd.read_csv(PAPER_CONCEPTS)
    cards = pd.read_csv(CARDS)
    programs = pd.read_csv(PROGRAMS)

    concepts = pd.concat(
        [source_concepts(papers, mapped), claim_nodes(papers, cards)],
        ignore_index=True,
    )
    concepts = deduplicate_paper_nodes(concepts)
    concepts, vocabulary = add_graph_flags(concepts)
    relations = paper_relations(concepts)
    targets = curated_targets(programs)
    overlap_audit = node_overlap_audit(vocabulary)
    paper_overlap = paper_overlap_audit(concepts)
    missing_papers = papers[~papers["paper_id"].isin(concepts["paper_id"])].copy()
    missing_papers["review_reason"] = "no_typed_node_in_existing_audited_layers"
    missing_papers["recommended_source"] = missing_papers["abstract"].fillna("").map(
        lambda value: "abstract_reextraction" if text(value) else "pdf_or_external_abstract_recovery"
    )

    concepts.to_csv(OUT / "paper_typed_concepts.csv", index=False)
    vocabulary.to_csv(OUT / "typed_concept_vocabulary.csv", index=False)
    relations.to_csv(OUT / "paper_typed_relations.csv", index=False)
    targets.to_csv(OUT / "curated_transfer_targets.csv", index=False)
    overlap_audit.to_csv(OUT / "typed_node_overlap_audit.csv", index=False)
    paper_overlap.to_csv(OUT / "paper_nested_concept_audit.csv", index=False)
    missing_papers.to_csv(OUT / "missing_typed_node_review_queue.csv", index=False)
    write_summary(
        papers,
        concepts,
        vocabulary,
        relations,
        targets,
        overlap_audit,
        paper_overlap,
        missing_papers,
    )

    print((OUT / "README.md").read_text(encoding="utf-8"))
    print(pd.read_csv(OUT / "typed_role_summary.csv").to_string(index=False))


if __name__ == "__main__":
    main()
