from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("/Users/ryan/Documents/iTE&TG")
DATA = ROOT / "minimal_clean_concept_layer"
OUT = ROOT / "mechanism_transfer_workflow"
OUT.mkdir(exist_ok=True)

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

EXCLUDE_LABELS = {
    # Solid-state thermoelectric mechanisms do not yet define the TG mechanism space.
    "electronic-structure modulation",
    "carrier-concentration optimization",
    "lattice thermal-conductivity suppression",
    "phonon scattering",
    "anharmonic phonon transport",
    "charge-carrier mobility",
    "mixed ionic-covalent bonding",
    "rattling-mode phonon suppression",
    "superionic transition",
    "polaron hopping",
    "defect engineering",
    "band engineering",
    "alloy/disorder phonon scattering",
    "electron-phonon coupling",
    "grain-boundary scattering",
    "energy filtering",
    # Material/redox-system labels, not atomic mechanisms.
    "ferri/ferrocyanide redox chemistry",
    "Fe2+/Fe3+ solvation redox chemistry",
    "iodide/triiodide redox chemistry",
    "organic redox molecular design",
    "Cu-based n/p redox thermocell",
    "Cu-ethylenediamine chelation entropy",
    # Specific material, electrode, device, or formulation labels.
    "hexacyanoferrate redox electrode",
    "biomass-derived porous carbon electrode",
    "carbon electrode",
    "metal-oxide nanostructured electrode",
    "porous/pin-electrode thermal-gradient architecture",
    "cellulose nanofiber scaffold",
    "double-network hydrogel",
    "interpenetrating-network thermogalvanic hydrogel",
    "water-state regulated MXene hydrogel",
    "thermogalvanic redox conversion",
    "thermally regenerative electrochemical cycle",
    "thermogalvanic corrosion",
    "piezoresistive-thermoelectric coupling",
    "biphase-solvation liquid thermocell",
    "molecular-chaperone redox-gradient stabilization",
    "Ni-bipyridine hydration-shell entropy",
    "high-entropy gel thermocell",
    "solvent-shell water/DES regulation",
    "redox-layer ionic-gradient cell",
    "polymer-electrolyte Soret spectroscopy",
    "GelMA ion-induced crystallization",
}


def pair_first_year(
    mapping: pd.DataFrame, papers: pd.DataFrame, paper_ids: set[str]
) -> pd.DataFrame:
    subset = mapping[mapping.paper_id.isin(paper_ids)].merge(
        papers[["paper_id", "year"]], on="paper_id", how="left"
    )
    rows = []
    for paper_id, group in subset.groupby("paper_id"):
        concepts = sorted(group.concept_id.unique())
        year = int(group.year.iloc[0])
        for u, v in combinations(concepts, 2):
            rows.append(
                {
                    "concept_u_id": u,
                    "concept_v_id": v,
                    "year": year,
                    "paper_id": paper_id,
                }
            )
    evidence = pd.DataFrame(rows)
    if evidence.empty:
        return evidence
    first = (
        evidence.sort_values(["year", "paper_id"])
        .groupby(["concept_u_id", "concept_v_id"], as_index=False)
        .agg(
            first_year=("year", "min"),
            first_evidence_paper=("paper_id", "first"),
            evidence_papers=("paper_id", "nunique"),
        )
    )
    return first


def main() -> None:
    vocab = pd.read_csv(DATA / "final_concept_vocabulary.csv")
    mapping = pd.read_csv(DATA / "final_paper_concept_map.csv")
    papers = pd.read_csv(DATA / "final_paper_index.csv")
    papers["year"] = pd.to_numeric(papers.year, errors="coerce")

    candidates = vocab[vocab.concept_type.isin(MECHANISM_TYPES)].copy()
    candidates["pure_mechanism"] = ~candidates.canonical_concept.isin(EXCLUDE_LABELS)
    candidates["curation_reason"] = np.where(
        candidates.pure_mechanism,
        "retained_atomic_or_generic_mechanism",
        "excluded_material_system_device_or_solid_state_label",
    )
    pure = candidates[candidates.pure_mechanism].copy()
    pure_ids = set(pure.concept_id)
    clean_mapping = mapping[mapping.concept_id.isin(pure_ids)].copy()

    ite_ids = set(
        papers[papers.source_membership.str.contains("iTE", na=False)].paper_id
    )
    tg_ids = set(
        papers[papers.source_membership.str.contains("TG", na=False)].paper_id
    )
    ite = pair_first_year(clean_mapping, papers, ite_ids).rename(
        columns={
            "first_year": "ite_first_year",
            "first_evidence_paper": "ite_first_evidence_paper",
            "evidence_papers": "ite_evidence_papers",
        }
    )
    tg = pair_first_year(clean_mapping, papers, tg_ids).rename(
        columns={
            "first_year": "tg_first_year",
            "first_evidence_paper": "tg_first_evidence_paper",
            "evidence_papers": "tg_evidence_papers",
        }
    )
    events = ite.merge(tg, on=["concept_u_id", "concept_v_id"], how="outer")
    labels = pure.set_index("concept_id").canonical_concept.to_dict()
    types = pure.set_index("concept_id").concept_type.to_dict()
    events["concept_u"] = events.concept_u_id.map(labels)
    events["concept_v"] = events.concept_v_id.map(labels)
    events["u_type"] = events.concept_u_id.map(types)
    events["v_type"] = events.concept_v_id.map(types)
    conditions = [
        events.ite_first_year.isna(),
        events.tg_first_year.isna(),
        events.ite_first_year < events.tg_first_year,
        events.ite_first_year == events.tg_first_year,
    ]
    choices = ["TG_only", "iTE_only", "iTE_then_TG", "same_year"]
    events["transfer_status"] = np.select(
        conditions, choices, default="TG_then_iTE"
    )
    events["transfer_lag_years"] = (
        events.tg_first_year - events.ite_first_year
    )
    events = events[
        [
            "concept_u_id",
            "concept_v_id",
            "concept_u",
            "concept_v",
            "u_type",
            "v_type",
            "ite_first_year",
            "tg_first_year",
            "transfer_lag_years",
            "transfer_status",
            "ite_first_evidence_paper",
            "tg_first_evidence_paper",
            "ite_evidence_papers",
            "tg_evidence_papers",
        ]
    ].sort_values(
        ["transfer_status", "tg_first_year", "ite_first_year"]
    )

    transfers = events[events.transfer_status.eq("iTE_then_TG")].copy()
    lag_summary = transfers.transfer_lag_years.describe().rename("value")
    status_summary = events.transfer_status.value_counts().rename_axis(
        "transfer_status"
    ).reset_index(name="pair_count")
    annual = (
        transfers.groupby("tg_first_year")
        .size()
        .rename("new_iTE_to_TG_transfers")
        .reset_index()
    )

    candidates.to_csv(OUT / "mechanism_node_curation.csv", index=False)
    pure.to_csv(OUT / "pure_mechanism_vocabulary.csv", index=False)
    clean_mapping.to_csv(OUT / "pure_mechanism_paper_map.csv", index=False)
    events.to_csv(OUT / "mechanism_pair_transfer_events.csv", index=False)
    transfers.to_csv(OUT / "observed_ite_to_tg_transfers.csv", index=False)
    status_summary.to_csv(OUT / "transfer_status_summary.csv", index=False)
    lag_summary.to_csv(OUT / "transfer_lag_summary.csv")
    annual.to_csv(OUT / "annual_transfer_counts.csv", index=False)
    print("candidate mechanism nodes", len(candidates))
    print("pure mechanism nodes", len(pure))
    print(status_summary.to_string(index=False))
    print("\nlag summary")
    print(lag_summary.to_string())


if __name__ == "__main__":
    main()
