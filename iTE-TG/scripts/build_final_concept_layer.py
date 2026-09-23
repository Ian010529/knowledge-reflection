from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
SOURCE_DIR = Path("/Users/ryan/Documents/iTE&TG/source_tables")
OPEN_DIR = Path("/Users/ryan/Documents/iTE&TG/figures_and_results/open_concepts_iter")
OUT = ROOT / "work" / "final_concept_layer"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "work"))
import tg_adoption_prediction_demo as curated  # noqa: E402


SOURCES = [
    ("TG_first333_material_mechanism.csv", "TG"),
    ("iTE1_first1000_material_mechanism.csv", "iTE1"),
    ("iTE2_first711_material_mechanism.csv", "iTE2"),
]

TYPE_PARENT = {
    "material_entity": "materials and chemical species",
    "material_system": "materials and chemical species",
    "redox_chemistry": "chemical and redox mechanisms",
    "solvation_entropy": "chemical and redox mechanisms",
    "transport_mechanism": "transport mechanisms",
    "electrode_interface": "interfaces and kinetics",
    "phase_or_species_transition": "phase and species transitions",
    "gel_microstructure": "soft-material structure",
    "solid_state_mechanism": "solid-state transport mechanisms",
    "device_mechanism": "device-scale conversion mechanisms",
    "device_function": "device and system functions",
    "property_metric": "properties and metrics",
    "characterization_method": "experimental methods",
    "computational_method": "computational methods",
}

CORE_TYPES = {
    "material_entity",
    "material_system",
    "redox_chemistry",
    "solvation_entropy",
    "transport_mechanism",
    "electrode_interface",
    "phase_or_species_transition",
    "gel_microstructure",
    "solid_state_mechanism",
    "device_mechanism",
}

BACKGROUND_TYPES = {
    "device_function",
    "property_metric",
    "characterization_method",
    "computational_method",
}


def norm_space(text: object) -> str:
    value = "" if pd.isna(text) else str(text)
    value = value.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", " ", value).strip()


def norm_key(text: object) -> str:
    value = norm_space(text).lower()
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_doi(value: object) -> str:
    doi = norm_space(value).lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.strip(" .;,")


def stable_concept_id(label: str) -> str:
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10].upper()
    return f"C{digest}"


def read_sources() -> tuple[pd.DataFrame, dict[str, str]]:
    rows = []
    for filename, source in SOURCES:
        data = pd.read_csv(SOURCE_DIR / filename)
        for idx, row in data.iterrows():
            legacy_id = f"{source}_{idx:04d}"
            doi = clean_doi(row.get("DOI", ""))
            title = norm_space(row.get("文章名", ""))
            dedupe_key = f"doi:{doi}" if doi else f"title:{norm_key(title)}"
            rows.append(
                {
                    "legacy_id": legacy_id,
                    "dedupe_key": dedupe_key,
                    "source": source,
                    "source_family": "TG" if source == "TG" else "iTE",
                    "year": pd.to_numeric(row.get("年份"), errors="coerce"),
                    "title": title,
                    "journal": norm_space(row.get("期刊名", "")),
                    "doi": doi,
                    "abstract": norm_space(row.get("摘要", "")),
                    "material_raw": norm_space(row.get("材料", "")),
                    "mechanism_raw": norm_space(row.get("机制", "")),
                }
            )
    raw = pd.DataFrame(rows)

    paper_rows = []
    legacy_to_paper = {}
    for number, (dedupe_key, group) in enumerate(raw.groupby("dedupe_key", sort=False), start=1):
        group = group.sort_values(
            ["source_family", "abstract"],
            key=lambda col: col.map({"TG": 0, "iTE": 1}) if col.name == "source_family" else col.str.len(),
            ascending=[True, False],
        )
        best = group.iloc[0]
        paper_id = f"P{number:04d}"
        for legacy_id in group["legacy_id"]:
            legacy_to_paper[legacy_id] = paper_id
        source_membership = "|".join(
            value for value in ["iTE", "TG"] if value in set(group["source_family"])
        )
        paper_rows.append(
            {
                "paper_id": paper_id,
                "source_membership": source_membership,
                "source_records": "|".join(group["legacy_id"]),
                "year": int(group["year"].dropna().min()) if group["year"].notna().any() else None,
                "title": best["title"],
                "journal": best["journal"],
                "doi": best["doi"],
                "abstract": best["abstract"],
                "material_raw": best["material_raw"],
                "mechanism_raw": best["mechanism_raw"],
            }
        )
    papers = pd.DataFrame(paper_rows)
    return papers, legacy_to_paper


def rule(
    label: str,
    concept_type: str,
    subtype: str,
    pattern: str,
    fields: tuple[str, ...] = ("material_raw", "mechanism_raw", "abstract", "title"),
    confidence: float = 0.94,
) -> dict:
    return {
        "label": label,
        "concept_type": concept_type,
        "subtype": subtype,
        "pattern": re.compile(pattern, re.I),
        "fields": fields,
        "confidence": confidence,
    }


RULES = [
    # Material platforms and matrices
    rule("hydrogel", "material_system", "soft material platform", r"\bhydrogel(s)?\b"),
    rule("ionogel", "material_system", "soft material platform", r"\bionogel(s)?\b"),
    rule("organohydrogel", "material_system", "soft material platform", r"\borganohydrogel(s)?\b"),
    rule("eutogel", "material_system", "soft material platform", r"\beutogel(s)?\b"),
    rule("deep eutectic solvent", "material_system", "electrolyte and solvent", r"\bdeep[- ]eutectic (solvent|electrolyte)|\bDES\b"),
    rule("ionic liquid", "material_system", "electrolyte and solvent", r"\bionic[- ]liquid(s)?\b|\bIL[- ]based\b"),
    rule("aqueous electrolyte", "material_system", "electrolyte and solvent", r"\baqueous electrolyte\b"),
    rule("polymer electrolyte", "material_system", "electrolyte and solvent", r"\bpolymer electrolyte\b"),
    rule("solid electrolyte", "material_system", "electrolyte and solvent", r"\bsolid[- ]state electrolyte\b|\bsolid electrolyte\b"),
    rule("ion-selective membrane", "material_system", "membrane", r"\bion[- ]selective membrane\b|\bselective ion membrane\b"),
    rule("nanochannel membrane", "material_system", "membrane", r"\bnanochannel membrane\b|\bnanoporous membrane\b"),
    rule("poly(vinyl alcohol) (PVA)", "material_entity", "polymer", r"\bpoly\(vinyl alcohol\)\b|\bPVA\b"),
    rule("polyacrylamide (PAM)", "material_entity", "polymer", r"\bpolyacrylamide\b|\bPAM\b"),
    rule("poly(acrylic acid) (PAA)", "material_entity", "polymer", r"\bpoly\(acrylic acid\)\b|\bPAA\b"),
    rule("PEDOT:PSS", "material_entity", "conducting polymer", r"\bPEDOT[:/\- ]PSS\b|\bPEDOT\.PSS\b"),
    rule("PEDOT", "material_entity", "conducting polymer", r"\bPEDOT\b"),
    rule("polyvinylpyrrolidone (PVP)", "material_entity", "polymer", r"\bpolyvinyl ?pyrrolidone\b|\bPVP\b"),
    rule("polyethylene glycol (PEG)", "material_entity", "polymer", r"\bpolyethylene glycol\b|\bPEG\b"),
    rule("polyurethane (PU)", "material_entity", "polymer", r"\bpolyurethane\b|\bPU\b"),
    rule("polyvinylidene fluoride (PVDF)", "material_entity", "polymer", r"\bPVDF\b|\bpolyvinylidene fluoride\b"),
    rule("Nafion", "material_entity", "ionomer", r"\bNafion\b"),
    rule("cellulose", "material_entity", "biopolymer", r"\bcellulose\b"),
    rule("cellulose nanofiber (CNF)", "material_entity", "biopolymer", r"\bcellulose nanofib(er|re)s?\b|\bCNF\b"),
    rule("bacterial cellulose", "material_entity", "biopolymer", r"\bbacterial cellulose\b"),
    rule("chitosan", "material_entity", "biopolymer", r"\bchitosan\b"),
    rule("alginate", "material_entity", "biopolymer", r"\balginate\b"),
    rule("gelatin", "material_entity", "biopolymer", r"\bgelatin\b"),
    rule("GelMA", "material_entity", "biopolymer", r"\bGelMA\b|gelatin methacryloyl"),
    rule("carrageenan", "material_entity", "biopolymer", r"\bcarrageenan\b"),
    rule("MXene", "material_entity", "two-dimensional material", r"\bMXene(s)?\b|\bTi3C2T[xX]\b"),
    rule("Ti3C2Tx MXene", "material_entity", "two-dimensional material", r"\bTi3C2T[xX]\b"),
    rule("graphene oxide", "material_entity", "carbon material", r"\bgraphene oxide\b|\bGO\b"),
    rule("reduced graphene oxide", "material_entity", "carbon material", r"\breduced graphene oxide\b|\brGO\b"),
    rule("graphene", "material_entity", "carbon material", r"\bgraphene\b"),
    rule("carbon nanotube", "material_entity", "carbon material", r"\bcarbon nanotube(s)?\b|\bCNT(s)?\b|\bMWCNT(s)?\b"),
    rule("carbon cloth", "material_entity", "electrode material", r"\bcarbon cloth\b"),
    rule("porous carbon", "material_entity", "electrode material", r"\bporous carbon\b"),
    rule("MoS2", "material_entity", "two-dimensional material", r"\bMoS2\b"),
    rule("Bi2Te3", "material_entity", "solid thermoelectric", r"\bBi2Te3\b"),
    rule("Sb2Te3", "material_entity", "solid thermoelectric", r"\bSb2Te3\b"),
    rule("Bi2Se3", "material_entity", "solid thermoelectric", r"\bBi2Se3\b"),
    rule("SnSe", "material_entity", "solid thermoelectric", r"\bSnSe\b"),
    rule("skutterudite", "material_system", "solid thermoelectric family", r"\bskutterudite(s)?\b"),
    rule("half-Heusler alloy", "material_system", "solid thermoelectric family", r"\bhalf[- ]Heusler\b"),
    rule("Zintl phase", "material_system", "solid thermoelectric family", r"\bZintl\b"),
    rule("clathrate", "material_system", "solid thermoelectric family", r"\bclathrate(s)?\b"),
    rule("perovskite", "material_system", "solid thermoelectric family", r"\bperovskite(s)?\b"),
    rule("chalcogenide", "material_system", "solid thermoelectric family", r"\bchalcogenide(s)?\b"),
    rule("metal oxide", "material_system", "inorganic material family", r"\bmetal[- ]oxide\b|\boxide (ceramic|semiconductor|thermoelectric)\b"),
    rule("metal sulfide", "material_system", "inorganic material family", r"\bmetal sulfide\b|\bsulfide (semiconductor|thermoelectric)\b"),
    rule("metal selenide", "material_system", "inorganic material family", r"\bmetal selenide\b|\bselenide (semiconductor|thermoelectric)\b"),
    rule("metal telluride", "material_system", "inorganic material family", r"\bmetal telluride\b|\btelluride (semiconductor|thermoelectric)\b"),
    rule("metal hydride", "material_system", "inorganic material family", r"\bmetal hydride(s)?\b"),
    rule("thermoelectric alloy", "material_system", "solid thermoelectric family", r"\bthermoelectric alloy(s)?\b|\balloy thermoelectric\b"),
    rule("nanocomposite", "material_system", "composite material", r"\bnanocomposite(s)?\b"),
    rule("cement-based ionic material", "material_system", "porous ionic material", r"\bcement[- ]based\b|\bPortland cement\b"),
    rule("molten salt", "material_system", "electrolyte and solvent", r"\bmolten salt(s)?\b|\beutectic melt\b"),
    rule("copper electrode", "material_entity", "electrode material", r"\bcopper electrode(s)?\b|\bCu electrode(s)?\b"),
    rule("platinum electrode", "material_entity", "electrode material", r"\bplatinum electrode(s)?\b|\bPt electrode(s)?\b"),
    rule("gold electrode", "material_entity", "electrode material", r"\bgold electrode(s)?\b|\bAu electrode(s)?\b"),
    rule("iron electrode", "material_entity", "electrode material", r"\biron (plate|electrode)\b|\bFe electrode(s)?\b"),
    rule("zinc electrode", "material_entity", "electrode material", r"\bzinc electrode(s)?\b|\bZn electrode(s)?\b"),
    # Redox species and functional additives
    rule("ferri/ferrocyanide", "material_entity", "redox couple", r"ferri/?ferrocyanide|ferrocyanide/?ferricyanide|\[?Fe\(CN\)6\]?[34][+\-/]*"),
    rule("Fe2+/Fe3+", "material_entity", "redox couple", r"\bFe2\+/?Fe3\+\b|\bFe3\+/?Fe2\+\b|\bferrous/?ferric\b"),
    rule("iodide/triiodide", "material_entity", "redox couple", r"\biodide/?triiodide\b|\bI-?/?I3-?\b|\bI3-\b"),
    rule("hydroquinone/benzoquinone", "material_entity", "redox couple", r"\bhydroquinone\b|\bbenzoquinone\b|\bHQ/?BQ\b"),
    rule("ferrocene/ferrocenium", "material_entity", "redox couple", r"\bferrocene\b|\bferrocenium\b"),
    rule("TEMPO", "material_entity", "organic redox species", r"\bTEMPO\b"),
    rule("viologen", "material_entity", "organic redox species", r"\bviologen\b"),
    rule("guanidinium chloride (GdmCl)", "material_entity", "functional additive", r"\bguanidinium( chloride)?\b|\bguanidine hydrochloride\b|\bGdmCl\b"),
    rule("urea", "material_entity", "functional additive", r"\burea\b"),
    rule("glycerol", "material_entity", "solvent/additive", r"\bglycerol\b"),
    rule("ethylene glycol", "material_entity", "solvent/additive", r"\bethylene glycol\b|\bEG\b"),
    rule("dimethyl sulfoxide (DMSO)", "material_entity", "solvent/additive", r"\bdimethyl sulfoxide\b|\bDMSO\b"),
    rule("lithium bromide (LiBr)", "material_entity", "salt", r"\bLiBr\b|\blithium bromide\b"),
    rule("lithium chloride (LiCl)", "material_entity", "salt", r"\bLiCl\b|\blithium chloride\b"),
    rule("sodium perchlorate (NaClO4)", "material_entity", "salt", r"\bNaClO4\b|\bsodium perchlorate\b"),
    rule("potassium iodide (KI)", "material_entity", "salt", r"\bpotassium iodide\b|\bKI\b"),
    # Ionic and redox mechanisms
    rule("ionic thermodiffusion (Soret effect)", "transport_mechanism", "thermodiffusion", r"\bSoret( effect| thermodiffusion)?\b|\bion(ic)? thermodiffusion\b|\bthermophoretic\b"),
    rule("cation-anion thermodiffusion asymmetry", "transport_mechanism", "thermodiffusion", r"cation.?anion thermodiffusion asymmetry|mobility difference between .* (cation|anion)|thermophoretic difference"),
    rule("ion migration", "transport_mechanism", "ionic transport", r"\bion(ic)? migration\b|\bmigration of (ions|cations|anions)\b"),
    rule("ion diffusion", "transport_mechanism", "ionic transport", r"\bion(ic)? diffusion\b|\bdiffusion of (ions|cations|anions)\b"),
    rule("selective ion transport", "transport_mechanism", "ionic transport", r"\bselective ion (transport|migration|conduction)\b|\bion selectivity\b"),
    rule("nanochannel-confined ion transport", "transport_mechanism", "ionic transport", r"\bnanochannel.*ion (transport|migration|conduction)|\bion.*nanochannel\b"),
    rule("Manning counterion condensation", "transport_mechanism", "ionic transport", r"\bManning counterion condensation\b|\bcounterion condensation\b"),
    rule("ion concentration-gradient formation", "transport_mechanism", "concentration gradient", r"\bion(ic)? concentration gradient\b|\bredox[- ]ion concentration gradient\b"),
    rule("convection and mass transport", "transport_mechanism", "mass transport", r"\bconvection\b|\bconvective mass transfer\b|\bmass transport\b"),
    rule("redox reaction entropy", "solvation_entropy", "redox thermodynamics", r"\bredox (reaction )?entropy( change| difference)?\b|\breaction entropy change\b"),
    rule("Eastman entropy of transfer", "solvation_entropy", "ionic thermodynamics", r"\bEastman entropy\b|\bentropy of transfer\b"),
    rule("selective solvation", "solvation_entropy", "solvation", r"\bselective solvation\b"),
    rule("solvation-shell remodeling", "solvation_entropy", "solvation", r"\bsolvation[- ]shell (remodel|reorgan|regulat|modulat)|\bchanges? .* solvation shell\b"),
    rule("hydration-shell regulation", "solvation_entropy", "hydration", r"\bhydration (shell|structure|environment|behavior)\b"),
    rule("ion-pairing and complexation", "solvation_entropy", "complexation", r"\bion[- ]pair(ing)?\b|\bcomplexation\b|\bcoordination (with|between)\b"),
    rule("host-guest complexation", "solvation_entropy", "supramolecular interaction", r"\bhost[- ]guest\b|\bcyclodextrin.*(confine|complex|cavit)"),
    rule("crown-ether cation complexation", "solvation_entropy", "supramolecular interaction", r"\bcrown ether.*(complex|cation)|\bcation.*crown ether\b"),
    rule("electrostatic interaction", "solvation_entropy", "intermolecular interaction", r"\belectrostatic interaction\b|\bCoulomb(ic)? interaction\b"),
    rule("hydrogen bonding", "solvation_entropy", "intermolecular interaction", r"\bhydrogen bond(ing|s)?\b"),
    rule("ion-dipole interaction", "solvation_entropy", "intermolecular interaction", r"\bion[- ]dipole interaction\b"),
    rule("hydrophobic association", "gel_microstructure", "intermolecular interaction", r"\bhydrophobic association\b"),
    rule("pi-pi stacking", "gel_microstructure", "intermolecular interaction", r"\bpi[- ]pi stacking\b|π[- ]π stacking"),
    rule("Hofmeister/chaotropic effect", "gel_microstructure", "specific-ion effect", r"\bHofmeister\b|\bchaotropic( effect|ity| ion| cation| salt)?"),
    rule("salting-out", "phase_or_species_transition", "phase/species transition", r"\bsalting[- ]out\b"),
    rule("ion-induced crystallization", "phase_or_species_transition", "phase/species transition", r"\bion[- ]induced crystallization\b|\bguanidinium[- ]induced .*crystallization\b|\bnucleates? .*crystallization\b"),
    rule("thermosensitive crystallization", "phase_or_species_transition", "phase/species transition", r"\bthermosensitive crystallization\b|\btemperature[- ]induced crystallization\b"),
    rule("precipitation and species redistribution", "phase_or_species_transition", "phase/species transition", r"\bprecipitation\b|\bspecies redistribution\b"),
    rule("volume phase transition", "phase_or_species_transition", "phase/species transition", r"\bvolume phase transition\b|\bvolume[- ]phase transition\b"),
    rule("solid-liquid phase transition", "phase_or_species_transition", "phase/species transition", r"\bsolid[- ]liquid phase transition\b"),
    rule("configurational-entropy modulation", "phase_or_species_transition", "entropy mechanism", r"\bconfigurational entropy\b"),
    rule("dynamic crosslinking", "gel_microstructure", "network structure", r"\bdynamic crosslink(ed|ing)?\b|\bdynamic network\b"),
    rule("double/interpenetrating network", "gel_microstructure", "network structure", r"\bdouble[- ]network\b|\binterpenetrating[- ]network\b"),
    rule("polymer-water interaction", "gel_microstructure", "polymer-solvent interaction", r"\bpolymer[- ]water interaction\b|\bwater state\b|\bbound water\b"),
    rule("oriented ion-transport channels", "gel_microstructure", "network structure", r"\boriented .*ion.*channel|\baligned nanochannel\b"),
    rule("ionic conduction", "transport_mechanism", "ionic transport", r"\bionic conduction\b|\bion conduction\b"),
    rule("ion redistribution", "transport_mechanism", "ionic transport", r"\bion redistribution\b|\bionic redistribution\b"),
    rule("ionic-electronic coupling", "transport_mechanism", "coupled transport", r"\bmixed ionic[- ]electronic\b|\bionic[- ]electronic coupling\b"),
    rule("moisture-driven ion transport", "transport_mechanism", "humidity response", r"\bmoisture[- ]gradient ion transport\b|\bhumidity[- ]driven ion transport\b|\bwater uptake.*ion transport\b"),
    # Interfaces and device-driving physical processes
    rule("interfacial charge transfer", "electrode_interface", "charge transfer", r"\bcharge[- ]transfer\b|\binterfacial .*electron transfer\b"),
    rule("redox-kinetics enhancement", "electrode_interface", "reaction kinetics", r"\bredox kinetics\b|\belectrode kinetics\b|\bexchange current density\b"),
    rule("charge-transfer resistance reduction", "electrode_interface", "interfacial resistance", r"\breduc(e|es|ing) charge[- ]transfer resistance\b|\blower charge[- ]transfer resistance\b"),
    rule("porous-electrode area enhancement", "electrode_interface", "electrode architecture", r"\bporous electrode\b|\breaction area\b|\bsurface area.*redox\b"),
    rule("photothermal conversion", "device_function", "thermal-gradient generation", r"\bphotothermal conversion\b|\bphotothermal heating\b"),
    rule("radiative cooling", "device_function", "thermal-gradient generation", r"\bradiative cooling\b|\bradiative[- ]cooling\b"),
    rule("evaporative cooling/concentration", "device_function", "thermal-gradient generation", r"\bevaporat(ion|ive).*cool|\bevaporation creates .*concentration gradient\b"),
    rule("thermogalvanic redox conversion", "device_mechanism", "thermoelectrochemical conversion", r"\bthermogalvanic (redox|conversion|voltage|current|power|effect)\b|\btemperature gradient drives .*redox\b"),
    rule("temperature-dependent electrode potential", "device_mechanism", "thermoelectrochemical conversion", r"\btemperature[- ]dependent (equilibrium )?potential\b|\belectrode thermogalvanic coefficient\b|\bdE/dT\b"),
    rule("thermally regenerative electrochemical cycle", "device_mechanism", "thermoelectrochemical conversion", r"\bthermally regenerative electrochemical\b|\bTREC\b"),
    rule("photothermal-thermoelectric coupling", "device_mechanism", "multimodal conversion", r"\bphotothermal[- ]thermoelectric\b|\bphoto[- ]thermal[- ]electric\b|\bphotothermal.*thermogalvanic\b"),
    rule("piezoresistive-thermoelectric coupling", "device_mechanism", "multimodal conversion", r"\bpiezoresistive\b|\bresistance gating\b|\bresistance[- ]gated\b"),
    rule("thermal-gradient heat-transfer control", "device_mechanism", "thermal management", r"\bheat transfer\b|\bthermal management\b|\bthermal resistance\b|\bthermally isolates\b"),
    rule("thermogalvanic corrosion", "device_mechanism", "electrochemical corrosion", r"\bthermogalvanic corrosion\b|\bcorrosion currents?\b|\belectrodissolution\b"),
    # Solid-state mechanisms
    rule("phonon scattering", "solid_state_mechanism", "thermal transport", r"\bphonon scattering\b|\bscatter(ing|s) .*phonon"),
    rule("lattice thermal-conductivity suppression", "solid_state_mechanism", "thermal transport", r"\b(reduc|suppress|lower).*lattice thermal conductivity\b|\bultralow lattice thermal conductivity\b"),
    rule("defect engineering", "solid_state_mechanism", "defect chemistry", r"\bdefect engineering\b|\bvacanc(y|ies) .*transport\b"),
    rule("band engineering", "solid_state_mechanism", "electronic structure", r"\bband engineering\b|\bband convergence\b|\bband alignment\b"),
    rule("carrier-concentration optimization", "solid_state_mechanism", "electronic transport", r"\bcarrier concentration\b|\bcarrier density\b"),
    rule("energy filtering", "solid_state_mechanism", "electronic transport", r"\benergy filtering\b"),
    rule("electron-phonon coupling", "solid_state_mechanism", "coupled transport", r"\belectron[- ]phonon coupling\b"),
    rule("mixed ionic-covalent bonding", "solid_state_mechanism", "chemical bonding", r"\bmixed ionic.?covalent\b|\bionic.?covalent bonding\b"),
    rule("interfacial thermal resistance", "solid_state_mechanism", "thermal transport", r"\binterfacial thermal resistance\b|\bKapitza resistance\b"),
    rule("anharmonic phonon transport", "solid_state_mechanism", "thermal transport", r"\banharmonic(ity| phonon)?\b|\bphonon anharmonicity\b"),
    rule("alloy/disorder phonon scattering", "solid_state_mechanism", "thermal transport", r"\balloy scattering\b|\bmass disorder\b|\bsite disorder\b"),
    rule("grain-boundary scattering", "solid_state_mechanism", "thermal transport", r"\bgrain[- ]boundary scattering\b|\bgrain boundaries.*phonon\b"),
    rule("rattling-mode phonon suppression", "solid_state_mechanism", "thermal transport", r"\brattling\b|\brattler\b"),
    rule("superionic transition", "solid_state_mechanism", "ionic transport", r"\bsuperionic (phase )?transition\b|\bsuperionic conductor\b"),
    rule("polaron hopping", "solid_state_mechanism", "electronic transport", r"\bpolaron(ic)? hopping\b|\bsmall[- ]polaron\b"),
    rule("charge-carrier mobility", "solid_state_mechanism", "electronic transport", r"\bcarrier mobility\b|\belectron mobility\b|\bhole mobility\b"),
    rule("electronic-structure modulation", "solid_state_mechanism", "electronic structure", r"\belectronic structure\b|\bdensity of states\b|\bband gap\b"),
    # Background methods and metrics, retained but excluded by default from prediction
    rule("density functional theory", "computational_method", "electronic-structure calculation", r"\bdensity functional theory\b|\bDFT\b"),
    rule("first-principles calculation", "computational_method", "electronic-structure calculation", r"\bfirst[- ]principles calculation\b"),
    rule("molecular dynamics", "computational_method", "atomistic simulation", r"\bmolecular dynamics\b"),
    rule("machine learning", "computational_method", "data-driven method", r"\bmachine learning\b"),
    rule("X-ray diffraction", "characterization_method", "structure characterization", r"\bX[- ]ray diffraction\b|\bXRD\b"),
    rule("scanning electron microscopy", "characterization_method", "microscopy", r"\bscanning electron microscopy\b|\bSEM\b"),
    rule("transmission electron microscopy", "characterization_method", "microscopy", r"\btransmission electron microscopy\b|\bTEM\b"),
    rule("X-ray photoelectron spectroscopy", "characterization_method", "spectroscopy", r"\bX[- ]ray photoelectron spectroscopy\b|\bXPS\b"),
    rule("Raman spectroscopy", "characterization_method", "spectroscopy", r"\bRaman spectroscopy\b"),
    rule("electrochemical impedance spectroscopy", "characterization_method", "electrochemical characterization", r"\belectrochemical impedance spectroscopy\b|\bEIS\b"),
    rule("Seebeck coefficient/thermopower", "property_metric", "thermoelectric metric", r"\bSeebeck coefficient\b|\bthermopower\b"),
    rule("ionic conductivity", "property_metric", "transport property", r"\bionic conductivity\b"),
    rule("electrical conductivity", "property_metric", "transport property", r"\belectrical conductivity\b"),
    rule("thermal conductivity", "property_metric", "transport property", r"\bthermal conductivity\b"),
    rule("power density", "property_metric", "device metric", r"\bpower density\b"),
    rule("power factor", "property_metric", "thermoelectric metric", r"\bpower factor\b"),
    rule("conversion efficiency", "property_metric", "device metric", r"\bconversion efficiency\b"),
]


OPEN_CANONICAL_PATTERNS = [
    (re.compile(r"^(soret effect|soret thermodiffusion|thermodiffusion soret|ion thermodiffusion)$"), "ionic thermodiffusion (Soret effect)"),
    (re.compile(r"^(redox entropy|redox entropy difference|reaction entropy)$"), "redox reaction entropy"),
    (re.compile(r"^solvation shell$"), "solvation-shell remodeling"),
    (re.compile(r"^(ion transport|ionic transport)$"), "ion transport"),
    (re.compile(r"^ion channels?$"), "ion channels"),
    (re.compile(r"^(phase transition|phase transitions)$"), "phase transition"),
    (re.compile(r"^(chaotropic ions|chaotropic salts)$"), "Hofmeister/chaotropic effect"),
    (re.compile(r"^charge transfer$"), "interfacial charge transfer"),
    (re.compile(r"^redox kinetics$"), "redox-kinetics enhancement"),
    (re.compile(r"^(x ray diffraction|powder x ray diffraction)$"), "X-ray diffraction"),
    (re.compile(r"^density functional theory$"), "density functional theory"),
]

VERB_FRAGMENT_RE = re.compile(
    r"\b(increase[sd]?|increasing|enhance[sd]?|enhancing|improve[sd]?|improving|"
    r"reduce[sd]?|reducing|enable[sd]?|enabling|create[sd]?|creating|generate[sd]?|"
    r"facilitate[sd]?|facilitating|produce[sd]?|producing|prevent[sd]?|prevents|"
    r"boost[sd]?|boosting|add[sd]?|adding|give[sd]?|giving|support[sd]?|supporting|"
    r"tune[sd]?|tuning|control[sd]?|controlling|drive[sd]?|driving)\b"
)

GENERIC_RE = re.compile(
    r"^(temperature|room temperature|high temperature|low temperature|temperature range|"
    r"temperature difference|temperature gradient|temperature gradients|energy conversion|"
    r"power generation|thermoelectric applications?|transport propert(y|ies)|thermal transport|"
    r"electronic transport|charge transport|thermoelectric transport|activation energy|"
    r"relative humidity|solid solution|high ionic|mobile ions|ionic bonding|ionic radius|ionic radii|"
    r"thermogalvanic effect|thermogalvanic cells?|ionic thermoelectric|ionic thermoelectrics)$"
)

GENERIC_CANONICAL_LABELS = {
    "redox couple",
    "redox reaction",
    "ion transport",
    "mass transport",
    "transport pathways",
    "transport phenomena",
    "cold electrode",
    "hot electrode",
    "electrode potential",
}

ONTOLOGY_ANCHORS = {
    "hydrogel",
    "ionogel",
    "ionic liquid",
    "perovskite",
    "chalcogenide",
    "material system",
}

GLOBAL_CANONICAL_PATTERNS = [
    (
        re.compile(
            r"^(soret thermodiffusion coupling|thermodiffusion effect|"
            r"soret-effect ion thermodiffusion|soret thermodiffusion)$",
            re.I,
        ),
        "ionic thermodiffusion (Soret effect)",
        "transport_mechanism",
        "thermodiffusion",
    ),
    (
        re.compile(r"^soret coefficients?$", re.I),
        "Soret coefficient",
        "property_metric",
        "transport property",
    ),
    (
        re.compile(r"^cation/anion thermodiffusion asymmetry$", re.I),
        "cation-anion thermodiffusion asymmetry",
        "transport_mechanism",
        "thermodiffusion",
    ),
    (
        re.compile(r"^soft mixed ionic-electronic coupling$", re.I),
        "ionic-electronic coupling",
        "transport_mechanism",
        "coupled transport",
    ),
    (
        re.compile(r"^ion selectivity$", re.I),
        "selective ion transport",
        "transport_mechanism",
        "ionic transport",
    ),
    (
        re.compile(r"^ion-dipole interaction transport$", re.I),
        "ion-dipole interaction",
        "solvation_entropy",
        "intermolecular interaction",
    ),
    (
        re.compile(r"^(ion-pair complexation control|ion-pairing and complexation)$", re.I),
        "ion-pairing and complexation",
        "solvation_entropy",
        "complexation",
    ),
    (
        re.compile(r"^(redox entropy tuning|redox entropy)$", re.I),
        "redox reaction entropy",
        "solvation_entropy",
        "redox thermodynamics",
    ),
    (
        re.compile(r"^eastman entropy$", re.I),
        "Eastman entropy of transfer",
        "solvation_entropy",
        "ionic thermodynamics",
    ),
    (
        re.compile(r"^electrostatic interactions$", re.I),
        "electrostatic interaction",
        "solvation_entropy",
        "intermolecular interaction",
    ),
    (
        re.compile(r"^selective solvation entropy engineering$", re.I),
        "selective solvation",
        "solvation_entropy",
        "solvation",
    ),
    (
        re.compile(r"^phase-transition entropy amplification$", re.I),
        "phase transition",
        "phase_or_species_transition",
        "phase/species transition",
    ),
    (
        re.compile(r"^(configurational entropy|configurational entropy gel design)$", re.I),
        "configurational-entropy modulation",
        "phase_or_species_transition",
        "entropy mechanism",
    ),
    (
        re.compile(r"^hydrogel volume-phase transition thermocell$", re.I),
        "volume phase transition",
        "phase_or_species_transition",
        "phase/species transition",
    ),
    (
        re.compile(r"^thermosensitive crystallization salting-out$", re.I),
        "thermosensitive crystallization",
        "phase_or_species_transition",
        "phase/species transition",
    ),
    (
        re.compile(r"^ferri/ferrocyanide thermogalvanic$", re.I),
        "ferri/ferrocyanide redox chemistry",
        "redox_chemistry",
        "redox mechanism",
    ),
    (
        re.compile(r"^iodide/triiodide redox$", re.I),
        "iodide/triiodide redox chemistry",
        "redox_chemistry",
        "redox mechanism",
    ),
]

MATERIAL_SIGNAL_RE = re.compile(
    r"hydrogel|ionogel|organohydrogel|eutogel|electrolyte|ionic liquid|deep eutectic|"
    r"polymer|pva|pam|paa|pedot|cellulose|chitosan|alginate|gelatin|gelma|mxene|"
    r"graphene|carbon|nanotube|mos2|bi2|sb2|snse|tellur|selen|sulfide|oxide|"
    r"perovskite|skutterudite|heusler|zintl|clathrate|chalcogenide|redox|"
    r"ferri|ferro|iodide|triiodide|quinone|viologen|tempo|electrode|membrane|"
    r"salt|guanid|urea|glycerol|ethylene glycol|dmso|solvent"
)


def canonicalize_global(
    canonical: str, concept_type: str, subtype: str
) -> tuple[str, str, str]:
    canonical = norm_space(canonical)
    for pattern, replacement, replacement_type, replacement_subtype in GLOBAL_CANONICAL_PATTERNS:
        if pattern.fullmatch(canonical):
            return replacement, replacement_type, replacement_subtype
    return canonical, concept_type, subtype


def canonicalize_open(label: str, concept_type: str) -> tuple[str, str]:
    clean = norm_space(label).lower().strip(" .;,")
    for pattern, canonical in OPEN_CANONICAL_PATTERNS:
        if pattern.fullmatch(clean):
            clean = canonical
            break
    if re.search(r"high[- ]entropy (chalcogenide|alloy|solid solution)", clean):
        concept_type = "material_system"
    if concept_type == "material_system" and re.search(r"\bthermal diffusion\b", clean):
        concept_type = "transport_mechanism"
        clean = "ionic thermodiffusion (Soret effect)"
    return clean, concept_type


def accept_open(label: str, concept_type: str) -> bool:
    clean = norm_space(label).lower()
    words = clean.split()
    if not clean or GENERIC_RE.fullmatch(clean):
        return False
    if VERB_FRAGMENT_RE.search(clean):
        return False
    if len(words) > 6:
        return False
    if concept_type == "material_system" and not MATERIAL_SIGNAL_RE.search(clean):
        return False
    if concept_type in {"transport_mechanism", "redox_chemistry", "solvation_entropy", "electrode_interface", "phase_or_species_transition", "gel_microstructure"}:
        return len(words) >= 2
    if concept_type in {"property_metric", "characterization_method", "computational_method"}:
        return True
    if concept_type == "device_function":
        return len(words) <= 5 and bool(re.search(r"thermogalvanic|thermal charging|refrigeration|photothermal|sensing|cooling|microfluidic", clean))
    return False


def infer_subtype(label: str, concept_type: str) -> str:
    label_lower = label.lower()
    for item in RULES:
        if item["label"].lower() == label_lower:
            return item["subtype"]
    defaults = {
        "material_entity": "specific material/entity",
        "material_system": "material/system",
        "redox_chemistry": "redox mechanism",
        "solvation_entropy": "solvation/entropy mechanism",
        "transport_mechanism": "transport mechanism",
        "electrode_interface": "interface/kinetics mechanism",
        "phase_or_species_transition": "phase/species transition",
        "gel_microstructure": "soft-material mechanism",
        "solid_state_mechanism": "solid-state mechanism",
        "device_mechanism": "device-scale conversion mechanism",
        "device_function": "device function",
        "property_metric": "property/metric",
        "characterization_method": "characterization method",
        "computational_method": "computational method",
    }
    return defaults.get(concept_type, concept_type)


def add_mapping(
    mapping_rows: list[dict],
    alias_rows: list[dict],
    paper_id: str,
    canonical: str,
    concept_type: str,
    subtype: str,
    evidence_field: str,
    evidence_text: str,
    extraction_method: str,
    confidence: float,
    original_label: str | None = None,
) -> None:
    canonical, concept_type, subtype = canonicalize_global(
        canonical, concept_type, subtype
    )
    canonical = norm_space(canonical)
    if canonical.lower() in GENERIC_CANONICAL_LABELS:
        return
    concept_id = stable_concept_id(canonical.lower())
    mapping_rows.append(
        {
            "paper_id": paper_id,
            "concept_id": concept_id,
            "canonical_concept": canonical,
            "concept_type": concept_type,
            "concept_subtype": subtype,
            "evidence_field": evidence_field,
            "evidence_text": norm_space(evidence_text)[:1000],
            "extraction_method": extraction_method,
            "confidence": round(float(confidence), 3),
        }
    )
    if original_label and norm_key(original_label) != norm_key(canonical):
        alias_rows.append(
            {
                "alias": norm_space(original_label),
                "concept_id": concept_id,
                "canonical_concept": canonical,
                "alias_source": extraction_method,
            }
        )


def extract_rule_concepts(papers: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    mappings: list[dict] = []
    aliases: list[dict] = []
    for paper in papers.itertuples(index=False):
        for item in RULES:
            matches = []
            for field in item["fields"]:
                text = getattr(paper, field)
                match = item["pattern"].search(text)
                if match:
                    matches.append((field, match.group(0)))
            if not matches:
                continue
            field, evidence = matches[0]
            add_mapping(
                mappings,
                aliases,
                paper.paper_id,
                item["label"],
                item["concept_type"],
                item["subtype"],
                field,
                evidence,
                "controlled_rule",
                item["confidence"],
                evidence,
            )
    return mappings, aliases


def extract_curated_concepts(
    papers: pd.DataFrame, legacy_to_paper: dict[str, str]
) -> tuple[list[dict], list[dict]]:
    mappings: list[dict] = []
    aliases: list[dict] = []
    by_paper = papers.set_index("paper_id")
    for legacy_id, paper_id in legacy_to_paper.items():
        paper = by_paper.loc[paper_id]
        row = type(
            "Paper",
            (),
            {
                "source": "TG" if legacy_id.startswith("TG_") else "iTE",
                "title": paper["title"],
                "abstract": paper["abstract"],
                "material": paper["material_raw"],
                "mechanism": paper["mechanism_raw"],
            },
        )
        for label, concept_type in curated.extract_phrases(row).items():
            add_mapping(
                mappings,
                aliases,
                paper_id,
                label,
                concept_type,
                infer_subtype(label, concept_type),
                "material+mechanism+abstract",
                f"{paper['material_raw']} | {paper['mechanism_raw']}",
                "domain_curated_rule",
                0.97,
            )
    return mappings, aliases


def import_clean_open_concepts(
    papers: pd.DataFrame, legacy_to_paper: dict[str, str]
) -> tuple[list[dict], list[dict]]:
    mappings: list[dict] = []
    aliases: list[dict] = []
    by_paper = papers.set_index("paper_id")
    open_pc = pd.read_csv(OPEN_DIR / "open_nmi_paper_concepts_1500.csv")
    for row in open_pc.itertuples(index=False):
        paper_id = legacy_to_paper.get(row.paper_id)
        if paper_id is None:
            continue
        canonical, concept_type = canonicalize_open(row.concept, row.concept_type)
        if not accept_open(canonical, concept_type):
            continue
        paper = by_paper.loc[paper_id]
        add_mapping(
            mappings,
            aliases,
            paper_id,
            canonical,
            concept_type,
            infer_subtype(canonical, concept_type),
            "abstract/material/mechanism",
            row.concept,
            "cleaned_open_concept",
            0.78,
            row.concept,
        )
    return mappings, aliases


FORMULA_RE = re.compile(
    r"(?<![A-Za-z])(?:\[[A-Z][A-Za-z0-9()]*\][0-9+\-/]*|"
    r"(?:[A-Z][a-z]?[0-9]*){2,}(?:\([A-Za-z0-9]+\)[0-9]*)*(?:[0-9+\-]+)?)(?![A-Za-z])"
)
FORMULA_BLOCKLIST = {
    "SMILES",
    "CNT",
    "CNF",
    "PVA",
    "PAM",
    "PAA",
    "PVP",
    "PEG",
    "PEDOT",
    "PSS",
    "MXENE",
    "DFT",
    "SEM",
    "TEM",
    "XRD",
    "XPS",
    "EIS",
    "NMR",
    "MEMS",
    "NIR",
}


def extract_formula_entities(papers: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    mappings: list[dict] = []
    aliases: list[dict] = []
    for paper in papers.itertuples(index=False):
        seen = set()
        for formula in FORMULA_RE.findall(paper.material_raw):
            formula = formula.strip(".,;:")
            if formula.upper() in FORMULA_BLOCKLIST or len(formula) < 3:
                continue
            if not re.search(r"\d", formula):
                continue
            normalized = formula.replace(" ", "")
            if normalized in seen:
                continue
            seen.add(normalized)
            add_mapping(
                mappings,
                aliases,
                paper.paper_id,
                normalized,
                "material_entity",
                "chemical formula",
                "material_raw",
                formula,
                "chemical_formula_parser",
                0.9,
                formula,
            )
    return mappings, aliases


def collapse_duplicate_mappings(mapping_rows: list[dict]) -> pd.DataFrame:
    mapping = pd.DataFrame(mapping_rows)
    if mapping.empty:
        return mapping
    method_rank = {
        "domain_curated_rule": 4,
        "controlled_rule": 3,
        "chemical_formula_parser": 2,
        "cleaned_open_concept": 1,
    }
    mapping["method_rank"] = mapping["extraction_method"].map(method_rank).fillna(0)
    mapping = mapping.sort_values(
        ["paper_id", "concept_id", "confidence", "method_rank"],
        ascending=[True, True, False, False],
    )
    mapping = mapping.drop_duplicates(["paper_id", "concept_id"], keep="first")
    # Open n-gram singletons are usually sentence fragments. Keep a singleton only
    # when a controlled, curated or chemical parser independently supports it.
    support = mapping.groupby("concept_id").agg(
        document_frequency=("paper_id", "nunique"),
        strongest_method=("method_rank", "max"),
    )
    weak_singletons = support[
        (support["document_frequency"] == 1) & (support["strongest_method"] <= 1)
    ].index
    mapping = mapping[~mapping["concept_id"].isin(weak_singletons)]
    return mapping.drop(columns="method_rank").reset_index(drop=True)


def build_vocabulary(mapping: pd.DataFrame, papers: pd.DataFrame) -> pd.DataFrame:
    enriched = mapping.merge(
        papers[["paper_id", "source_membership", "year"]], on="paper_id", how="left"
    )
    rows = []
    for concept_id, group in enriched.groupby("concept_id", sort=False):
        best = group.sort_values("confidence", ascending=False).iloc[0]
        ite_mask = group["source_membership"].str.contains("iTE", na=False)
        tg_mask = group["source_membership"].str.contains("TG", na=False)
        doc_freq = group["paper_id"].nunique()
        core = best["concept_type"] in CORE_TYPES
        prediction_eligible = (
            core
            and doc_freq >= 2
            and group["confidence"].max() >= 0.78
            and best["canonical_concept"].lower() not in ONTOLOGY_ANCHORS
        )
        if prediction_eligible and best["canonical_concept"].lower() not in ONTOLOGY_ANCHORS:
            graph_role = "prediction_core"
        elif core:
            graph_role = (
                "ontology_anchor"
                if best["canonical_concept"].lower() in ONTOLOGY_ANCHORS
                else "rare_core_evidence"
            )
        else:
            graph_role = "background"
        rows.append(
            {
                "concept_id": concept_id,
                "canonical_concept": best["canonical_concept"],
                "concept_type": best["concept_type"],
                "concept_subtype": best["concept_subtype"],
                "parent_domain": TYPE_PARENT.get(best["concept_type"], "other"),
                "graph_role": graph_role,
                "document_frequency": doc_freq,
                "iTE_document_frequency": group.loc[ite_mask, "paper_id"].nunique(),
                "TG_document_frequency": group.loc[tg_mask, "paper_id"].nunique(),
                "first_year": int(group["year"].dropna().min()) if group["year"].notna().any() else None,
                "last_year": int(group["year"].dropna().max()) if group["year"].notna().any() else None,
                "max_confidence": round(float(group["confidence"].max()), 3),
                "prediction_eligible": prediction_eligible,
                "evidence_only": bool(core and doc_freq == 1),
            }
        )
    vocab = pd.DataFrame(rows)
    return vocab.sort_values(
        ["graph_role", "document_frequency", "canonical_concept"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def build_alias_map(alias_rows: list[dict], vocab: pd.DataFrame) -> pd.DataFrame:
    aliases = pd.DataFrame(alias_rows)
    canonical_aliases = vocab[
        ["concept_id", "canonical_concept"]
    ].copy()
    canonical_aliases["alias"] = canonical_aliases["canonical_concept"]
    canonical_aliases["alias_source"] = "canonical"
    aliases = pd.concat([aliases, canonical_aliases], ignore_index=True)
    aliases["alias_key"] = aliases["alias"].map(norm_key)
    aliases = aliases.sort_values(
        ["concept_id", "alias_source", "alias"], ascending=[True, True, True]
    ).drop_duplicates(["alias_key", "concept_id"])
    return aliases.drop(columns="alias_key").reset_index(drop=True)


def build_merge_review(vocab: pd.DataFrame) -> pd.DataFrame:
    eligible = vocab[
        (vocab["graph_role"] == "prediction_core")
        & (vocab["document_frequency"] >= 2)
    ].copy()
    if len(eligible) < 2:
        return pd.DataFrame()
    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        local_files_only=True,
    )
    embeddings = model.encode(
        eligible["canonical_concept"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    similarity = embeddings @ embeddings.T
    rows = []
    for i in range(len(eligible)):
        neighbors = np.argsort(-similarity[i])
        added = 0
        for j in neighbors:
            if i == j or j < i:
                continue
            score = float(similarity[i, j])
            if score < 0.84:
                break
            left = eligible.iloc[i]
            right = eligible.iloc[j]
            rows.append(
                {
                    "concept_a_id": left["concept_id"],
                    "concept_a": left["canonical_concept"],
                    "concept_a_type": left["concept_type"],
                    "concept_b_id": right["concept_id"],
                    "concept_b": right["canonical_concept"],
                    "concept_b_type": right["concept_type"],
                    "embedding_similarity": round(score, 4),
                    "recommended_action": "review; do not auto-merge",
                }
            )
            added += 1
            if added >= 3:
                break
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        "embedding_similarity", ascending=False
    ).reset_index(drop=True)


def build_qc(
    papers: pd.DataFrame, mapping: pd.DataFrame, vocab: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    paper_counts = (
        mapping.assign(
            is_core=mapping["concept_type"].isin(CORE_TYPES),
            is_material=mapping["concept_type"].isin({"material_entity", "material_system"}),
            is_mechanism=mapping["concept_type"].isin(CORE_TYPES - {"material_entity", "material_system"}),
        )
        .groupby("paper_id")
        .agg(
            total_concepts=("concept_id", "nunique"),
            core_concepts=("is_core", "sum"),
            material_concepts=("is_material", "sum"),
            mechanism_concepts=("is_mechanism", "sum"),
        )
        .reset_index()
    )
    coverage = papers.merge(paper_counts, on="paper_id", how="left").fillna(
        {
            "total_concepts": 0,
            "core_concepts": 0,
            "material_concepts": 0,
            "mechanism_concepts": 0,
        }
    )
    coverage["has_material"] = coverage["material_concepts"] > 0
    coverage["has_mechanism"] = coverage["mechanism_concepts"] > 0
    coverage["prediction_ready"] = (
        coverage["has_material"] & coverage["has_mechanism"]
    )
    coverage["qc_flag"] = np.select(
        [
            ~coverage["has_material"] & ~coverage["has_mechanism"],
            ~coverage["has_material"],
            ~coverage["has_mechanism"],
        ],
        ["missing material and mechanism", "missing material", "missing mechanism"],
        default="pass",
    )

    unique_rows = [
        ("input source rows", 2044, "before DOI/title deduplication"),
        ("unique papers", len(papers), "after DOI/title deduplication"),
        ("paper-concept links", len(mapping), "deduplicated links"),
        ("all canonical concepts", len(vocab), "core + background"),
        ("prediction-core concepts", int((vocab["graph_role"] == "prediction_core").sum()), "reusable materials and mechanisms"),
        ("ontology anchor concepts", int((vocab["graph_role"] == "ontology_anchor").sum()), "broad parents retained for navigation, excluded from prediction"),
        ("rare core evidence concepts", int((vocab["graph_role"] == "rare_core_evidence").sum()), "real but currently single-paper materials/mechanisms"),
        ("background concepts", int((vocab["graph_role"] == "background").sum()), "methods, metrics and device functions"),
        ("prediction-eligible concepts", int(vocab["prediction_eligible"].sum()), "core concepts with document frequency >= 2"),
        ("singleton evidence concepts", int(vocab["evidence_only"].sum()), "retained for evidence, excluded from prediction"),
        ("papers with material concepts", int(coverage["has_material"].sum()), "unique papers"),
        ("papers with mechanism concepts", int(coverage["has_mechanism"].sum()), "unique papers"),
        ("prediction-ready papers", int(coverage["prediction_ready"].sum()), "contains both material and mechanism"),
        ("median concepts per paper", float(coverage["total_concepts"].median()), "all concept roles"),
        ("median core concepts per paper", float(coverage["core_concepts"].median()), "materials and mechanisms"),
    ]
    summary = pd.DataFrame(unique_rows, columns=["metric", "value", "definition"])
    return summary, coverage


def build_surface_evidence(papers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for paper in papers.itertuples(index=False):
        rows.extend(
            [
                {
                    "paper_id": paper.paper_id,
                    "evidence_type": "material formulation",
                    "raw_evidence": paper.material_raw,
                    "use_in_embedding_map": True,
                    "use_as_graph_node": False,
                },
                {
                    "paper_id": paper.paper_id,
                    "evidence_type": "mechanism statement",
                    "raw_evidence": paper.mechanism_raw,
                    "use_in_embedding_map": True,
                    "use_as_graph_node": False,
                },
            ]
        )
    return pd.DataFrame(rows)


def main() -> None:
    papers, legacy_to_paper = read_sources()
    mapping_rows: list[dict] = []
    alias_rows: list[dict] = []

    for extractor in [
        lambda: extract_rule_concepts(papers),
        lambda: extract_curated_concepts(papers, legacy_to_paper),
        lambda: import_clean_open_concepts(papers, legacy_to_paper),
        lambda: extract_formula_entities(papers),
    ]:
        new_mapping, new_aliases = extractor()
        mapping_rows.extend(new_mapping)
        alias_rows.extend(new_aliases)

    mapping = collapse_duplicate_mappings(mapping_rows)
    vocabulary = build_vocabulary(mapping, papers)
    aliases = build_alias_map(alias_rows, vocabulary)
    merge_review = build_merge_review(vocabulary)
    qc_summary, paper_qc = build_qc(papers, mapping, vocabulary)
    surface_evidence = build_surface_evidence(papers)

    vocabulary.to_csv(OUT / "final_concept_vocabulary.csv", index=False)
    mapping.to_csv(OUT / "final_paper_concept_map.csv", index=False)
    aliases.to_csv(OUT / "final_concept_alias_map.csv", index=False)
    papers.to_csv(OUT / "final_paper_index.csv", index=False)
    paper_qc.to_csv(OUT / "final_paper_qc.csv", index=False)
    surface_evidence.to_csv(OUT / "final_surface_evidence.csv", index=False)
    merge_review.to_csv(OUT / "final_embedding_merge_review.csv", index=False)
    qc_summary.to_csv(OUT / "final_qc_summary.csv", index=False)

    summary = {
        row.metric: row.value for row in qc_summary.itertuples(index=False)
    }
    summary["concepts_by_type"] = (
        vocabulary.groupby("concept_type").size().sort_values(ascending=False).to_dict()
    )
    summary["links_by_type"] = (
        mapping.groupby("concept_type").size().sort_values(ascending=False).to_dict()
    )
    (OUT / "final_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
