from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import sentence_transformers
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "minimal_clean_concept_layer"
FLOW = ROOT / "mechanism_transfer_workflow"
DEFAULT_OUT = ROOT / "ite_insight_transfer"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_SNAPSHOT_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
SCRIPT_VERSION = "1.1.0"
RANDOM_STATE = 27

MATERIAL_TYPES = {"material_entity", "material_system"}
MECHANISM_TYPES = {
    "transport_mechanism",
    "solvation_entropy",
    "gel_microstructure",
    "phase_or_species_transition",
    "electrode_interface",
    "redox_chemistry",
    "solid_state_mechanism",
    "device_mechanism",
}

DIRECT_ITE_PHRASE_PATTERN = re.compile(
    r"\b(?:ionic|iontronic)[ -]?(?:thermoelectric|thermo-electric|"
    r"thermopower|seebeck|thermal potential|thermovoltage)\b|"
    r"\bi-?te\b",
    re.I,
)
THERMAL_ION_PROCESS_PATTERN = re.compile(
    r"\b(?:thermodiffusion|soret effect|thermophor\w*|thermo.?osmos\w*|"
    r"thermoelectric field|thermally generated electric field|"
    r"heat of transport)\b|"
    r"\b(?:temperature|thermal)[ -]?gradient\b[^;]{0,100}"
    r"\b(?:ion(?:ic)? migration|ion transport|proton transport|"
    r"cation transport|anion transport)\b|"
    r"\b(?:ion(?:ic)? migration|ion transport|proton transport|"
    r"cation transport|anion transport)\b[^;]{0,100}"
    r"\b(?:temperature|thermal)[ -]?gradient\b",
    re.I,
)
SOFT_IONIC_SYSTEM_PATTERN = re.compile(
    r"\b(?:ionogel|ionic hydrogel|polymer electrolyte|electrolyte gel|"
    r"cellulose ionic conductor)\b",
    re.I,
)
MIXED_IONIC_CONDUCTOR_PATTERN = re.compile(
    r"\b(?:mixed ionic[- ]electronic conductor|ionic conductor|"
    r"superionic(?: conductor| system)?)\b",
    re.I,
)
THERMOELECTRIC_OUTPUT_PATTERN = re.compile(
    r"\b(?:thermoelectric|thermo-electric|thermopower|seebeck|"
    r"thermovoltage)\b",
    re.I,
)
THERMOPOWER_OUTPUT_PATTERN = re.compile(
    r"\b(?:thermopower|seebeck|thermovoltage)\b",
    re.I,
)
EXTERNAL_TE_MODULE_PATTERN = re.compile(
    r"\b(?:commercial thermoelectric (?:generator|module)|"
    r"coupled (?:to|with) (?:a )?commercial thermoelectric "
    r"(?:generator|module))\b",
    re.I,
)
COUPLED_TG_SOURCE_PATTERN = re.compile(
    r"\b(?:thermogalvanic|thermo-galvanic|thermocell|"
    r"thermoelectrochemical|redox thermocell|gel thermocell|"
    r"redox[- ](?:reaction|couple|entropy|electrode)s?|"
    r"thermoelectric[- ]electrochemical)\b",
    re.I,
)
CLEAR_REVIEW_PATTERN = re.compile(
    r"\b(?:review|overview|recent advances|recent progress|"
    r"research progress|progress of|roadmap|bibliometric|perspective|"
    r"state of the art)\b",
    re.I,
)
ABSTRACT_REVIEW_PATTERN = re.compile(
    r"\b(?:this review|in this review|we (?:briefly )?review|"
    r"this (?:article|paper) reviews|we (?:present|provide) (?:a )?"
    r"summari[sz]ation|we summarize|review summarizes|reviewed "
    r"strategies|in this perspective|this perspective article|"
    r"aims? to (?:give|provide) an overview|"
    r"this (?:paper|article) (?:first )?summarizes|"
    r"we discuss (?:the )?(?:principle|fundamentals|similarities|"
    r"recent progress)|serves as a guide|great progress was recently "
    r"made)\b",
    re.I,
)
CAUSAL_PATTERN = re.compile(
    r"\b(?:because|due to|through|via|thereby|thus|owing to|attribut|"
    r"stem|lead|result|enable|enhanc|increase|decrease|improv|boost|"
    r"suppress|promot|facilitat|regulat|control|govern|induc|drive|"
    r"confine|stabiliz|modulat|tune|alter|contribut|assist|augment|"
    r"convert|creat|generat|provide|yield)\w*\b",
    re.I,
)
INTERVENTION_PATTERN = re.compile(
    r"\b(?:we report|we propose|we develop|we design|we demonstrate|"
    r"we introduce|herein|incorporat|functionaliz|cross.?link|dop|"
    r"replace|substitut|engineer|modif|add|load|confine|coat|embed|"
    r"construct|fabricat|integrat|coupl|complexation|coordination|"
    r"present|utiliz|append|employ|prepare|synthes|assemble|apply)\w*\b",
    re.I,
)
OUTCOME_PATTERN = re.compile(
    r"\b(?:seebeck|thermopower|power density|energy density|conductiv|"
    r"efficien|stability|stretch|strength|current density|voltage|"
    r"diffusion|mobility|resistance|thermal conductivity|output|"
    r"performance|sensitivity|response time|figure of merit|zt|"
    r"robust|mechanic|durab|thermovoltage|power factor)\w*\b",
    re.I,
)
QUANTITATIVE_PATTERN = re.compile(
    r"(?:[-+]?\d+(?:\.\d+)?\s*(?:%|mV|V|kV|µV|uV|mW|µW|uW|W|"
    r"mA|µA|uA|A(?=\s|$)|mS|µS|uS|S|K|°C|Pa|kPa|MPa|GPa|"
    r"ms|s|h|J|mJ|µJ|uJ|mW\s*m[-−]?\s*2|W\s*m[-−]?\s*2))"
    r"(?![A-Za-z])",
)
GENERIC_SENTENCE_PATTERN = re.compile(
    r"\b(?:show promise|promising avenue|important for|great potential|"
    r"critical challenge|has attracted|are becoming increasingly|"
    r"this work offers|future applications)\b",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build claim-level iTE-evidenced insights, trace later TG semantic "
            "alignment, and generate TG translation review queues."
        )
    )
    parser.add_argument(
        "--freeze-year",
        type=int,
        default=2025,
        help="Last complete year used for directional analysis (default: 2025).",
    )
    parser.add_argument(
        "--theme-cosine",
        type=float,
        default=0.70,
        help="Average-linkage cosine similarity used to group iTE claims.",
    )
    parser.add_argument(
        "--possible-alignment",
        type=float,
        default=0.66,
        help="Lower threshold for a possible cross-corpus analogy.",
    )
    parser.add_argument(
        "--strong-alignment",
        type=float,
        default=0.72,
        help="Threshold for a strong semantic audit candidate.",
    )
    parser.add_argument(
        "--evidence-cosine",
        type=float,
        default=0.60,
        help=(
            "Minimum claim-to-exact-causal-sentence cosine for the primary "
            "theme analysis."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, value: str) -> str:
    token = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}_{token}"


def normalize_space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def split_mechanism_claims(value: object) -> list[str]:
    text = normalize_space(value)
    if not text:
        return []
    raw_parts = [normalize_space(part) for part in re.split(r"\s*;\s*", text)]
    raw_parts = [part for part in raw_parts if part]
    if len(raw_parts) <= 1:
        return [text]
    claims: list[str] = []
    carry = ""
    for part in raw_parts:
        words = part.split()
        part_is_directional = bool(
            CAUSAL_PATTERN.search(part)
            or OUTCOME_PATTERN.search(part)
            or re.search(
                r"\b(?:provide|give|yield|produce|convert|switch|maintain|"
                r"raise|lower|change|determine|allow|achieve|migrate|"
                r"create|form|generate)\w*\b",
                part,
                re.I,
            )
        )
        if len(words) < 5 or not part_is_directional:
            carry = f"{carry}; {part}".strip("; ")
            continue
        if carry:
            part = f"{carry}; {part}"
            carry = ""
        claims.append(part)
    if carry:
        if claims:
            claims[-1] = f"{claims[-1]}; {carry}"
        else:
            claims.append(text)
    return claims or [text]


def split_sentences(value: object) -> list[str]:
    text = normalize_space(value)
    if not text:
        return []
    # Stored evidence must remain an exact substring of the normalized source
    # abstract.  Token repair and truncation are left to the embedding model.
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9αβγΔ])", text)
    cleaned = []
    for sentence in sentences:
        sentence = normalize_space(sentence)
        words = sentence.split()
        if len(words) < 7:
            continue
        cleaned.append(sentence)
    if not cleaned and text:
        cleaned = [text]
    return cleaned


def is_likely_review(row: pd.Series) -> bool:
    title = normalize_space(row.get("title", ""))
    abstract = normalize_space(row.get("abstract", ""))
    mechanism = normalize_space(row.get("mechanism_raw", ""))
    return bool(
        CLEAR_REVIEW_PATTERN.search(title)
        or ABSTRACT_REVIEW_PATTERN.search(abstract)
        or ABSTRACT_REVIEW_PATTERN.search(mechanism)
    )


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    papers = pd.read_csv(DATA / "final_paper_index.csv")
    mapping = pd.read_csv(DATA / "final_paper_concept_map.csv")
    vocab = pd.read_csv(FLOW / "pure_mechanism_vocabulary.csv")
    papers["year"] = pd.to_numeric(papers["year"], errors="coerce")
    for column in [
        "title",
        "abstract",
        "material_raw",
        "mechanism_raw",
        "journal",
        "doi",
        "source_membership",
    ]:
        papers[column] = papers[column].fillna("").map(normalize_space)
    return papers, mapping, vocab


def load_or_initialize_adjudication(
    path: Path,
    id_column: str,
    review_columns: list[str],
) -> pd.DataFrame:
    columns = [id_column, *review_columns]
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)
        return pd.DataFrame(columns=columns)
    frame = pd.read_csv(path, dtype=str).fillna("")
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(
            f"Adjudication file {path} is missing columns: {missing}"
        )
    if frame[id_column].duplicated().any():
        duplicates = frame.loc[
            frame[id_column].duplicated(keep=False), id_column
        ].tolist()
        raise ValueError(
            f"Adjudication file {path} has duplicate IDs: {duplicates[:5]}"
        )
    return frame[columns].copy()


def review_value_is_true(value: object) -> bool:
    return normalize_space(value).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "include",
        "approved",
    }


def concept_context(mapping: pd.DataFrame) -> pd.DataFrame:
    frame = mapping[
        ["paper_id", "canonical_concept", "concept_type"]
    ].drop_duplicates()
    rows = []
    for paper_id, group in frame.groupby("paper_id"):
        types = group["concept_type"]
        rows.append(
            {
                "paper_id": paper_id,
                "mechanism_concepts": "; ".join(
                    sorted(
                        group.loc[
                            types.isin(MECHANISM_TYPES), "canonical_concept"
                        ].unique()
                    )
                ),
                "material_concepts": "; ".join(
                    sorted(
                        group.loc[
                            types.isin(MATERIAL_TYPES), "canonical_concept"
                        ].unique()
                    )
                ),
                "outcome_metric_concepts": "; ".join(
                    sorted(
                        group.loc[
                            types.eq("property_metric"), "canonical_concept"
                        ].unique()
                    )
                ),
                "device_context_concepts": "; ".join(
                    sorted(
                        group.loc[
                            types.eq("device_function"), "canonical_concept"
                        ].unique()
                    )
                ),
            }
        )
    return pd.DataFrame(rows)


def classify_source_scope(
    papers: pd.DataFrame,
    mapping: pd.DataFrame,
    vocab: pd.DataFrame,
) -> pd.DataFrame:
    pure_ids = set(vocab["concept_id"])
    pure_papers = set(mapping.loc[mapping["concept_id"].isin(pure_ids), "paper_id"])
    solid_papers = set(
        mapping.loc[
            mapping["concept_type"].eq("solid_state_mechanism")
            | mapping["concept_subtype"].eq("solid thermoelectric family"),
            "paper_id",
        ]
    )
    source = papers[papers["source_membership"].eq("iTE")].copy()
    source["has_curated_ionic_mechanism"] = source["paper_id"].isin(pure_papers)
    source["has_solid_state_marker"] = source["paper_id"].isin(solid_papers)
    title_mechanism = source["title"] + " " + source["mechanism_raw"]
    direct_phrase = title_mechanism.map(
        lambda value: bool(DIRECT_ITE_PHRASE_PATTERN.search(value))
    )
    thermal_ion_process = title_mechanism.map(
        lambda value: bool(THERMAL_ION_PROCESS_PATTERN.search(value))
    )
    soft_ionic_with_output = title_mechanism.map(
        lambda value: bool(SOFT_IONIC_SYSTEM_PATTERN.search(value))
        and bool(THERMOELECTRIC_OUTPUT_PATTERN.search(value))
    )
    mixed_ionic_with_output = title_mechanism.map(
        lambda value: bool(MIXED_IONIC_CONDUCTOR_PATTERN.search(value))
        and bool(THERMOPOWER_OUTPUT_PATTERN.search(value))
    )
    external_module = title_mechanism.map(
        lambda value: bool(EXTERNAL_TE_MODULE_PATTERN.search(value))
    )
    coupled_tg_source = title_mechanism.map(
        lambda value: bool(COUPLED_TG_SOURCE_PATTERN.search(value))
    )
    source["direct_ite_phrase_cue"] = direct_phrase
    source["thermal_ion_process_cue"] = thermal_ion_process
    source["soft_ionic_thermoelectric_cue"] = soft_ionic_with_output
    source["mixed_ionic_conductor_thermopower_cue"] = mixed_ionic_with_output
    source["external_te_module_cue"] = external_module
    source["already_TG_or_coupled_at_source"] = coupled_tg_source
    source["core_ite_text_cue"] = (
        direct_phrase
        | thermal_ion_process
        | soft_ionic_with_output
        | mixed_ionic_with_output
    ) & ~external_module
    source["iTE_relevance_score"] = (
        4 * direct_phrase.astype(int)
        + 3 * thermal_ion_process.astype(int)
        + 2 * soft_ionic_with_output.astype(int)
        + 2 * mixed_ionic_with_output.astype(int)
        + source["has_curated_ionic_mechanism"].astype(int)
        - 5 * external_module.astype(int)
    )
    source["iTE_relevance_reason"] = [
        "; ".join(
            reason
            for flag, reason in [
                (a, "explicit_ionic_thermoelectric_phrase"),
                (b, "temperature_driven_ion_process"),
                (c, "soft_ionic_system_with_thermoelectric_output"),
                (d, "mixed_ionic_conductor_thermopower"),
                (e, "curated_ionic_mechanism"),
                (f, "external_commercial_TE_module_exclusion"),
            ]
            if flag
        )
        for a, b, c, d, e, f in zip(
            direct_phrase,
            thermal_ion_process,
            soft_ionic_with_output,
            mixed_ionic_with_output,
            source["has_curated_ionic_mechanism"],
            external_module,
        )
    ]
    source["source_scope"] = np.select(
        [
            source["already_TG_or_coupled_at_source"],
            source["core_ite_text_cue"],
            source["has_curated_ionic_mechanism"]
            & ~source["has_solid_state_marker"],
            source["has_curated_ionic_mechanism"],
        ],
        [
            "already_TG_or_coupled_at_source",
            "core_iTE_evidenced_insight",
            "adjacent_ionic_transport_insight",
            "cross_domain_inspiration_supplement",
        ],
        default="outside_current_iTE_transfer_scope",
    )
    source["source_mechanism_route"] = source["source_scope"].map(
        {
            "already_TG_or_coupled_at_source": "coupled_iTE_TG",
            "core_iTE_evidenced_insight": "iTE_thermodiffusion_or_ionic_thermal_response",
            "adjacent_ionic_transport_insight": "adjacent_enabling_chemistry",
            "cross_domain_inspiration_supplement": "electronic_TE_or_cross_domain",
            "outside_current_iTE_transfer_scope": "unrelated_or_unresolved",
        }
    )
    source["likely_review"] = source.apply(is_likely_review, axis=1)
    source["source_analysis_included"] = (
        source["source_scope"].eq("core_iTE_evidenced_insight")
        & ~source["likely_review"]
        & source["abstract"].ne("")
        & source["mechanism_raw"].ne("")
    )
    source["source_exclusion_reason"] = np.select(
        [
            source["source_analysis_included"],
            source["likely_review"],
            source["abstract"].eq(""),
            source["mechanism_raw"].eq(""),
            source["source_scope"].eq("already_TG_or_coupled_at_source"),
            source["source_scope"].eq("adjacent_ionic_transport_insight"),
            source["source_scope"].eq("cross_domain_inspiration_supplement"),
        ],
        [
            "",
            "likely_review_or_overview",
            "missing_abstract",
            "missing_mechanism_summary",
            "retained_as_source_already_TG_or_coupled",
            "retained_as_adjacent_ionic_transport_reference",
            "retained_in_cross_domain_supplement_only",
        ],
        default="outside_current_iTE_transfer_scope",
    )
    return source


def build_claim_units(
    papers: pd.DataFrame,
    corpus_role: str,
    context: pd.DataFrame,
) -> pd.DataFrame:
    context_lookup = context.set_index("paper_id").to_dict("index")
    rows = []
    for paper in papers.itertuples(index=False):
        claims = split_mechanism_claims(paper.mechanism_raw)
        for claim_index, claim in enumerate(claims, start=1):
            claim_id = stable_id(
                "INSIGHT",
                f"{paper.paper_id}|{claim.lower()}",
            )
            row = {
                "insight_id": claim_id,
                "paper_id": paper.paper_id,
                "claim_index_in_paper": claim_index,
                "corpus_role": corpus_role,
                "retrieval_provenance": paper.source_membership,
                "year": int(paper.year),
                "title": paper.title,
                "journal": paper.journal,
                "doi": paper.doi,
                "material_raw": paper.material_raw,
                "mechanism_raw_full": paper.mechanism_raw,
                "insight_claim": claim,
                "claim_origin": "normalized_mechanism_summary",
                "approved_abstract_candidate_id": "",
                "abstract": paper.abstract,
                "likely_review": bool(getattr(paper, "likely_review", False)),
            }
            for key, value in context_lookup.get(paper.paper_id, {}).items():
                row[key] = value
            for column in [
                "source_scope",
                "has_curated_ionic_mechanism",
                "has_solid_state_marker",
                "core_ite_text_cue",
                "direct_ite_phrase_cue",
                "thermal_ion_process_cue",
                "soft_ionic_thermoelectric_cue",
                "mixed_ionic_conductor_thermopower_cue",
                "external_te_module_cue",
                "already_TG_or_coupled_at_source",
                "iTE_relevance_score",
                "iTE_relevance_reason",
                "source_mechanism_route",
                "source_analysis_included",
                "source_exclusion_reason",
            ]:
                if hasattr(paper, column):
                    row[column] = getattr(paper, column)
            rows.append(row)
    return pd.DataFrame(rows)


def sentence_flags(sentence: str) -> dict[str, bool]:
    return {
        "causal": bool(CAUSAL_PATTERN.search(sentence)),
        "intervention": bool(INTERVENTION_PATTERN.search(sentence)),
        "outcome": bool(OUTCOME_PATTERN.search(sentence)),
        "quantitative": bool(QUANTITATIVE_PATTERN.search(sentence)),
        "generic": bool(GENERIC_SENTENCE_PATTERN.search(sentence)),
    }


def attach_cimo_evidence(
    units: pd.DataFrame,
    claim_embeddings: np.ndarray,
    model: SentenceTransformer,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paper_sentences: dict[str, list[str]] = {}
    sentence_rows = []
    for paper_id, abstract in (
        units[["paper_id", "abstract"]].drop_duplicates("paper_id").itertuples(
            index=False
        )
    ):
        sentences = split_sentences(abstract)
        paper_sentences[paper_id] = sentences
        cursor = 0
        for position, sentence in enumerate(sentences, start=1):
            char_start = abstract.find(sentence, cursor)
            if char_start < 0:
                char_start = abstract.find(sentence)
            char_end = (
                char_start + len(sentence) if char_start >= 0 else -1
            )
            if char_end >= 0:
                cursor = char_end
            sentence_rows.append(
                {
                    "paper_id": paper_id,
                    "sentence_position": position,
                    "sentence": sentence,
                    "char_start": char_start,
                    "char_end": char_end,
                }
            )
    sentence_frame = pd.DataFrame(sentence_rows)
    sentence_embeddings = model.encode(
        sentence_frame["sentence"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=128,
    )
    paper_sentence_indices = (
        sentence_frame.groupby("paper_id").indices
        if not sentence_frame.empty
        else {}
    )

    intervention_evidence = []
    mechanism_evidence = []
    outcome_evidence = []
    evidence_bundles = []
    additional_evidence = []
    mechanism_similarity = []
    intervention_status = []
    mechanism_status = []
    outcome_status = []
    role_overlap_status = []
    selected_outcome_quantitative = []
    intervention_char_start = []
    intervention_char_end = []
    mechanism_char_start = []
    mechanism_char_end = []
    outcome_char_start = []
    outcome_char_end = []
    quantitative_flags = []
    causal_flags = []
    abstract_candidates = []

    for unit_position, unit in enumerate(units.itertuples(index=False)):
        sentence_indices = np.asarray(
            paper_sentence_indices.get(unit.paper_id, []), dtype=int
        )
        if len(sentence_indices) == 0:
            intervention_evidence.append("")
            mechanism_evidence.append("")
            outcome_evidence.append("")
            evidence_bundles.append("")
            additional_evidence.append("")
            mechanism_similarity.append(np.nan)
            intervention_status.append("role_not_found")
            mechanism_status.append("role_not_found")
            outcome_status.append("role_not_found")
            role_overlap_status.append("no_roles_found")
            selected_outcome_quantitative.append(False)
            intervention_char_start.append(np.nan)
            intervention_char_end.append(np.nan)
            mechanism_char_start.append(np.nan)
            mechanism_char_end.append(np.nan)
            outcome_char_start.append(np.nan)
            outcome_char_end.append(np.nan)
            quantitative_flags.append(False)
            causal_flags.append(False)
            continue
        sentences = sentence_frame.loc[sentence_indices, "sentence"].tolist()
        vectors = sentence_embeddings[sentence_indices]
        similarities = vectors @ claim_embeddings[unit_position]
        flags = [sentence_flags(sentence) for sentence in sentences]
        intervention_score = similarities + np.array(
            [
                0.09 * flag["intervention"] + 0.03 * flag["causal"]
                for flag in flags
            ]
        )
        mechanism_score = similarities + np.array(
            [0.10 * flag["causal"] - 0.04 * flag["generic"] for flag in flags]
        )
        outcome_score = similarities + np.array(
            [
                0.07 * flag["outcome"]
                + 0.10 * flag["quantitative"]
                - 0.04 * flag["generic"]
                for flag in flags
            ]
        )

        def choose_index(
            scores: np.ndarray,
            eligible: list[bool],
        ) -> int | None:
            candidates = np.flatnonzero(np.asarray(eligible, dtype=bool))
            if len(candidates) == 0:
                return None
            return int(candidates[int(np.argmax(scores[candidates]))])

        intervention_index = choose_index(
            intervention_score,
            [flag["intervention"] for flag in flags],
        )
        mechanism_index = choose_index(
            mechanism_score,
            [flag["causal"] for flag in flags],
        )
        quantitative_outcome_exists = any(
            flag["outcome"] and flag["quantitative"] for flag in flags
        )
        outcome_index = choose_index(
            outcome_score,
            [
                flag["outcome"]
                and (
                    flag["quantitative"]
                    if quantitative_outcome_exists
                    else True
                )
                for flag in flags
            ],
        )
        intervention_sentence = (
            sentences[intervention_index]
            if intervention_index is not None
            else ""
        )
        mechanism_sentence = (
            sentences[mechanism_index] if mechanism_index is not None else ""
        )
        outcome_sentence = (
            sentences[outcome_index] if outcome_index is not None else ""
        )
        intervention_evidence.append(intervention_sentence)
        mechanism_evidence.append(mechanism_sentence)
        outcome_evidence.append(outcome_sentence)
        mechanism_similarity.append(
            float(similarities[mechanism_index])
            if mechanism_index is not None
            else np.nan
        )
        intervention_status.append(
            "cue_gated_role_selected"
            if intervention_index is not None
            else "role_not_found"
        )
        mechanism_status.append(
            "cue_gated_role_selected"
            if mechanism_index is not None
            else "role_not_found"
        )
        outcome_status.append(
            "quantitative_outcome_selected"
            if (
                outcome_index is not None
                and flags[outcome_index]["quantitative"]
            )
            else (
                "qualitative_outcome_selected"
                if outcome_index is not None
                else "role_not_found"
            )
        )
        chosen_roles = [
            index
            for index in [
                intervention_index,
                mechanism_index,
                outcome_index,
            ]
            if index is not None
        ]
        unique_roles = len(set(chosen_roles))
        role_overlap_status.append(
            "all_selected_roles_distinct"
            if len(chosen_roles) >= 2 and unique_roles == len(chosen_roles)
            else (
                "selected_roles_share_sentence"
                if len(chosen_roles) >= 2
                else "fewer_than_two_roles_found"
            )
        )
        selected_outcome_quantitative.append(
            bool(
                outcome_index is not None
                and flags[outcome_index]["quantitative"]
            )
        )
        local_starts = sentence_frame.loc[
            sentence_indices, "char_start"
        ].to_numpy()
        local_ends = sentence_frame.loc[
            sentence_indices, "char_end"
        ].to_numpy()
        for index, starts, ends in [
            (
                intervention_index,
                intervention_char_start,
                intervention_char_end,
            ),
            (
                mechanism_index,
                mechanism_char_start,
                mechanism_char_end,
            ),
            (outcome_index, outcome_char_start, outcome_char_end),
        ]:
            starts.append(
                int(local_starts[index]) if index is not None else np.nan
            )
            ends.append(
                int(local_ends[index]) if index is not None else np.nan
            )
        quantitative_flags.append(any(flag["quantitative"] for flag in flags))
        causal_flags.append(any(flag["causal"] for flag in flags))

        candidate_order = np.argsort(
            similarities
            + np.array(
                [
                    0.08 * flag["causal"]
                    + 0.06 * flag["intervention"]
                    + 0.06 * flag["outcome"]
                    + 0.08 * flag["quantitative"]
                    - 0.08 * flag["generic"]
                    for flag in flags
                ]
            )
        )[::-1]
        kept = 0
        gated_sentence_indices: list[int] = []
        for sentence_index in candidate_order:
            flag = flags[int(sentence_index)]
            relation_quality_gate = (
                flag["causal"]
                and (flag["intervention"] or flag["outcome"])
                and not (flag["generic"] and not flag["quantitative"])
            )
            if not relation_quality_gate:
                continue
            sentence = sentences[int(sentence_index)]
            gated_sentence_indices.append(int(sentence_index))
            abstract_candidates.append(
                {
                    "abstract_claim_candidate_id": stable_id(
                        "ABSTRACT",
                        f"{unit.paper_id}|{sentence.lower()}",
                    ),
                    "linked_insight_id": unit.insight_id,
                    "paper_id": unit.paper_id,
                    "year": unit.year,
                    "corpus_role": unit.corpus_role,
                    "source_scope": getattr(unit, "source_scope", ""),
                    "source_analysis_included": bool(
                        getattr(unit, "source_analysis_included", False)
                    ),
                    "title": unit.title,
                    "doi": unit.doi,
                    "candidate_evidence_sentence": sentence,
                    "sentence_position": int(sentence_index) + 1,
                    "char_start": int(local_starts[int(sentence_index)]),
                    "char_end": int(local_ends[int(sentence_index)]),
                    "similarity_to_mechanism_summary": float(
                        similarities[int(sentence_index)]
                    ),
                    "has_causal_cue": flag["causal"],
                    "has_intervention_cue": flag["intervention"],
                    "has_outcome_cue": flag["outcome"],
                    "has_quantitative_detail": flag["quantitative"],
                    "candidate_status": (
                        "candidate_additional_CIMO_E_insight_pending_review"
                    ),
                }
            )
            kept += 1
            if kept >= 5:
                break
        role_indices = {
            index
            for index in [
                intervention_index,
                mechanism_index,
                outcome_index,
            ]
            if index is not None
        }
        evidence_indices = sorted(
            role_indices.union(gated_sentence_indices[:5])
        )
        evidence_bundles.append(
            " || ".join(sentences[index] for index in evidence_indices)
        )
        additional_evidence.append(
            " || ".join(
                sentences[index]
                for index in sorted(set(gated_sentence_indices) - role_indices)
            )
        )

    enriched = units.copy()
    enriched["context"] = (
        enriched["title"]
        + " | material context: "
        + enriched["material_raw"].fillna("")
    )
    enriched["intervention_evidence_sentence"] = intervention_evidence
    enriched["mechanism_evidence_sentence"] = mechanism_evidence
    enriched["outcome_evidence_sentence"] = outcome_evidence
    enriched["intervention_evidence_status"] = intervention_status
    enriched["mechanism_evidence_status"] = mechanism_status
    enriched["outcome_evidence_status"] = outcome_status
    enriched["CIMO_role_sentence_overlap_status"] = role_overlap_status
    enriched["selected_outcome_has_quantitative_detail"] = (
        selected_outcome_quantitative
    )
    enriched["intervention_evidence_char_start"] = intervention_char_start
    enriched["intervention_evidence_char_end"] = intervention_char_end
    enriched["mechanism_evidence_char_start"] = mechanism_char_start
    enriched["mechanism_evidence_char_end"] = mechanism_char_end
    enriched["outcome_evidence_char_start"] = outcome_char_start
    enriched["outcome_evidence_char_end"] = outcome_char_end
    enriched["exact_abstract_evidence_bundle"] = evidence_bundles
    enriched["additional_exact_abstract_evidence_sentences"] = (
        additional_evidence
    )
    enriched["claim_to_mechanism_sentence_cosine"] = mechanism_similarity
    enriched["abstract_contains_quantitative_detail"] = quantitative_flags
    enriched["abstract_contains_causal_cue"] = causal_flags
    enriched["mechanism_summary_provenance"] = (
        "normalized mechanism_raw; not a verbatim evidence span"
    )
    candidate_frame = pd.DataFrame(abstract_candidates)
    if not candidate_frame.empty:
        linkage = (
            candidate_frame.groupby(
                ["paper_id", "candidate_evidence_sentence"],
                as_index=False,
            )["linked_insight_id"]
            .agg(lambda values: "; ".join(sorted(set(values))))
            .rename(columns={"linked_insight_id": "linked_insight_ids"})
        )
        candidate_frame = (
            candidate_frame.sort_values(
                "similarity_to_mechanism_summary", ascending=False
            )
            .drop_duplicates(
                ["paper_id", "candidate_evidence_sentence"], keep="first"
            )
            .sort_values(
                ["paper_id", "sentence_position", "similarity_to_mechanism_summary"],
                ascending=[True, True, False],
            )
            .reset_index(drop=True)
        )
        candidate_frame = candidate_frame.merge(
            linkage,
            on=["paper_id", "candidate_evidence_sentence"],
            how="left",
        )
    return enriched, candidate_frame


def promote_approved_abstract_candidates(
    base_units: pd.DataFrame,
    candidate_frame: pd.DataFrame,
    adjudication: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    review_columns = [
        column
        for column in adjudication.columns
        if column != "abstract_claim_candidate_id"
    ]
    reviewed_candidates = candidate_frame.merge(
        adjudication,
        on="abstract_claim_candidate_id",
        how="left",
    )
    for column in review_columns:
        reviewed_candidates[column] = reviewed_candidates[column].fillna("")
    reviewed_candidates["promotion_status"] = np.where(
        reviewed_candidates["include_as_separate_insight"].map(
            review_value_is_true
        ),
        "approved_for_promotion_on_next_analysis",
        "not_approved_or_pending",
    )
    approved = reviewed_candidates[
        reviewed_candidates["include_as_separate_insight"].map(
            review_value_is_true
        )
        & reviewed_candidates["corpus_role"].eq("iTE_source")
        & reviewed_candidates["source_analysis_included"].fillna(False)
    ].copy()
    if approved.empty:
        return base_units, reviewed_candidates, 0

    promoted_rows = []
    existing_ids = set(base_units["insight_id"])
    next_indices = (
        base_units.groupby("paper_id")["claim_index_in_paper"].max().to_dict()
    )
    for candidate in approved.itertuples(index=False):
        paper_rows = base_units[
            base_units["paper_id"].eq(candidate.paper_id)
            & base_units["corpus_role"].eq("iTE_source")
        ]
        if paper_rows.empty:
            continue
        promoted_id = stable_id(
            "INSIGHT",
            f"{candidate.paper_id}|{candidate.candidate_evidence_sentence.lower()}",
        )
        if promoted_id in existing_ids:
            reviewed_candidates.loc[
                reviewed_candidates["abstract_claim_candidate_id"].eq(
                    candidate.abstract_claim_candidate_id
                ),
                "promotion_status",
            ] = "already_represented_by_existing_insight"
            continue
        row = paper_rows.iloc[0].copy()
        next_indices[candidate.paper_id] = (
            int(next_indices.get(candidate.paper_id, 0)) + 1
        )
        row["insight_id"] = promoted_id
        row["claim_index_in_paper"] = next_indices[candidate.paper_id]
        row["insight_claim"] = candidate.candidate_evidence_sentence
        row["claim_origin"] = "approved_exact_abstract_candidate"
        row["approved_abstract_candidate_id"] = (
            candidate.abstract_claim_candidate_id
        )
        promoted_rows.append(row)
        existing_ids.add(promoted_id)
        reviewed_candidates.loc[
            reviewed_candidates["abstract_claim_candidate_id"].eq(
                candidate.abstract_claim_candidate_id
            ),
            "promotion_status",
        ] = "promoted_to_primary_claim_unit"
    if not promoted_rows:
        return base_units, reviewed_candidates, 0
    promoted_frame = pd.DataFrame(promoted_rows)
    combined = pd.concat(
        [base_units, promoted_frame],
        ignore_index=True,
    )
    return combined, reviewed_candidates, len(promoted_frame)


def top_values(series: pd.Series, limit: int = 20) -> str:
    values = []
    for value in series.fillna(""):
        values.extend(part.strip() for part in str(value).split(";") if part.strip())
    counts = Counter(values)
    return "; ".join(
        value
        for value, _ in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )[:limit]
    )


def best_temporal_match(
    source_indices: np.ndarray,
    source_years: np.ndarray,
    target_indices: np.ndarray,
    target_years: np.ndarray,
    embeddings: np.ndarray,
    mode: str,
    origin_year: int,
) -> tuple[float, int | None, int | None]:
    if len(source_indices) == 0 or len(target_indices) == 0:
        return np.nan, None, None
    source_vectors = embeddings[source_indices]
    target_vectors = embeddings[target_indices]
    scores = source_vectors @ target_vectors.T
    if mode == "preexisting":
        # A TG paper is pre-existing only if it predates the origin of the
        # whole iTE theme.  Comparing it with a later iTE replication would
        # otherwise reverse the apparent direction of knowledge flow.
        valid = np.broadcast_to(
            target_years[None, :] < origin_year,
            scores.shape,
        )
    elif mode == "contemporaneous":
        valid = np.broadcast_to(
            target_years[None, :] == origin_year,
            scores.shape,
        )
    elif mode == "later":
        valid = source_years[:, None] < target_years[None, :]
        valid &= target_years[None, :] > origin_year
    else:
        valid = np.ones_like(scores, dtype=bool)
    if not valid.any():
        return np.nan, None, None
    masked = np.where(valid, scores, -np.inf)
    flat = int(np.argmax(masked))
    source_position, target_position = np.unravel_index(flat, masked.shape)
    score = float(masked[source_position, target_position])
    if not np.isfinite(score):
        return np.nan, None, None
    return (
        score,
        int(source_indices[source_position]),
        int(target_indices[target_position]),
    )


def alignment_band(
    score: float, possible_threshold: float, strong_threshold: float
) -> str:
    if pd.isna(score):
        return "no_eligible_comparison"
    if score >= strong_threshold:
        return "strong_semantic_audit_candidate"
    if score >= possible_threshold:
        return "possible_analogy_requires_review"
    return "below_alignment_threshold"


def percentile(series: pd.Series) -> pd.Series:
    return series.rank(method="average", pct=True)


TRANSFER_TEMPLATES = {
    "molecular_interaction_and_solvation": {
        "principle": (
            "Use reversible coordination, host-guest binding, hydrogen bonding, "
            "or selective solvation to differentiate the thermodynamics and "
            "mobility of ionic species."
        ),
        "bottleneck": (
            "TG output is limited when the oxidized and reduced states have "
            "similar solvation entropy or when both species diffuse similarly."
        ),
        "adaptation": (
            "Introduce a ligand, host, polymer functionality, or solvent motif "
            "that interacts differently with the two TG redox states while "
            "preserving access to the electrode."
        ),
        "effect": (
            "Increase the redox entropy/activity contrast and therefore the "
            "thermogalvanic voltage without an unacceptable kinetic penalty."
        ),
        "constraints": (
            "Binding must be reversible over the working temperature and "
            "compatible with the redox window, solvent, and electrode."
        ),
        "risk": (
            "Over-binding can reduce diffusion, exchange current, or redox "
            "reversibility and erase any voltage gain."
        ),
        "experiment": (
            "Compare matched TG cells with and without the interaction motif; "
            "measure temperature-dependent open-circuit potential, diffusion, "
            "speciation, EIS, exchange current, and sustained power."
        ),
    },
    "selective_ion_transport": {
        "principle": (
            "Create selective confinement or transport pathways so one ionic "
            "species moves or redistributes differently from its counter-species."
        ),
        "bottleneck": (
            "TG voltage and power are weakened by nonselective mass transport, "
            "concentration polarization, or crossover of redox species."
        ),
        "adaptation": (
            "Adapt the iTE channel, membrane, fixed-charge, or confinement motif "
            "to discriminate between TG redox states or supporting ions while "
            "retaining electrode-facing transport."
        ),
        "effect": (
            "Reinforce the hot/cold activity difference and reduce crossover or "
            "polarization losses."
        ),
        "constraints": (
            "Selectivity must persist at TG concentrations and should not block "
            "electroneutrality or substantially raise bulk resistance."
        ),
        "risk": (
            "The same confinement that creates selectivity may slow redox mass "
            "transfer and lower current density."
        ),
        "experiment": (
            "Use a concentration- and thickness-matched membrane/gel series; "
            "measure transference/selectivity, redox diffusion, Seebeck "
            "coefficient, EIS, limiting current, and power."
        ),
    },
    "phase_or_species_transition": {
        "principle": (
            "Use a reversible phase or species transition to amplify a "
            "temperature-dependent concentration, solvation, or mobility contrast."
        ),
        "bottleneck": (
            "Conventional TG electrolytes often change smoothly with temperature, "
            "limiting the redox activity and entropy difference."
        ),
        "adaptation": (
            "Choose a TG-compatible transition that redistributes or changes the "
            "solvation of one redox state across the operating temperature range."
        ),
        "effect": (
            "Increase the effective thermogalvanic voltage or switch its sign in "
            "a controlled and reversible manner."
        ),
        "constraints": (
            "The transition temperature, latent heat, cycling hysteresis, and "
            "redox compatibility must match the intended device."
        ),
        "risk": (
            "Precipitation, hysteresis, phase separation, or incomplete recovery "
            "can cause drift and rapid power loss."
        ),
        "experiment": (
            "Map potential, phase/species fraction, diffusion, and power through "
            "heating-cooling cycles around the transition; include an isothermal "
            "composition control."
        ),
    },
    "electrode_and_redox_interface": {
        "principle": (
            "Engineer electrode chemistry and architecture to accelerate redox "
            "exchange and shorten diffusion paths while retaining thermodynamic "
            "selectivity."
        ),
        "bottleneck": (
            "TG power is often limited by charge-transfer resistance, active "
            "surface area, adsorption, and redox diffusion near the electrode."
        ),
        "adaptation": (
            "Transfer the iTE surface functionality, porosity, or multilayer "
            "strategy to both TG electrodes with controlled redox-state affinity."
        ),
        "effect": (
            "Lower kinetic and mass-transfer losses, increasing usable current "
            "and power at the same thermogalvanic voltage."
        ),
        "constraints": (
            "Electrode area, loading, spacing, and thermal conductance must be "
            "matched so intrinsic and geometric effects can be separated."
        ),
        "risk": (
            "Strong adsorption or catalytic asymmetry can shift equilibrium "
            "potential, foul the surface, or create misleading transient gains."
        ),
        "experiment": (
            "Run symmetric-electrode TG cells across matched surface areas; "
            "measure EIS, exchange current, rotating-electrode mass transfer, "
            "open-circuit voltage, and steady-state power."
        ),
    },
    "gel_network_and_environmental_stability": {
        "principle": (
            "Use a mechanically robust, water-retaining, anti-freezing gel "
            "network that preserves ionic pathways under realistic operation."
        ),
        "bottleneck": (
            "TG gels can dry, leak, freeze, delaminate, or lose redox mobility "
            "during long-duration and wearable operation."
        ),
        "adaptation": (
            "Rebuild the iTE network around the TG redox electrolyte, tuning "
            "crosslink density and solvent retention without immobilizing the "
            "redox couple."
        ),
        "effect": (
            "Improve operational stability and mechanical integration while "
            "retaining a useful fraction of liquid-cell voltage and power."
        ),
        "constraints": (
            "Redox compatibility, solvent uptake, thermal conductivity, electrode "
            "contact, and diffusion must be measured together."
        ),
        "risk": (
            "A stronger network can reduce redox diffusion and current even when "
            "mechanical and environmental stability improve."
        ),
        "experiment": (
            "Compare liquid and gel TG cells over crosslink density; quantify "
            "Seebeck coefficient, diffusion, EIS, power, dehydration/freezing "
            "cycles, adhesion, and mechanical fatigue."
        ),
    },
    "ionic_thermodiffusion": {
        "principle": (
            "Tune ion-solvent interactions and mobility asymmetry so thermal "
            "diffusion creates a useful ionic activity or electric-field gradient."
        ),
        "bottleneck": (
            "Supporting-ion thermodiffusion in TG cells may be weak, unmeasured, "
            "or oppose the redox-derived thermovoltage."
        ),
        "adaptation": (
            "Screen supporting electrolyte and solvent combinations whose Soret "
            "redistribution reinforces the TG redox entropy contribution."
        ),
        "effect": (
            "Increase effective thermovoltage and reduce adverse concentration "
            "polarization under a temperature gradient."
        ),
        "constraints": (
            "Bulk thermodiffusion, electrode redox entropy, convection, and liquid "
            "junction potentials must be separated experimentally."
        ),
        "risk": (
            "The ionic field can oppose the redox voltage or increase internal "
            "resistance despite a larger open-circuit signal."
        ),
        "experiment": (
            "Reverse the temperature gradient in convection-controlled TG cells; "
            "measure spatial ion concentration, open-circuit potential, redox "
            "Seebeck coefficient, EIS, and load-dependent power."
        ),
    },
    "thermal_management_and_device_coupling": {
        "principle": (
            "Preserve or concentrate the temperature gradient through thermal, "
            "photothermal, or device-level architecture."
        ),
        "bottleneck": (
            "TG performance is often limited by loss of the internal temperature "
            "difference rather than electrolyte thermodynamics alone."
        ),
        "adaptation": (
            "Integrate the iTE heat-management architecture around a TG cell while "
            "keeping electrode temperatures and thermal leakage measurable."
        ),
        "effect": (
            "Increase system-level voltage, harvested energy, or duty cycle by "
            "maintaining a larger effective temperature gradient."
        ),
        "constraints": (
            "Intrinsic Seebeck changes must be separated from a larger applied "
            "temperature difference and added thermal mass."
        ),
        "risk": (
            "Apparent gains may come only from boundary conditions, with slower "
            "response or lower net system efficiency."
        ),
        "experiment": (
            "Compare identical TG cells with and without the thermal architecture; "
            "record internal temperature fields, heat flux, response time, voltage, "
            "power, and net energy."
        ),
    },
    "other_iTE_design_principle": {
        "principle": (
            "Treat the source claim as an iTE design principle requiring a "
            "mechanism-specific TG analogue before implementation."
        ),
        "bottleneck": (
            "The corresponding TG limitation has not yet been assigned with "
            "enough specificity."
        ),
        "adaptation": (
            "Identify the TG redox species, transport step, or device component "
            "that is causally analogous to the source intervention."
        ),
        "effect": (
            "Define a directional TG outcome only after the analogue and mediator "
            "are verified."
        ),
        "constraints": (
            "Do not infer transfer from shared thermoelectric vocabulary alone."
        ),
        "risk": (
            "A thematic resemblance may be mistaken for the same physical or "
            "chemical driver."
        ),
        "experiment": (
            "Design a paired TG experiment that changes only the proposed analogue "
            "and measures thermodynamics, kinetics, transport, and power."
        ),
    },
}


def transfer_family_labels(row: pd.Series) -> list[str]:
    primary_text = " ".join(
        normalize_space(row.get(column, ""))
        for column in [
            "representative_iTE_claim",
            "mechanism_evidence_sentence",
            "outcome_evidence_sentence",
        ]
    ).lower()
    fallback_text = " ".join(
        normalize_space(row.get(column, ""))
        for column in [
            "mechanism_concepts",
            "material_contexts",
            "device_contexts",
        ]
    ).lower()
    patterns = [
        (
            "electrode_and_redox_interface",
            r"electrode|charge.transfer|exchange current|redox kinetics|"
            r"porous.electrode|current density",
        ),
        (
            "phase_or_species_transition",
            r"phase transition|crystalli|precipitat|micell|species "
            r"redistribution|salting.out",
        ),
        (
            "molecular_interaction_and_solvation",
            r"host.guest|complex|coordinat|solvat|hydrogen bond|"
            r"ion.dipole|hydration|hofmeister|chaotrop|ion.pair",
        ),
        (
            "selective_ion_transport",
            r"selectiv|confine|channel|membrane|nanopore|mobility "
            r"difference|cation transport|anion transport",
        ),
        (
            "gel_network_and_environmental_stability",
            r"gel|hydrogel|ionogel|network|anti.freez|water retention|"
            r"mechanic|stretch|self.heal",
        ),
        (
            "ionic_thermodiffusion",
            r"thermodiffusion|soret|thermal migration|thermophor|"
            r"ionic seebeck|ionic thermopower|heat of transport",
        ),
        (
            "thermal_management_and_device_coupling",
            r"photothermal|solar|heat transfer|thermal.gradient|"
            r"thermal management",
        ),
    ]
    hits = [
        family
        for family, pattern in patterns
        if re.search(pattern, primary_text, re.I)
    ]
    if not hits:
        hits = [
            family
            for family, pattern in patterns
            if re.search(pattern, fallback_text, re.I)
        ]
    return hits or ["other_iTE_design_principle"]


def transfer_family(row: pd.Series) -> str:
    return transfer_family_labels(row)[0]


def build_transfer_cards(
    themes: pd.DataFrame,
    possible_alignment: float,
) -> pd.DataFrame:
    cards = themes.copy()
    cards["transfer_family"] = cards.apply(transfer_family, axis=1)
    cards["transfer_family_labels"] = cards.apply(
        lambda row: "; ".join(transfer_family_labels(row)),
        axis=1,
    )
    cards["transfer_family_rule_hit_count"] = cards[
        "transfer_family_labels"
    ].map(lambda value: len(str(value).split("; ")))
    cards["transfer_family_assignment_status"] = np.select(
        [
            cards["transfer_family"].eq("other_iTE_design_principle"),
            cards["transfer_family_rule_hit_count"].gt(1),
        ],
        [
            "unresolved_family_requires_review",
            "multi_label_family_draft_primary_template_requires_review",
        ],
        default="single_family_rule_hit_requires_review",
    )
    for field, template_key in [
        ("transferable_design_principle", "principle"),
        ("TG_bottleneck", "bottleneck"),
        ("adaptation_required", "adaptation"),
        ("expected_TG_effect", "effect"),
        ("transfer_constraints", "constraints"),
        ("failure_risk", "risk"),
        ("minimal_validation_experiment", "experiment"),
    ]:
        cards[field] = cards["transfer_family"].map(
            lambda family: TRANSFER_TEMPLATES[family][template_key]
        )
    cards["iTE_informed_TG_hypothesis"] = (
        "Source iTE claim: "
        + cards["representative_iTE_claim"]
        + " TG adaptation draft: "
        + cards["adaptation_required"]
        + " Expected test: "
        + cards["expected_TG_effect"]
    )
    cards["TG_relation_candidate_status"] = cards["relation_status_flags"]
    cards["TG_evidence_status"] = np.where(
        cards["relation_status_flags"].eq(
            "no_cross_corpus_relation_above_threshold"
        ),
        "untested_or_not_aligned_in_current_TG_corpus",
        "semantic_candidate_unverified_by_relation_or_full_text_review",
    )
    aligned = cards["selected_alignment_cosine"].ge(possible_alignment) & ~cards[
        "trajectory"
    ].eq("iTE-evidenced insight → TG translation opportunity")
    cards["TG_analogue_candidate"] = cards["matched_target_claim"].where(
        aligned, ""
    )
    cards["closest_TG_reference_for_context"] = cards["matched_target_claim"]
    cards["above_similarity_review_threshold"] = aligned
    cards["relation_evidence_verified"] = False
    cards["translation_draft_status"] = (
        "rule_based_iTE_to_TG_draft_requires_relation_and_full_text_review"
    )
    cards["transfer_priority"] = ""
    return cards.sort_values(
        ["TG_translation_review_priority", "supporting_iTE_paper_count"],
        ascending=False,
    )


def build_themes_and_matches(
    units: pd.DataFrame,
    embeddings: np.ndarray,
    theme_cosine: float,
    possible_alignment: float,
    strong_alignment: float,
    freeze_year: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source_mask = (
        units["corpus_role"].eq("iTE_source")
        & units["evidence_ready_for_primary_analysis"].fillna(False)
    )
    target_mask = units["corpus_role"].eq("TG_reference") & ~units[
        "likely_review"
    ]
    bridge_mask = units["corpus_role"].eq("bridge") & ~units["likely_review"]
    source_indices = units.index[source_mask].to_numpy()
    target_indices = units.index[target_mask].to_numpy()
    bridge_indices = units.index[bridge_mask].to_numpy()
    if len(source_indices) == 0:
        raise RuntimeError("No eligible iTE insight claims were found.")

    distance_threshold = 1.0 - theme_cosine
    cluster_labels = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=distance_threshold,
    ).fit_predict(embeddings[source_indices])
    units.loc[source_indices, "_cluster"] = cluster_labels
    source_cluster_lookup = dict(zip(source_indices, cluster_labels))
    target_years_all = units.loc[target_indices, "year"].to_numpy(dtype=int)
    bridge_years_all = units.loc[bridge_indices, "year"].to_numpy(dtype=int)

    rows = []
    member_rows = []
    relation_rows = []
    for cluster_label in sorted(set(cluster_labels)):
        member_indices = np.asarray(
            [
                index
                for index in source_indices
                if source_cluster_lookup[index] == cluster_label
            ],
            dtype=int,
        )
        members = units.loc[member_indices].copy()
        member_vectors = embeddings[member_indices]
        within_theme_cosines = member_vectors @ member_vectors.T
        medoid_position = int(
            np.argmax(within_theme_cosines.mean(axis=1))
        )
        if len(member_vectors) > 1:
            upper_triangle = within_theme_cosines[
                np.triu_indices(len(member_vectors), k=1)
            ]
            mean_pairwise_cosine = float(upper_triangle.mean())
            min_pairwise_cosine = float(upper_triangle.min())
            medoid_other_cosines = np.delete(
                within_theme_cosines[medoid_position], medoid_position
            )
            medoid_min_cosine = float(medoid_other_cosines.min())
        else:
            mean_pairwise_cosine = 1.0
            min_pairwise_cosine = 1.0
            medoid_min_cosine = 1.0
        medoid_index = int(member_indices[medoid_position])
        medoid = units.loc[medoid_index]
        theme_id = stable_id(
            "ITE_THEME",
            "|".join(sorted(members["insight_id"].tolist())),
        )
        origin_year = int(members["year"].min())
        source_years = members["year"].to_numpy(dtype=int)

        pre_score, pre_source, pre_target = best_temporal_match(
            member_indices,
            source_years,
            target_indices,
            target_years_all,
            embeddings,
            "preexisting",
            origin_year,
        )
        same_score, same_source, same_target = best_temporal_match(
            member_indices,
            source_years,
            target_indices,
            target_years_all,
            embeddings,
            "contemporaneous",
            origin_year,
        )
        later_score, later_source, later_target = best_temporal_match(
            member_indices,
            source_years,
            target_indices,
            target_years_all,
            embeddings,
            "later",
            origin_year,
        )
        bridge_score, bridge_source, bridge_target = best_temporal_match(
            member_indices,
            source_years,
            bridge_indices,
            bridge_years_all,
            embeddings,
            "later",
            origin_year,
        )
        proximity_score, proximity_source, proximity_target = best_temporal_match(
            member_indices,
            source_years,
            target_indices,
            target_years_all,
            embeddings,
            "any",
            origin_year,
        )

        pre_aligned = pd.notna(pre_score) and pre_score >= possible_alignment
        same_aligned = (
            pd.notna(same_score) and same_score >= possible_alignment
        )
        later_aligned = (
            pd.notna(later_score) and later_score >= possible_alignment
        )
        bridge_aligned = (
            pd.notna(bridge_score) and bridge_score >= possible_alignment
        )
        relation_candidates = [
            {
                "relation_temporal_class": "pre_existing_TG_candidate",
                "trajectory": (
                    "iTE-evidenced insight with pre-existing TG analogue "
                    "candidate"
                ),
                "score": pre_score,
                "source": pre_source,
                "target": pre_target,
                "target_role": "TG_reference",
                "aligned": pre_aligned,
            },
            {
                "relation_temporal_class": (
                    "same_year_temporally_ambiguous_candidate"
                ),
                "trajectory": (
                    "iTE-evidenced insight with same-year TG analogue "
                    "candidate"
                ),
                "score": same_score,
                "source": same_source,
                "target": same_target,
                "target_role": "TG_reference",
                "aligned": same_aligned,
            },
            {
                "relation_temporal_class": "later_TG_alignment_candidate",
                "trajectory": (
                    "iTE-evidenced insight → subsequent TG alignment candidate"
                ),
                "score": later_score,
                "source": later_source,
                "target": later_target,
                "target_role": "TG_reference",
                "aligned": later_aligned,
            },
            {
                "relation_temporal_class": "later_bridge_alignment_candidate",
                "trajectory": (
                    "iTE-evidenced insight → bridge alignment candidate"
                ),
                "score": bridge_score,
                "source": bridge_source,
                "target": bridge_target,
                "target_role": "bridge",
                "aligned": bridge_aligned,
            },
        ]
        aligned_candidates = [
            candidate
            for candidate in relation_candidates
            if candidate["aligned"]
        ]
        if aligned_candidates:
            selected = max(
                aligned_candidates,
                key=lambda candidate: float(candidate["score"]),
            )
            trajectory = selected["trajectory"]
            selected_score = selected["score"]
            selected_source = selected["source"]
            selected_target = selected["target"]
            selected_role = selected["target_role"]
            selected_relation_temporal_class = selected[
                "relation_temporal_class"
            ]
        else:
            trajectory = (
                "iTE-evidenced insight → TG translation opportunity"
            )
            selected_score = proximity_score
            selected_source = proximity_source
            selected_target = proximity_target
            selected_role = (
                "TG_reference" if proximity_target is not None else ""
            )
            selected_relation_temporal_class = (
                "nearest_TG_text_below_review_threshold"
            )
        relation_status_flags = "; ".join(
            candidate["relation_temporal_class"]
            for candidate in relation_candidates
            if candidate["aligned"]
        )
        if not relation_status_flags:
            relation_status_flags = "no_cross_corpus_relation_above_threshold"

        mutual_nearest = False
        if (
            selected_target is not None
            and selected_source is not None
            and units.loc[selected_target, "year"] > units.loc[selected_source, "year"]
        ):
            eligible_global_source = source_indices[
                units.loc[source_indices, "year"].to_numpy(dtype=int)
                < int(units.loc[selected_target, "year"])
            ]
            if len(eligible_global_source):
                nearest = int(
                    eligible_global_source[
                        np.argmax(
                            embeddings[eligible_global_source]
                            @ embeddings[selected_target]
                        )
                    ]
                )
                mutual_nearest = source_cluster_lookup.get(nearest) == cluster_label

        selected_source_row = (
            units.loc[selected_source] if selected_source is not None else None
        )
        selected_target_row = (
            units.loc[selected_target] if selected_target is not None else None
        )
        source_paper_count = members["paper_id"].nunique()
        recent_paper_count = members.loc[
            members["year"] >= freeze_year - 2, "paper_id"
        ].nunique()
        row = {
            "theme_id": theme_id,
            "representative_insight_id": medoid["insight_id"],
            "representative_iTE_claim": medoid["insight_claim"],
            "representative_iTE_paper_id": medoid["paper_id"],
            "representative_iTE_year": int(medoid["year"]),
            "representative_iTE_title": medoid["title"],
            "representative_iTE_doi": medoid["doi"],
            "source_abstract": medoid["abstract"],
            "context": medoid["context"],
            "intervention_evidence_sentence": medoid[
                "intervention_evidence_sentence"
            ],
            "mechanism_evidence_sentence": medoid[
                "mechanism_evidence_sentence"
            ],
            "outcome_evidence_sentence": medoid[
                "outcome_evidence_sentence"
            ],
            "exact_abstract_evidence_bundle": medoid[
                "exact_abstract_evidence_bundle"
            ],
            "iTE_theme_origin_year": origin_year,
            "iTE_theme_latest_year": int(members["year"].max()),
            "supporting_iTE_paper_count": source_paper_count,
            "recent_iTE_papers_3y": recent_paper_count,
            "semantic_theme_support_status": (
                "multi_paper_semantic_theme_pending_same_insight_review"
                if source_paper_count >= 2
                else "single_paper_semantic_theme"
            ),
            "mechanistic_replication_verified": False,
            "theme_mean_pairwise_claim_cosine": mean_pairwise_cosine,
            "theme_min_pairwise_claim_cosine": min_pairwise_cosine,
            "theme_medoid_min_claim_cosine": medoid_min_cosine,
            "source_scope_mix": "; ".join(
                sorted(members["source_scope"].dropna().unique())
            ),
            "iTE_evidence_paper_ids": "; ".join(
                sorted(members["paper_id"].unique())
            ),
            "iTE_evidence_years": "; ".join(
                str(value) for value in sorted(members["year"].unique())
            ),
            "mechanism_concepts": top_values(
                members["mechanism_concepts"]
            ),
            "material_contexts": top_values(members["material_concepts"]),
            "outcome_metrics": top_values(
                members["outcome_metric_concepts"]
            ),
            "device_contexts": top_values(
                members["device_context_concepts"]
            ),
            "preexisting_TG_analogue_cosine": pre_score,
            "contemporaneous_TG_analogue_cosine": same_score,
            "later_TG_alignment_cosine": later_score,
            "bridge_alignment_cosine": bridge_score,
            "has_preexisting_TG_candidate": pre_aligned,
            "has_same_year_TG_candidate": same_aligned,
            "has_later_TG_candidate": later_aligned,
            "has_later_bridge_candidate": bridge_aligned,
            "preexisting_TG_alignment_band": alignment_band(
                pre_score, possible_alignment, strong_alignment
            ),
            "contemporaneous_TG_alignment_band": alignment_band(
                same_score, possible_alignment, strong_alignment
            ),
            "later_TG_alignment_band": alignment_band(
                later_score, possible_alignment, strong_alignment
            ),
            "bridge_alignment_band": alignment_band(
                bridge_score, possible_alignment, strong_alignment
            ),
            "relation_status_flags": relation_status_flags,
            "current_TG_proximity_cosine": proximity_score,
            "trajectory": trajectory,
            "selected_relation_temporal_class": (
                selected_relation_temporal_class
            ),
            "selected_alignment_cosine": selected_score,
            "selected_alignment_band": alignment_band(
                selected_score, possible_alignment, strong_alignment
            ),
            "mutual_nearest_theme_match": mutual_nearest,
            "matched_source_insight_id": (
                selected_source_row["insight_id"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_claim": (
                selected_source_row["insight_claim"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_year": (
                int(selected_source_row["year"])
                if selected_source_row is not None
                else np.nan
            ),
            "matched_source_paper_id": (
                selected_source_row["paper_id"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_title": (
                selected_source_row["title"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_doi": (
                selected_source_row["doi"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_abstract": (
                selected_source_row["abstract"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_intervention_evidence_sentence": (
                selected_source_row["intervention_evidence_sentence"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_mechanism_evidence_sentence": (
                selected_source_row["mechanism_evidence_sentence"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_outcome_evidence_sentence": (
                selected_source_row["outcome_evidence_sentence"]
                if selected_source_row is not None
                else ""
            ),
            "matched_source_exact_abstract_evidence_bundle": (
                selected_source_row["exact_abstract_evidence_bundle"]
                if selected_source_row is not None
                else ""
            ),
            "matched_target_role": selected_role,
            "matched_target_insight_id": (
                selected_target_row["insight_id"]
                if selected_target_row is not None
                else ""
            ),
            "matched_target_claim": (
                selected_target_row["insight_claim"]
                if selected_target_row is not None
                else ""
            ),
            "matched_target_year": (
                int(selected_target_row["year"])
                if selected_target_row is not None
                else np.nan
            ),
            "matched_target_paper_id": (
                selected_target_row["paper_id"]
                if selected_target_row is not None
                else ""
            ),
            "matched_target_title": (
                selected_target_row["title"]
                if selected_target_row is not None
                else ""
            ),
            "matched_target_doi": (
                selected_target_row["doi"]
                if selected_target_row is not None
                else ""
            ),
            "matched_target_abstract": (
                selected_target_row["abstract"]
                if selected_target_row is not None
                else ""
            ),
            "matched_target_mechanism_evidence_sentence": (
                selected_target_row["mechanism_evidence_sentence"]
                if selected_target_row is not None
                else ""
            ),
            "matched_target_outcome_evidence_sentence": (
                selected_target_row["outcome_evidence_sentence"]
                if selected_target_row is not None
                else ""
            ),
            "temporal_lag_years": (
                int(selected_target_row["year"] - selected_source_row["year"])
                if (
                    selected_target_row is not None
                    and selected_source_row is not None
                    and bool(aligned_candidates)
                    and selected_target_row["year"] > selected_source_row["year"]
                )
                else np.nan
            ),
            "directional_transfer_claim_allowed": False,
            "review_status": "pending_relation_and_full_text_review",
        }
        rows.append(row)
        for candidate in aligned_candidates:
            relation_source = units.loc[int(candidate["source"])]
            relation_target = units.loc[int(candidate["target"])]
            relation_mutual_nearest = False
            eligible_global_source = source_indices
            if relation_target["year"] > origin_year:
                eligible_global_source = source_indices[
                    units.loc[
                        source_indices, "year"
                    ].to_numpy(dtype=int)
                    < int(relation_target["year"])
                ]
            if len(eligible_global_source):
                nearest = int(
                    eligible_global_source[
                        np.argmax(
                            embeddings[eligible_global_source]
                            @ embeddings[int(candidate["target"])]
                        )
                    ]
                )
                relation_mutual_nearest = (
                    source_cluster_lookup.get(nearest) == cluster_label
                )
            relation_rows.append(
                {
                    "relation_candidate_id": stable_id(
                        "RELATION",
                        (
                            f"{theme_id}|"
                            f"{candidate['relation_temporal_class']}|"
                            f"{relation_source['insight_id']}|"
                            f"{relation_target['insight_id']}"
                        ),
                    ),
                    "theme_id": theme_id,
                    "relation_temporal_class": candidate[
                        "relation_temporal_class"
                    ],
                    "trajectory": candidate["trajectory"],
                    "alignment_cosine": float(candidate["score"]),
                    "alignment_band": alignment_band(
                        float(candidate["score"]),
                        possible_alignment,
                        strong_alignment,
                    ),
                    "mutual_nearest_theme_match": relation_mutual_nearest,
                    "iTE_theme_origin_year": origin_year,
                    "supporting_iTE_paper_count": source_paper_count,
                    "representative_iTE_insight_id": medoid["insight_id"],
                    "representative_iTE_paper_id": medoid["paper_id"],
                    "representative_iTE_claim": medoid["insight_claim"],
                    "matched_source_insight_id": relation_source[
                        "insight_id"
                    ],
                    "matched_source_paper_id": relation_source["paper_id"],
                    "matched_source_year": int(relation_source["year"]),
                    "matched_source_title": relation_source["title"],
                    "matched_source_doi": relation_source["doi"],
                    "matched_source_claim": relation_source["insight_claim"],
                    "matched_source_abstract": relation_source["abstract"],
                    "matched_source_intervention_evidence_sentence": (
                        relation_source["intervention_evidence_sentence"]
                    ),
                    "matched_source_mechanism_evidence_sentence": (
                        relation_source["mechanism_evidence_sentence"]
                    ),
                    "matched_source_outcome_evidence_sentence": (
                        relation_source["outcome_evidence_sentence"]
                    ),
                    "matched_source_exact_abstract_evidence_bundle": (
                        relation_source["exact_abstract_evidence_bundle"]
                    ),
                    "matched_target_role": candidate["target_role"],
                    "matched_target_insight_id": relation_target[
                        "insight_id"
                    ],
                    "matched_target_paper_id": relation_target["paper_id"],
                    "matched_target_year": int(relation_target["year"]),
                    "matched_target_title": relation_target["title"],
                    "matched_target_doi": relation_target["doi"],
                    "matched_target_claim": relation_target["insight_claim"],
                    "matched_target_abstract": relation_target["abstract"],
                    "matched_target_intervention_evidence_sentence": (
                        relation_target["intervention_evidence_sentence"]
                    ),
                    "matched_target_mechanism_evidence_sentence": (
                        relation_target["mechanism_evidence_sentence"]
                    ),
                    "matched_target_outcome_evidence_sentence": (
                        relation_target["outcome_evidence_sentence"]
                    ),
                    "matched_target_exact_abstract_evidence_bundle": (
                        relation_target["exact_abstract_evidence_bundle"]
                    ),
                    "temporal_lag_years": (
                        int(
                            relation_target["year"]
                            - relation_source["year"]
                        )
                        if relation_target["year"] > relation_source["year"]
                        else np.nan
                    ),
                    "direction_possible_by_time": bool(
                        relation_target["year"] > relation_source["year"]
                        and candidate["relation_temporal_class"]
                        in {
                            "later_TG_alignment_candidate",
                            "later_bridge_alignment_candidate",
                        }
                    ),
                    "directional_transfer_claim_allowed": False,
                    "review_status": (
                        "pending_relation_and_full_text_review"
                    ),
                }
            )
        for member_index in member_indices:
            member_rows.append(
                {
                    "theme_id": theme_id,
                    "insight_id": units.loc[member_index, "insight_id"],
                    "paper_id": units.loc[member_index, "paper_id"],
                    "year": int(units.loc[member_index, "year"]),
                    "insight_claim": units.loc[member_index, "insight_claim"],
                }
            )
    themes = pd.DataFrame(rows)
    themes["support_rank"] = percentile(
        themes["supporting_iTE_paper_count"]
    )
    themes["recency_rank"] = percentile(themes["recent_iTE_papers_3y"])
    themes["tg_proximity_rank"] = percentile(
        themes["current_TG_proximity_cosine"].fillna(-1)
    )
    themes["evidence_quality_rank"] = percentile(
        themes["representative_insight_id"].map(
            units.set_index("insight_id")[
                "claim_to_mechanism_sentence_cosine"
            ]
        ).fillna(0)
    )
    themes["TG_translation_review_priority"] = themes[
        [
            "support_rank",
            "recency_rank",
            "tg_proximity_rank",
            "evidence_quality_rank",
        ]
    ].mean(axis=1)
    themes["priority_note"] = (
        "Unweighted review-priority rank, not a probability or effect estimate."
    )
    return (
        themes.sort_values(
            [
                "TG_translation_review_priority",
                "supporting_iTE_paper_count",
            ],
            ascending=False,
        ).reset_index(drop=True),
        pd.DataFrame(member_rows),
        pd.DataFrame(relation_rows),
    )


def build_review_queues(
    themes: pd.DataFrame,
    relation_candidates: pd.DataFrame,
    possible_alignment: float,
    strong_alignment: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    alignment = relation_candidates.copy()
    alignment["relation_label_options"] = (
        "same_driver_same_effect | adapted_driver | thematic_similarity_only | reject"
    )
    alignment = alignment.sort_values(
        [
            "alignment_cosine",
            "mutual_nearest_theme_match",
            "supporting_iTE_paper_count",
        ],
        ascending=False,
    )

    transfer_cards = build_transfer_cards(themes, possible_alignment)
    opportunity = transfer_cards[
        transfer_cards["trajectory"].eq(
            "iTE-evidenced insight → TG translation opportunity"
        )
    ].copy()
    opportunity = opportunity.sort_values(
        [
            "TG_translation_review_priority",
            "supporting_iTE_paper_count",
        ],
        ascending=False,
    )

    bands = [
        (
            "strong",
            themes["selected_alignment_cosine"] >= strong_alignment,
        ),
        (
            "possible",
            themes["selected_alignment_cosine"].between(
                possible_alignment, strong_alignment, inclusive="left"
            ),
        ),
        (
            "near_threshold",
            themes["selected_alignment_cosine"].between(
                max(0.0, possible_alignment - 0.07),
                possible_alignment,
                inclusive="left",
            ),
        ),
        (
            "weak",
            themes["selected_alignment_cosine"]
            < max(0.0, possible_alignment - 0.07),
        ),
    ]
    samples = []
    for label, mask in bands:
        candidates = themes[mask].sort_values(
            "selected_alignment_cosine", ascending=False
        )
        if len(candidates) > 12:
            candidates = candidates.sample(
                n=12, random_state=RANDOM_STATE
            ).sort_values("selected_alignment_cosine", ascending=False)
        candidates = candidates.copy()
        candidates["audit_band"] = label
        samples.append(candidates)
    threshold_audit = pd.concat(samples, ignore_index=True)
    threshold_audit["manual_relation_label"] = ""
    threshold_audit["threshold_appropriate"] = ""
    threshold_audit["review_notes"] = ""
    return alignment, opportunity, transfer_cards, threshold_audit


def portable_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def validate_analysis(
    units: pd.DataFrame,
    themes: pd.DataFrame,
    theme_members: pd.DataFrame,
    alignment: pd.DataFrame,
    opportunity: pd.DataFrame,
    abstract_candidates: pd.DataFrame,
    possible_alignment: float,
    evidence_cosine: float,
    freeze_year: int,
) -> dict:
    primary = units[
        units["evidence_ready_for_primary_analysis"].fillna(False)
    ].copy()

    def exact_role_check(frame: pd.DataFrame, column: str) -> bool:
        values = frame[column].fillna("")
        abstracts = frame["abstract"].fillna("")
        return all(
            not value or value in abstract
            for value, abstract in zip(values, abstracts)
        )

    relation_time_checks = {
        "pre_existing_TG_candidate": lambda frame: (
            frame["matched_target_year"] < frame["iTE_theme_origin_year"]
        ).all(),
        "same_year_temporally_ambiguous_candidate": lambda frame: (
            frame["matched_target_year"] == frame["iTE_theme_origin_year"]
        ).all(),
        "later_TG_alignment_candidate": lambda frame: (
            frame["matched_target_year"] > frame["matched_source_year"]
        ).all(),
        "later_bridge_alignment_candidate": lambda frame: (
            frame["matched_target_year"] > frame["matched_source_year"]
        ).all(),
    }
    relation_time_passed = True
    for relation_class, checker in relation_time_checks.items():
        subset = alignment[
            alignment["relation_temporal_class"].eq(relation_class)
        ]
        if not subset.empty and not bool(checker(subset)):
            relation_time_passed = False

    member_support = (
        theme_members.groupby("theme_id")["paper_id"].nunique()
        if not theme_members.empty
        else pd.Series(dtype=int)
    )
    reported_support = themes.set_index("theme_id")[
        "supporting_iTE_paper_count"
    ]
    support_matches = reported_support.equals(
        member_support.reindex(reported_support.index).astype(int)
    )
    expected_relation_rows = int(
        themes[
            [
                "has_preexisting_TG_candidate",
                "has_same_year_TG_candidate",
                "has_later_TG_candidate",
                "has_later_bridge_candidate",
            ]
        ]
        .astype(int)
        .to_numpy()
        .sum()
    )
    opportunity_theme_ids = set(
        themes.loc[
            ~themes[
                [
                    "has_preexisting_TG_candidate",
                    "has_same_year_TG_candidate",
                    "has_later_TG_candidate",
                    "has_later_bridge_candidate",
                ]
            ].any(axis=1),
            "theme_id",
        ]
    )
    primary_ids = set(primary["insight_id"])
    member_ids = set(theme_members["insight_id"])
    checks = {
        "primary_insight_ids_unique": bool(
            primary["insight_id"].is_unique
        ),
        "theme_ids_unique": bool(themes["theme_id"].is_unique),
        "relation_candidate_ids_unique": bool(
            alignment["relation_candidate_id"].is_unique
        ),
        "abstract_candidate_ids_unique": bool(
            abstract_candidates["abstract_claim_candidate_id"].is_unique
        ),
        "primary_claims_partition_exactly_into_themes": (
            primary_ids == member_ids
        ),
        "theme_supporting_paper_counts_match_members": bool(
            support_matches
        ),
        "intervention_evidence_is_exact_abstract_substring": (
            exact_role_check(units, "intervention_evidence_sentence")
        ),
        "mechanism_evidence_is_exact_abstract_substring": (
            exact_role_check(units, "mechanism_evidence_sentence")
        ),
        "outcome_evidence_is_exact_abstract_substring": (
            exact_role_check(units, "outcome_evidence_sentence")
        ),
        "abstract_candidates_are_exact_substrings": all(
            sentence in abstract
            for sentence, abstract in zip(
                abstract_candidates[
                    "candidate_evidence_sentence"
                ].fillna(""),
                abstract_candidates["paper_id"].map(
                    units.drop_duplicates("paper_id").set_index("paper_id")[
                        "abstract"
                    ]
                ).fillna(""),
            )
        ),
        "primary_claims_meet_evidence_threshold": bool(
            primary["claim_to_mechanism_sentence_cosine"]
            .ge(evidence_cosine)
            .all()
        ),
        "primary_claims_have_causal_mechanism_role": bool(
            primary["mechanism_evidence_status"]
            .eq("cue_gated_role_selected")
            .all()
        ),
        "primary_claims_have_outcome_role": bool(
            ~primary["outcome_evidence_status"].eq("role_not_found").any()
        ),
        "primary_claims_are_not_reviews": bool(
            ~primary["likely_review"].astype(bool).any()
        ),
        "primary_claims_are_direct_iTE_scope": bool(
            primary["source_scope"].eq("core_iTE_evidenced_insight").all()
        ),
        "relation_rows_cover_all_nonexclusive_flags": (
            len(alignment) == expected_relation_rows
        ),
        "relation_rows_meet_similarity_threshold": bool(
            alignment["alignment_cosine"].ge(possible_alignment).all()
        ),
        "relation_chronology_is_consistent": relation_time_passed,
        "opportunity_partition_matches_no_relation_flags": (
            set(opportunity["theme_id"]) == opportunity_theme_ids
        ),
        "freeze_year_respected": bool(
            pd.to_numeric(units["year"], errors="coerce")
            .le(freeze_year)
            .all()
        ),
    }
    return {
        "all_passed": all(checks.values()),
        "checks": {
            name: {"passed": bool(passed)}
            for name, passed in checks.items()
        },
        "details": {
            "primary_claims": len(primary),
            "theme_member_claims": len(theme_members),
            "expected_relation_rows_from_flags": expected_relation_rows,
            "actual_relation_rows": len(alignment),
            "opportunity_themes": len(opportunity_theme_ids),
        },
    }


def write_readme(
    out: Path,
    freeze_year: int,
    counts: dict,
    theme_cosine: float,
    possible_alignment: float,
    strong_alignment: float,
    evidence_cosine: float,
) -> None:
    text = f"""# iTE-evidenced insight translation to TG

## Scientific task

This workflow asks:

> Which evidence-backed design insights from the iTE source corpus can inform
> TG research, and which later TG or bridge papers show a semantically aligned
> claim?

The analysis unit is a directional **claim/insight**, not a concept pair.
`iTE`, `TG`, and bridge labels record retrieval provenance; they do not mean a
mechanism is unique to one field.

## CIMO-E representation

Each claim retains:

- **Context:** paper, material system, and mapped concepts.
- **Intervention:** an exact abstract sentence describing the design action.
- **Mechanism:** the normalized mechanism claim plus its closest exact abstract
  evidence sentence.
- **Outcome:** an exact abstract result sentence, retaining quantitative detail
  when present.
- **Evidence:** paper ID, DOI, title, year, and the exact evidence bundle.

`mechanism_raw` is treated as a normalized navigation claim, not verbatim
evidence. Additional causal abstract sentences are exported separately and
must pass review before becoming independent insights.

## Frozen analysis

- Complete through: **{freeze_year}**.
- Directly evidenced iTE claim units in the primary analysis:
  **{counts['included_source_claims']}** from
  **{counts['included_source_papers']}** papers.
- Direct-scope claims held for evidence repair:
  **{counts['direct_source_scope_claims'] - counts['included_source_claims']}**.
- Adjacent ionic-transport references retained outside the primary analysis:
  **{counts['adjacent_source_claims']}** claims from
  **{counts['adjacent_source_papers']}** papers.
- Source papers already using TG/thermocell/redox-electrode coupling are routed
  separately: **{counts['coupled_source_claims']}** claims from
  **{counts['coupled_source_papers']}** papers.
- iTE insight themes: **{counts['themes']}**.
- Subsequent TG alignment candidates: **{counts['subsequent_tg']}**.
- Bridge alignment candidates: **{counts['bridge']}**.
- Pre-existing TG analogue candidates: **{counts['preexisting_tg']}**.
- Same-year, temporally ambiguous candidates: **{counts['same_year_tg']}**.
- TG translation opportunities: **{counts['opportunities']}**.
- Strong semantic audit candidates: **{counts['strong']}**.

Claims are grouped at cosine **{theme_cosine:.2f}**. Cross-corpus similarity
**≥{strong_alignment:.2f}** is a strong audit candidate,
**{possible_alignment:.2f}–{strong_alignment:.2f}** is a possible analogy, and
lower values are unaligned. These are provisional review thresholds, not
validated probabilities or proof of transfer.

Pre-existing, same-year, later-TG, and later-bridge statuses are recorded
independently and may co-occur for one theme. `trajectory` is only the
highest-similarity relation chosen for display.

Primary claims also require an exact causal mechanism sentence, an outcome
sentence, and claim-to-mechanism-evidence cosine
**≥{evidence_cosine:.2f}**. Missing CIMO-E roles are left blank rather than
filled with an unconstrained nearest sentence.

## Terminology

Use:

- `iTE-evidenced insight`
- `iTE-informed TG hypothesis`
- `TG translation opportunity`
- `subsequent TG alignment candidate`
- `bridge alignment candidate`

Do not use `iTE-only mechanism`, `TG-only mechanism`, or claim causal transfer
from semantic similarity alone.

## Main outputs

- `ite_primary_insight_claims.csv`: the direct, evidence-ready iTE claim set
  used for themes and TG translation.
- `ite_insight_claim_units.csv`: complete claim-level source inventory,
  including excluded and supplemental records.
- `ite_evidence_repair_queue.csv`: direct-scope claims held out because an
  exact mechanism/outcome role or the evidence-consistency threshold failed.
- `ite_adjacent_reference_supplement.csv`: adjacent ionic-transport references
  kept outside the primary ranking.
- `ite_source_already_tg_coupled.csv`: source records already using TG,
  thermocell, or redox-electrode coupling; these are context, not untested
  translation opportunities.
- `ite_to_tg_transfer_cards.csv`: every primary iTE theme translated into a
  structured TG hypothesis, bottleneck, adaptation, constraints, failure risk,
  and minimal validation experiment. These are reproducible rule-based drafts,
  not validated recommendations.
- `ite_abstract_claim_candidates.csv`: additional exact abstract sentences
  that may become separate insights after review.
- `ite_abstract_claim_adjudication.csv`: persistent reviewer decisions. Mark
  `include_as_separate_insight=true`; the next run promotes that exact sentence
  into its own insight without overwriting the decision file.
- `ite_insight_themes.csv`: deduplicated themes and their trajectories.
- `ite_to_tg_alignment_review_queue.csv`: exact source/target evidence for
  relation adjudication.
- `ite_tg_relation_adjudication.csv`: persistent relation/full-text decisions;
  regenerated review queues merge these decisions by stable relation ID.
- `tg_translation_opportunity_watchlist.csv`: the subset with no aligned TG
  claim at the current review threshold.
- `alignment_threshold_audit_sample.csv`: stratified sample for threshold QA.
- `tg_reference_claim_units.csv` and `bridge_claim_units.csv`: target evidence.
- `qa_invariants.json`: executable checks for IDs, evidence spans, theme
  membership, chronology, queue coverage, and the frozen year.
- `run_manifest.json`: frozen parameters, model snapshot, software, input and
  output hashes, row counts, review-state hashes, and invariant results.

## Important limits

- Semantic similarity can confuse shared vocabulary with the same causal
  mechanism. Every alignment must be classified as same driver/same effect,
  adapted driver, thematic similarity, or reject.
- Only direct iTE evidence enters the primary theme analysis. Adjacent ionic
  transport and broader cross-domain records remain visible in the claim table
  as supplements and are not silently discarded.
- The CIMO-E role sentences are heuristic selections from exact abstracts.
  They remain evidence anchors, not automatic causal extraction.
- Reviews are excluded by a conservative heuristic and still require manual
  study-type checking.
- Corpus completeness and the pre-existing concept vocabulary require
  independent documentation/curation before confirmatory publication.

## Re-run

```bash
python3 scripts/run_ite_insight_transfer.py --freeze-year {freeze_year}
```
"""
    (out / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    if not 0 < args.theme_cosine < 1:
        raise ValueError("--theme-cosine must be between 0 and 1.")
    if not 0 < args.possible_alignment < args.strong_alignment < 1:
        raise ValueError(
            "Alignment thresholds must satisfy 0 < possible < strong < 1."
        )
    if not 0 < args.evidence_cosine < 1:
        raise ValueError("--evidence-cosine must be between 0 and 1.")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    papers, mapping, vocab = load_data()
    papers = papers[papers["year"].between(1990, args.freeze_year)].copy()
    context = concept_context(mapping)

    source_papers = classify_source_scope(papers, mapping, vocab)
    target_papers = papers[papers["source_membership"].eq("TG")].copy()
    target_papers["likely_review"] = target_papers.apply(is_likely_review, axis=1)
    bridge_papers = papers[papers["source_membership"].eq("iTE|TG")].copy()
    bridge_papers["likely_review"] = bridge_papers.apply(is_likely_review, axis=1)

    source_units = build_claim_units(source_papers, "iTE_source", context)
    target_units = build_claim_units(target_papers, "TG_reference", context)
    bridge_units = build_claim_units(bridge_papers, "bridge", context)
    base_units = pd.concat(
        [source_units, target_units, bridge_units], ignore_index=True
    )
    base_units["_unit_index"] = np.arange(len(base_units))

    model = SentenceTransformer(MODEL_NAME, local_files_only=True)
    claim_embeddings = model.encode(
        base_units["insight_claim"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=128,
    )
    discovered_units, discovered_candidates = attach_cimo_evidence(
        base_units, claim_embeddings, model
    )
    abstract_adjudication = load_or_initialize_adjudication(
        out / "ite_abstract_claim_adjudication.csv",
        "abstract_claim_candidate_id",
        [
            "include_as_separate_insight",
            "reviewer_relation_type",
            "reviewer",
            "review_notes",
        ],
    )
    promoted_base_units, reviewed_candidates, promoted_count = (
        promote_approved_abstract_candidates(
            base_units,
            discovered_candidates,
            abstract_adjudication,
        )
    )
    if promoted_count:
        promoted_base_units = promoted_base_units.reset_index(drop=True)
        promoted_base_units["_unit_index"] = np.arange(
            len(promoted_base_units)
        )
        claim_embeddings = model.encode(
            promoted_base_units["insight_claim"].tolist(),
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=128,
        )
        units, rediscovered_candidates = attach_cimo_evidence(
            promoted_base_units,
            claim_embeddings,
            model,
        )
        _, abstract_candidates, _ = promote_approved_abstract_candidates(
            promoted_base_units,
            rediscovered_candidates,
            abstract_adjudication,
        )
    else:
        units = discovered_units
        abstract_candidates = reviewed_candidates
    source_scope_eligible = (
        units["source_analysis_included"].fillna(False).astype(bool)
    )
    units["evidence_ready_for_primary_analysis"] = (
        units["corpus_role"].eq("iTE_source")
        & source_scope_eligible
        & units["mechanism_evidence_status"].eq("cue_gated_role_selected")
        & ~units["outcome_evidence_status"].eq("role_not_found")
        & units["claim_to_mechanism_sentence_cosine"].ge(
            args.evidence_cosine
        )
    )
    units["primary_evidence_exclusion_reason"] = np.select(
        [
            units["evidence_ready_for_primary_analysis"],
            ~source_scope_eligible,
            units["mechanism_evidence_status"].eq("role_not_found"),
            units["outcome_evidence_status"].eq("role_not_found"),
            units["claim_to_mechanism_sentence_cosine"].lt(
                args.evidence_cosine
            ),
        ],
        [
            "",
            "not_in_direct_iTE_source_scope",
            "no_cue_gated_exact_mechanism_sentence",
            "no_cue_gated_exact_outcome_sentence",
            "claim_to_exact_mechanism_evidence_below_threshold",
        ],
        default="evidence_status_unresolved",
    )
    units.index = units["_unit_index"].astype(int)
    themes, theme_members, relation_candidates = build_themes_and_matches(
        units,
        claim_embeddings,
        args.theme_cosine,
        args.possible_alignment,
        args.strong_alignment,
        args.freeze_year,
    )
    alignment, opportunity, transfer_cards, threshold_audit = build_review_queues(
        themes,
        relation_candidates,
        args.possible_alignment,
        args.strong_alignment,
    )
    relation_adjudication = load_or_initialize_adjudication(
        out / "ite_tg_relation_adjudication.csv",
        "relation_candidate_id",
        [
            "relation_label",
            "source_evidence_verified",
            "target_evidence_verified",
            "target_study_type",
            "reviewer_1",
            "reviewer_2",
            "adjudication",
            "relation_confirmed",
            "directional_transfer_supported",
            "review_notes",
        ],
    )
    alignment = alignment.merge(
        relation_adjudication,
        on="relation_candidate_id",
        how="left",
    )
    for column in relation_adjudication.columns:
        if column != "relation_candidate_id":
            alignment[column] = alignment[column].fillna("")

    source_output = units[units["corpus_role"].eq("iTE_source")].drop(
        columns=["_unit_index", "_cluster"], errors="ignore"
    )
    primary_source_output = source_output[
        source_output["evidence_ready_for_primary_analysis"].fillna(False)
    ].copy()
    evidence_repair_output = source_output[
        source_output["source_analysis_included"].fillna(False).astype(bool)
        & ~source_output[
            "evidence_ready_for_primary_analysis"
        ].fillna(False)
    ].copy()
    adjacent_source_output = source_output[
        source_output["source_scope"].eq(
            "adjacent_ionic_transport_insight"
        )
    ].copy()
    coupled_source_output = source_output[
        source_output["source_scope"].eq(
            "already_TG_or_coupled_at_source"
        )
    ].copy()
    target_output = units[units["corpus_role"].eq("TG_reference")].drop(
        columns=["_unit_index", "_cluster"], errors="ignore"
    )
    bridge_output = units[units["corpus_role"].eq("bridge")].drop(
        columns=["_unit_index", "_cluster"], errors="ignore"
    )
    source_output.to_csv(out / "ite_insight_claim_units.csv", index=False)
    primary_source_output.to_csv(
        out / "ite_primary_insight_claims.csv", index=False
    )
    evidence_repair_output.to_csv(
        out / "ite_evidence_repair_queue.csv", index=False
    )
    adjacent_source_output.to_csv(
        out / "ite_adjacent_reference_supplement.csv", index=False
    )
    coupled_source_output.to_csv(
        out / "ite_source_already_tg_coupled.csv", index=False
    )
    target_output.to_csv(out / "tg_reference_claim_units.csv", index=False)
    bridge_output.to_csv(out / "bridge_claim_units.csv", index=False)
    primary_source_paper_ids = set(
        units.loc[
            units["evidence_ready_for_primary_analysis"].fillna(False),
            "paper_id",
        ]
    )
    primary_abstract_candidates = abstract_candidates[
        abstract_candidates["corpus_role"].eq("iTE_source")
        & abstract_candidates["paper_id"].isin(primary_source_paper_ids)
    ].copy()
    primary_abstract_candidates.to_csv(
        out / "ite_abstract_claim_candidates.csv", index=False
    )
    themes.to_csv(out / "ite_insight_themes.csv", index=False)
    theme_members.to_csv(out / "ite_insight_theme_members.csv", index=False)
    alignment.to_csv(
        out / "ite_to_tg_alignment_review_queue.csv", index=False
    )
    opportunity.to_csv(
        out / "tg_translation_opportunity_watchlist.csv", index=False
    )
    transfer_cards.to_csv(out / "ite_to_tg_transfer_cards.csv", index=False)
    threshold_audit.to_csv(
        out / "alignment_threshold_audit_sample.csv", index=False
    )

    counts = {
        "source_claims_all": int(
            units["corpus_role"].eq("iTE_source").sum()
        ),
        "approved_abstract_claims_promoted": int(promoted_count),
        "direct_source_scope_claims": int(
            (
                units["corpus_role"].eq("iTE_source")
                & units["source_analysis_included"].fillna(False)
            ).sum()
        ),
        "included_source_claims": int(
            (
                units["corpus_role"].eq("iTE_source")
                & units["evidence_ready_for_primary_analysis"].fillna(False)
            ).sum()
        ),
        "included_source_papers": int(
            units.loc[
                units["corpus_role"].eq("iTE_source")
                & units["evidence_ready_for_primary_analysis"].fillna(False),
                "paper_id",
            ].nunique()
        ),
        "coupled_source_claims": int(
            (
                units["corpus_role"].eq("iTE_source")
                & units["source_scope"].eq(
                    "already_TG_or_coupled_at_source"
                )
            ).sum()
        ),
        "coupled_source_papers": int(
            units.loc[
                units["corpus_role"].eq("iTE_source")
                & units["source_scope"].eq(
                    "already_TG_or_coupled_at_source"
                ),
                "paper_id",
            ].nunique()
        ),
        "adjacent_source_claims": int(
            (
                units["corpus_role"].eq("iTE_source")
                & units["source_scope"].eq(
                    "adjacent_ionic_transport_insight"
                )
            ).sum()
        ),
        "adjacent_source_papers": int(
            units.loc[
                units["corpus_role"].eq("iTE_source")
                & units["source_scope"].eq(
                    "adjacent_ionic_transport_insight"
                ),
                "paper_id",
            ].nunique()
        ),
        "target_claims": int(
            units["corpus_role"].eq("TG_reference").sum()
        ),
        "bridge_claims": int(units["corpus_role"].eq("bridge").sum()),
        "themes": len(themes),
        "subsequent_tg": int(
            themes["has_later_TG_candidate"].sum()
        ),
        "bridge": int(
            themes["has_later_bridge_candidate"].sum()
        ),
        "preexisting_tg": int(
            themes["has_preexisting_TG_candidate"].sum()
        ),
        "same_year_tg": int(
            themes["has_same_year_TG_candidate"].sum()
        ),
        "opportunities": len(opportunity),
        "strong": int(
            alignment["alignment_band"].eq(
                "strong_semantic_audit_candidate"
            ).sum()
        ),
        "abstract_claim_candidates": len(primary_abstract_candidates),
        "relation_review_candidates": len(alignment),
    }
    generated_at_utc = datetime.now(timezone.utc).isoformat()
    summary = {
        "generated_on": date.today().isoformat(),
        "generated_at_utc": generated_at_utc,
        "task": "iTE-evidenced insight translation to TG",
        "analysis_unit": "directional claim with CIMO-E evidence anchors",
        "freeze_year": args.freeze_year,
        "theme_cosine": args.theme_cosine,
        "possible_alignment": args.possible_alignment,
        "strong_alignment": args.strong_alignment,
        "evidence_cosine": args.evidence_cosine,
        "counts": counts,
        "interpretation": (
            "Semantic alignments and opportunities are manual-review queues, "
            "not probabilities or causal transfer claims."
        ),
    }
    (out / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    write_readme(
        out,
        args.freeze_year,
        counts,
        args.theme_cosine,
        args.possible_alignment,
        args.strong_alignment,
        args.evidence_cosine,
    )
    qa = validate_analysis(
        units,
        themes,
        theme_members,
        alignment,
        opportunity,
        primary_abstract_candidates,
        args.possible_alignment,
        args.evidence_cosine,
        args.freeze_year,
    )
    (out / "qa_invariants.json").write_text(
        json.dumps(qa, indent=2), encoding="utf-8"
    )
    if not qa["all_passed"]:
        failed = [
            name
            for name, result in qa["checks"].items()
            if not result["passed"]
        ]
        raise RuntimeError(
            "Analysis invariants failed: " + ", ".join(failed)
        )

    input_paths = [
        DATA / "final_paper_index.csv",
        DATA / "final_paper_concept_map.csv",
        FLOW / "pure_mechanism_vocabulary.csv",
    ]
    generated_output_rows = {
        "ite_insight_claim_units.csv": len(source_output),
        "ite_primary_insight_claims.csv": len(primary_source_output),
        "ite_evidence_repair_queue.csv": len(evidence_repair_output),
        "ite_adjacent_reference_supplement.csv": len(
            adjacent_source_output
        ),
        "ite_source_already_tg_coupled.csv": len(coupled_source_output),
        "tg_reference_claim_units.csv": len(target_output),
        "bridge_claim_units.csv": len(bridge_output),
        "ite_abstract_claim_candidates.csv": len(
            primary_abstract_candidates
        ),
        "ite_insight_themes.csv": len(themes),
        "ite_insight_theme_members.csv": len(theme_members),
        "ite_to_tg_alignment_review_queue.csv": len(alignment),
        "tg_translation_opportunity_watchlist.csv": len(opportunity),
        "ite_to_tg_transfer_cards.csv": len(transfer_cards),
        "alignment_threshold_audit_sample.csv": len(threshold_audit),
        "analysis_summary.json": None,
        "README.md": None,
        "qa_invariants.json": None,
    }
    generated_output_paths = [
        out / filename for filename in generated_output_rows
    ]
    script_hash = sha256(Path(__file__).resolve())
    run_id = stable_id("RUN", f"{generated_at_utc}|{script_hash}")
    model_config = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--sentence-transformers--all-MiniLM-L6-v2"
        / "snapshots"
        / MODEL_SNAPSHOT_REVISION
        / "config.json"
    )
    manifest = {
        "run_id": run_id,
        "script_version": SCRIPT_VERSION,
        "script_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "script_sha256": script_hash,
        "generated_on": date.today().isoformat(),
        "generated_at_utc": generated_at_utc,
        "parameters": {
            "freeze_year": args.freeze_year,
            "theme_cosine": args.theme_cosine,
            "possible_alignment": args.possible_alignment,
            "strong_alignment": args.strong_alignment,
            "evidence_cosine": args.evidence_cosine,
            "embedding_model": MODEL_NAME,
            "embedding_model_snapshot_revision": MODEL_SNAPSHOT_REVISION,
            "embedding_model_config_sha256": (
                sha256(model_config) if model_config.exists() else ""
            ),
            "random_state": RANDOM_STATE,
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "sentence_transformers": sentence_transformers.__version__,
        },
        "inputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in input_paths
        ],
        "review_state": [
            {
                "path": portable_path(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in [
                out / "ite_abstract_claim_adjudication.csv",
                out / "ite_tg_relation_adjudication.csv",
            ]
        ],
        "outputs": [
            {
                "path": path.name,
                "rows": generated_output_rows[path.name],
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in generated_output_paths
        ],
        "invariants": qa,
    }
    (out / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print("iTE-evidenced insight → TG translation analysis complete")
    print(f"Output: {out}")
    print(json.dumps(counts, indent=2))
    print("\nTop alignment audit candidates")
    columns = [
        "trajectory",
        "alignment_cosine",
        "representative_iTE_claim",
        "matched_target_claim",
    ]
    print(alignment[columns].head(10).to_string(index=False))
    print("\nTop TG translation opportunities")
    print(
        opportunity[
            [
                "TG_translation_review_priority",
                "supporting_iTE_paper_count",
                "representative_iTE_claim",
                "transfer_family",
                "iTE_informed_TG_hypothesis",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
