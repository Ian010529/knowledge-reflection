"""Build a clean-room iTE/TG concept and pair layer from original abstracts only.

This pipeline intentionally does not import any prior concept map, mechanism card,
transfer lever, complementarity program, preferred paper, or curated bridge.  Every
concept occurrence is an extractive span from one abstract.  Normalization is
limited to case, punctuation/hyphen, Greek transliteration, and simple plurals.
Explicit relations require a visible predicate in the same sentence.  Same-
sentence co-occurrence pairs are stored separately and never called causal.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha1, sha256
from itertools import combinations
import json
import math
from pathlib import Path
import re

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "source_tables"
OUT = ROOT / "cleanroom_abstract_pair_layer"


def json_default(value: object) -> object:
    """Convert NumPy/Pandas scalar values without weakening QA assertions."""
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

SOURCES = [
    ("TG_first333_material_mechanism.csv", "TG"),
    ("iTE1_first1000_material_mechanism.csv", "iTE1"),
    ("iTE2_first711_material_mechanism.csv", "iTE2"),
]
SOURCE_COLUMNS = ["文章名", "期刊名", "DOI", "年份", "摘要"]

TG_CUE = re.compile(
    r"\bthermogalvanic\b|\bthermo[- ]?electrochemical\b|\bthermocells?\b|"
    r"\bthermo[- ]?electrochemistry\b",
    re.I,
)
TG_CORE_CUE = re.compile(
    # The returned match must itself be the TG evidence.  Do not use a reverse
    # look-ahead whose reported span is merely "heat", "power", or "redox".
    r"\bthermogalvanic(?:\s*\([^)]{1,12}\))?\s+"
    r"(?:cells?|devices?|generators?|hydrogels?|electrolytes?|redox)\b|"
    r"\bthermogalvanic effect\b",
    re.I,
)
TG_AMBIGUOUS_DEVICE_CUE = re.compile(
    r"\bthermocells?\b|\bthermo[- ]?electrochemical cells?\b",
    re.I,
)
TG_EXCLUSION_CUE = re.compile(
    r"\bthermogalvanic corrosion\b|\bthermogalvanic profil(?:e|es|ing)\b|"
    r"\bmagneto[- ]?thermogalvanic\b|\bspin[- ]dependent\b|"
    r"\bmagnetic nanostructures?\b|\bheat exchangers?\b|"
    # Separate temperature-cycling/storage technologies are held out instead of
    # being silently relabelled as temperature-difference TG devices.
    r"\bthermally regenerative electrochemical cycles?\b|\bTREC(?:-FB)?\b|"
    r"\bthermally regenerative electrochemically cycled flow batter(?:y|ies)\b|"
    r"\bthermocapacitors?\b|\bdirect thermal charging cells?\b|"
    r"\btraditional thermogalvanic cells?\b|"
    r"\brather than fixed thermal gradients?\b|"
    r"\bwithout a spatial temperature gradient\b|"
    r"\bfaradaic and EDL contributions\b|"
    r"\bin this (?:review|perspective)\b|"
    r"\bcharged at (?:a|one) temperature\b(?=.{0,180}\bdischarged at "
    r"(?:a )?different temperature\b)|"
    r"\bthermostimulated depolarization\b|"
    r"\b(?:is|are|were) reviewed and compared\b|"
    # In these abstracts the TG cell is explicitly a measurement instrument for
    # diffusion/solvation quantities, not the target conversion mechanism.
    r"\bsymmetr(?:ic|ical) thermogalvanic (?:cells?|elements?)\b|"
    r"\b(?:initial|stationary|steady[- ]state) temperature (?:voltage )?"
    r"coefficients?\b(?=.{0,220}\bthermogalvanic\b)|"
    r"\bthermogalvanic cells?\b(?=.{0,260}\b(?:results (?:are|were) used to determine|"
    r"used to determine (?:standard )?entrop|soret coefficients?)\b)|"
    r"\b(?:peltier heats?|reaction entropy)\b(?=.{0,220}\bmeasured "
    r"(?:through|using|by)\b.{0,100}\bthermogalvanic cells?\b)|"
    r"\babsolute standard partial molar entropy\b",
    re.I,
)
TG_MENTION_ONLY_CUE = re.compile(
    r"\btraditional routes?\b(?=.{0,220}\bthermogalvanic cells?\b)|"
    r"\bapplications?\s*,?\s*(?:including|such as|e\.g\.)"
    r"[^.!?]{0,260}\bthermogalvanic cells?\b|"
    r"\bdevices?\s*,?\s*(?:including|such as)"
    r"[^.!?]{0,180}\bthermogalvanic cells?\b",
    re.I,
)
ITE_STRONG_CUE = re.compile(
    r"\bionic thermoelectric\b(?!\s+field)|\bionic thermopower\b|\bionic seebeck\b|"
    r"\bion[- ]?thermoelectric\b",
    re.I,
)
ITE_WEAK_CUE = re.compile(
    r"\bion(?:ic)? thermodiffusion\b|\bthermodiffusion\b|\bthermal diffusion\b|"
    r"\bsoret(?: effect)?\b|"
    r"\bthermo[- ]?diffusion of (?:ions|cations|anions)\b",
    re.I,
)
ITE_LIQUID_ION_CONTEXT = re.compile(
    r"\b(?:ion|ions|ionic|cation|cations|anion|anions|proton|protons|"
    r"electrolyte|electrolytes)\b"
    r"(?=.{0,220}\b(?:solution|solutions|liquid|liquids|aqueous|hydrogels?|"
    r"ionogels?|gels?|electrolyte|electrolytes|seebeck|thermovoltage|thermoelectric field|"
    r"thermoelectric response)\b)|"
    r"\b(?:solution|solutions|liquid|liquids|aqueous|hydrogels?|ionogels?|gels?|"
    r"electrolyte|electrolytes)\b(?=.{0,220}\b(?:ion|ions|ionic|cation|cations|"
    r"anion|anions|proton|protons|seebeck|thermovoltage|thermoelectric field|"
    r"thermoelectric response)\b)",
    re.I,
)
ITE_SOFT_MEDIUM_CUE = re.compile(
    r"\b(?:solutions?|liquids?|aqueous|hydrogels?|ionogels?|eutogels?|gels?|"
    r"gelled|electrolytes?|polyelectrolytes?|polymer complexes?)\b",
    re.I,
)
ITE_MOBILE_ION_CUE = re.compile(
    r"\b(?:ions?|ionic|cations?|anions?|protons?|electrolytes?|electrolytic)\b",
    re.I,
)
ITE_ADJACENT_EXCLUSION_CUE = re.compile(
    r"\b(?:colloid|colloids|colloidal|nanoparticle|nanoparticles|ferrofluid|"
    r"liquid metal alloy|liquid metal alloys|(?<!quasi-)(?<!quasi )solid[- ]state|"
    r"nonstoichiometric oxide|magnetic nanostructure|magnetic nanostructures|"
    r"mixed electronic[- ]ionic conductor|mixed ionic[- ]electronic conductor|"
    r"mobile oxide ions?)\b",
    re.I,
)
ITE_MENTION_ONLY_CUE = re.compile(
    r"\bapplications?\s*,?\s*(?:including|such as)\b"
    r"(?=.{0,220}\bionic (?:thermoelectric|TE)\b)|"
    r"\b(?:could|may|might)\b[^.!?]{0,140}\bionic thermoelectric materials?\b",
    re.I,
)
FARADAIC_CUE = re.compile(
    r"\bfaradai(?:c|ically)\b|(?<!non-)(?<!non )\bredox\b|"
    r"\bredox (?:ion|ions|pair|pairs|couple|couples|"
    r"reaction|reactions|solution|solutions|species|chemistry|effect)\b|"
    r"\bferri(?:cyanide)?\b|\bferrocyanide\b|"
    r"(?:K3|K4|Fe)\s*\[?Fe\s*\(\s*CN\s*\)\s*6\]?|"
    r"\[?\s*Fe\s*\(\s*CN\s*\)\s*6\s*\]?\s*[34]\s*-|"
    r"\bFe\s*\(\s*ClO4\s*\)\s*\(?\s*2\s*/\s*3\s*\)?|"
    r"\bFe\s*2\s*\+\s*/\s*(?:Fe\s*)?3\s*\+|"
    r"\bFeCN\s*4\s*-\s*/\s*3\s*-|"
    r"\[?\s*Fe\s*\(\s*CN\s*\)\s*\(?\s*6\s*\)?\s*\]?\s*"
    r"\(\s*3\s*-\s*/\s*4\s*-\s*\)|"
    r"\bCu\s*/\s*Cu\s*(?:2\s*\+|\+\s*2)|"
    r"\bCu\s*/\s*CuSO4\b|\bthermogalvanic reaction\b|"
    r"\belectrochemical reactions?\b|\belectroactive interfaces?\b|"
    r"\bthermogalvanic kinetics\b|"
    r"\b(?:oxidation|reduction|corrosion) (?:reaction|process)\b|"
    r"\bhydrogen\b(?=.{0,100}\b(?:consumed|regenerated)\b)|"
    r"\bproton[- ]coupled electron transfer\b|\bPCET\b",
    re.I,
)
COUPLED_CUE = re.compile(
    r"\bredox (?:ion|ions|pair|pairs|reaction|reactions|electrode|electrodes|"
    r"couple|couples|solution|solutions|species|chemistry|effect)\b|"
    r"\belectrode[- ]interface redox\b|\bthermogalvanic\b|"
    r"\bfaradai(?:c|ically)\b|(?<!non-)(?<!non )\bredox\b|"
    r"(?:K3|K4|Fe)\s*\[?Fe\s*\(\s*CN\s*\)\s*6\]?|"
    r"\[?\s*Fe\s*\(\s*CN\s*\)\s*6\s*\]?\s*[34]\s*-|"
    r"\bFe\s*\(\s*ClO4\s*\)\s*\(?\s*2\s*/\s*3\s*\)?|"
    r"\bFe\s*2\s*\+\s*/\s*(?:Fe\s*)?3\s*\+|"
    r"\bFeCN\s*4\s*-\s*/\s*3\s*-|"
    r"\bCu\s*/\s*Cu\s*(?:2\s*\+|\+\s*2)|"
    r"\bproton[- ]coupled electron transfer\b|\bPCET\b|"
    r"\bhybrid mechanisms?\b|\bsimultaneous energy conversion and storage\b|"
    r"\bfunctional electrodes?\b|\bgraphite electrodes?\b",
    re.I,
)
COUPLED_STRONG_CUE = re.compile(
    r"\bhybrid mechanisms?\b|\bsimultaneous energy conversion and storage\b|"
    r"\bthermal charging cells?\b|"
    r"\b(?:zinc|lithium|magnesium)[- ]ion batter(?:y|ies)\b|"
    r"\bgalvanostatic charge[- ]?discharge\b|\bspecific capacitance\b|"
    r"\belectrodepositing\b",
    re.I,
)
SOLID_TE_CUE = re.compile(r"\bthermoelectric\b|\bseebeck\b|\bthermopower\b", re.I)

STOP = set(ENGLISH_STOP_WORDS) | {
    "study",
    "work",
    "report",
    "reports",
    "reported",
    "result",
    "results",
    "using",
    "used",
    "based",
    "novel",
    "new",
    "high",
    "higher",
    "highest",
    "low",
    "lower",
    "significant",
    "significantly",
    "potential",
    "application",
    "applications",
    "performance",
    "approach",
    "method",
    "methods",
    "system",
    "systems",
    "material",
    "materials",
    "device",
    "devices",
    "sample",
    "samples",
    "herein",
    "accordingly",
    "furthermore",
    "however",
    "moreover",
    "thus",
    "including",
    "include",
    "includes",
    "achieved",
    "achieves",
    "show",
    "shows",
    "shown",
    "demonstrated",
    "demonstrates",
    "provide",
    "provides",
    "present",
    "presents",
    "developed",
    "fabricated",
    "optimized",
    "impressive",
    "strong",
    "substantial",
    "efficient",
    "enhanced",
    "advanced",
}

CONNECTORS = {
    "of",
    "and",
    "or",
    "for",
    "between",
    "within",
    "through",
    "by",
    "with",
    "to",
    "in",
    "on",
    "from",
    "under",
    "via",
    "into",
    "as",
}

BOUNDARY_WORDS = STOP | CONNECTORS | {
    "increase",
    "increases",
    "increased",
    "improve",
    "improves",
    "improved",
    "enhance",
    "enhances",
    "boost",
    "boosts",
    "facilitate",
    "facilitates",
    "yield",
    "yields",
    "lead",
    "leads",
    "leading",
    "attracting",
    "offer",
    "offers",
    "highlight",
    "highlights",
    "highlighting",
    "reveal",
    "reveals",
    "enable",
    "enables",
    "tailoring",
    "controlling",
    "control",
    "controls",
    "affect",
    "affects",
    "introduces",
    "incorporating",
    "exhibits",
    "exhibit",
    "confine",
    "confines",
    "enhance",
    "enhances",
    "reduce",
    "reduces",
    "decrease",
    "decreases",
    "suppress",
    "suppresses",
    "promote",
    "promotes",
    "enable",
    "enables",
    "cause",
    "causes",
    "drive",
    "drives",
    "regulate",
    "regulates",
    "induce",
    "induces",
    "create",
    "creates",
    "form",
    "forms",
    "generate",
    "generates",
    "produce",
    "produces",
    "limit",
    "limits",
    "immobilize",
    "immobilizes",
    "decouple",
    "decouples",
    "shift",
    "shifts",
    "modulate",
    "modulates",
    "rearrange",
    "rearranges",
    "establish",
    "establishes",
    "realize",
    "realizes",
    "frustrate",
    "frustrates",
}

HEAD_CATEGORY = {
    # Materials, chemical species, and physical structures.
    "alloy": "material_or_structure",
    "alloys": "material_or_structure",
    "hydrogel": "material_or_structure",
    "hydrogels": "material_or_structure",
    "ionogel": "material_or_structure",
    "ionogels": "material_or_structure",
    "eutogel": "material_or_structure",
    "eutogels": "material_or_structure",
    "gel": "material_or_structure",
    "gels": "material_or_structure",
    "electrolyte": "material_or_structure",
    "electrolytes": "material_or_structure",
    "polymer": "material_or_structure",
    "polymers": "material_or_structure",
    "membrane": "material_or_structure",
    "membranes": "material_or_structure",
    "nanoparticle": "material_or_structure",
    "nanoparticles": "material_or_structure",
    "nanostructure": "material_or_structure",
    "nanostructures": "material_or_structure",
    "film": "material_or_structure",
    "films": "material_or_structure",
    "coating": "material_or_structure",
    "coatings": "material_or_structure",
    "electrode": "material_or_structure",
    "electrodes": "material_or_structure",
    "solvent": "material_or_structure",
    "solvents": "material_or_structure",
    "salt": "material_or_structure",
    "salts": "material_or_structure",
    "composite": "material_or_structure",
    "composites": "material_or_structure",
    "oxide": "material_or_structure",
    "oxides": "material_or_structure",
    "sulfide": "material_or_structure",
    "sulfides": "material_or_structure",
    "selenide": "material_or_structure",
    "selenides": "material_or_structure",
    "telluride": "material_or_structure",
    "tellurides": "material_or_structure",
    "clathrate": "material_or_structure",
    "clathrates": "material_or_structure",
    "perovskite": "material_or_structure",
    "perovskites": "material_or_structure",
    "scaffold": "material_or_structure",
    "scaffolds": "material_or_structure",
    "network": "material_or_structure",
    "networks": "material_or_structure",
    "channel": "material_or_structure",
    "channels": "material_or_structure",
    "cavity": "material_or_structure",
    "cavities": "material_or_structure",
    "pore": "material_or_structure",
    "pores": "material_or_structure",
    "ion": "material_or_structure",
    "ions": "material_or_structure",
    "anion": "material_or_structure",
    "anions": "material_or_structure",
    "cation": "material_or_structure",
    "cations": "material_or_structure",
    "pair": "material_or_structure",
    "pairs": "material_or_structure",
    # Mechanisms and processes. The label is always the literal local phrase.
    "complexation": "mechanism_or_process",
    "interaction": "mechanism_or_process",
    "interactions": "mechanism_or_process",
    "confinement": "mechanism_or_process",
    "diffusion": "mechanism_or_process",
    "thermodiffusion": "mechanism_or_process",
    "migration": "mechanism_or_process",
    "transport": "mechanism_or_process",
    "mobility": "mechanism_or_process",
    "difference": "mechanism_or_process",
    "gradient": "mechanism_or_process",
    "gradients": "mechanism_or_process",
    "regulation": "mechanism_or_process",
    "cooling": "mechanism_or_process",
    "heating": "mechanism_or_process",
    "swelling": "mechanism_or_process",
    "crystallization": "mechanism_or_process",
    "solvation": "mechanism_or_process",
    "hydration": "mechanism_or_process",
    "association": "mechanism_or_process",
    "condensation": "mechanism_or_process",
    "micellization": "mechanism_or_process",
    "transition": "mechanism_or_process",
    "redistribution": "mechanism_or_process",
    "conversion": "mechanism_or_process",
    "kinetics": "mechanism_or_process",
    "reaction": "mechanism_or_process",
    "reactions": "mechanism_or_process",
    "transfer": "mechanism_or_process",
    "anchoring": "mechanism_or_process",
    "crosslinking": "mechanism_or_process",
    "coupling": "mechanism_or_process",
    "separation": "mechanism_or_process",
    "adsorption": "mechanism_or_process",
    "desorption": "mechanism_or_process",
    "doping": "mechanism_or_process",
    "scattering": "mechanism_or_process",
    "entropy": "mechanism_or_process",
    # Outcomes and measurements.
    "thermopower": "outcome_or_property",
    "coefficient": "outcome_or_property",
    "conductivity": "outcome_or_property",
    "resistivity": "outcome_or_property",
    "power": "outcome_or_property",
    "density": "outcome_or_property",
    "efficiency": "outcome_or_property",
    "stability": "outcome_or_property",
    "strength": "outcome_or_property",
    "modulus": "outcome_or_property",
    "bandgap": "outcome_or_property",
    "capacity": "outcome_or_property",
    "voltage": "outcome_or_property",
    "thermovoltage": "outcome_or_property",
    "current": "outcome_or_property",
    "factor": "outcome_or_property",
    "property": "outcome_or_property",
    "properties": "outcome_or_property",
    "rate": "outcome_or_property",
    "rates": "outcome_or_property",
    # Methods.
    "spectroscopy": "evidence_method",
    "microscopy": "evidence_method",
    "diffraction": "evidence_method",
    "simulation": "evidence_method",
    "simulations": "evidence_method",
    "calorimetry": "evidence_method",
    "voltammetry": "evidence_method",
    # Device/context nouns remain background and never drive ranking.
    "cell": "device_or_context",
    "cells": "device_or_context",
    "capacitor": "device_or_context",
    "capacitors": "device_or_context",
    "sensor": "device_or_context",
    "sensors": "device_or_context",
    "generator": "device_or_context",
    "generators": "device_or_context",
    "refrigeration": "device_or_context",
}

SINGLETON_ALLOWED = {
    "hydrogel",
    "ionogel",
    "eutogel",
    "thermodiffusion",
    "thermopower",
    "complexation",
    "micellization",
    "entropy",
    "conductivity",
    "resistivity",
    "confinement",
    "diffusion",
    "migration",
    "transport",
    "mobility",
    "gradient",
    "crystallization",
    "solvation",
    "hydration",
    "association",
    "condensation",
    "transition",
    "redistribution",
    "conversion",
    "kinetics",
    "reaction",
    "coupling",
    "interaction",
    "regulation",
    "cooling",
    "heating",
    "swelling",
}

PLURAL_NORMALIZATION = {
    "ions": "ion",
    "cells": "cell",
    "hydrogels": "hydrogel",
    "gels": "gel",
    "polymers": "polymer",
    "electrodes": "electrode",
    "electrolytes": "electrolyte",
    "capacitors": "capacitor",
    "materials": "material",
    "channels": "channel",
    "cavities": "cavity",
    "gradients": "gradient",
    "nanoparticles": "nanoparticle",
    "nanostructures": "nanostructure",
    "crystals": "crystal",
    "films": "film",
    "coatings": "coating",
    "mechanisms": "mechanism",
    "interactions": "interaction",
    "properties": "property",
    "rates": "rate",
    "molecules": "molecule",
    "solvents": "solvent",
    "salts": "salt",
    "networks": "network",
    "micelles": "micelle",
    "anions": "anion",
    "cations": "cation",
    "temperatures": "temperature",
    "pairs": "pair",
    "reactions": "reaction",
    "membranes": "membrane",
    "composites": "composite",
    "alloys": "alloy",
    "pores": "pore",
    "sensors": "sensor",
    "generators": "generator",
}

TOKEN_RE = re.compile(
    r"[A-Za-zα-ωΑ-Ω][A-Za-z0-9α-ωΑ-Ω+]*(?:[-/:][A-Za-z0-9α-ωΑ-Ω+]+)*[+\-]*"
)
SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
UNIT_RE = re.compile(
    r"^(?:mv|mw|kw|ev|cm|mm|nm|um|kg|mol|wt|vol|k|m|s|h|hz|pa|mpa|gpa|j|w)(?:-?\d+)?$",
    re.I,
)

PREDICATES = [
    (r"leads? to", "lead_to"),
    (r"results? in", "result_in"),
    (r"gives? rise to", "give_rise_to"),
    (r"is responsible for", "responsible_for"),
    (r"are responsible for", "responsible_for"),
    (r"confines?", "confine"),
    (r"enhances?", "enhance"),
    (r"increases?", "increase"),
    (r"boosts?", "boost"),
    (r"improves?", "improve"),
    (r"reduces?", "reduce"),
    (r"decreases?", "decrease"),
    (r"suppresses?", "suppress"),
    (r"promotes?", "promote"),
    (r"enables?", "enable"),
    (r"causes?", "cause"),
    (r"drives?", "drive"),
    (r"regulates?", "regulate"),
    (r"controls?", "control"),
    (r"facilitates?", "facilitate"),
    (r"induces?", "induce"),
    (r"creates?", "create"),
    (r"forms?", "form"),
    (r"generates?", "generate"),
    (r"produces?", "produce"),
    (r"limits?", "limit"),
    (r"immobilizes?", "immobilize"),
    (r"decouples?", "decouple"),
    (r"shifts?", "shift"),
    (r"modulates?", "modulate"),
    (r"affects?", "affect"),
    (r"rearranges?", "rearrange"),
    (r"establishes?", "establish"),
    (r"realizes?", "realize"),
    (r"frustrates?", "frustrate"),
    (r"yields?", "yield"),
    (r"shows?", "show"),
    (r"provides?", "provide"),
]
PREDICATE_RE = re.compile(
    r"\b(?:" + "|".join(f"(?:{pattern})" for pattern, _ in PREDICATES) + r")\b",
    re.I,
)
PREDICATE_NORMALIZATION = [
    (re.compile(rf"^(?:{pattern})$", re.I), normalized)
    for pattern, normalized in PREDICATES
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def norm_key(value: object) -> str:
    text = clean(value).casefold()
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_doi(value: object) -> str:
    doi = clean(value).casefold()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.strip(" .;,")


def stable_id(prefix: str, *values: object) -> str:
    payload = "\x1f".join(clean(value).casefold() for value in values)
    return f"{prefix}_{sha1(payload.encode('utf-8')).hexdigest()[:12]}"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_contract_sha256(path: Path) -> str:
    """Hash only the five allowed source columns, never prior annotation columns."""
    frame = pd.read_csv(
        path,
        usecols=SOURCE_COLUMNS,
        dtype=str,
        keep_default_na=False,
    )[SOURCE_COLUMNS]
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return sha256(payload).hexdigest()


def read_sources() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for filename, source in SOURCES:
        frame = pd.read_csv(
            SOURCE_DIR / filename,
            usecols=SOURCE_COLUMNS,
        )
        for index, row in frame.iterrows():
            source_record_id = f"{source}_{index:04d}"
            doi = clean_doi(row.get("DOI", ""))
            title = clean(row.get("文章名", ""))
            dedupe_key = f"doi:{doi}" if doi else f"title:{norm_key(title)}"
            rows.append(
                {
                    "source_record_id": source_record_id,
                    "source": source,
                    "source_family": "TG" if source == "TG" else "iTE",
                    "dedupe_key": dedupe_key,
                    "year": pd.to_numeric(row.get("年份"), errors="coerce"),
                    "title": title,
                    "journal": clean(row.get("期刊名", "")),
                    "doi": doi,
                    "abstract": clean(row.get("摘要", "")),
                }
            )
    records = pd.DataFrame(rows)

    papers: list[dict[str, object]] = []
    record_to_paper: dict[str, str] = {}
    for number, (dedupe_key, group) in enumerate(
        records.groupby("dedupe_key", sort=False), start=1
    ):
        ranked = group.assign(
            family_rank=group["source_family"].map({"TG": 0, "iTE": 1}),
            abstract_length=group["abstract"].str.len(),
        ).sort_values(
            ["family_rank", "abstract_length"], ascending=[True, False]
        )
        best = ranked.iloc[0]
        paper_id = f"P{number:04d}"
        for source_record_id in group["source_record_id"]:
            record_to_paper[source_record_id] = paper_id
        families = set(group["source_family"])
        membership = "|".join(
            layer for layer in ["iTE", "TG"] if layer in families
        )
        abstract = best["abstract"]
        papers.append(
            {
                "paper_id": paper_id,
                "source_membership": membership,
                "source_record_ids": "; ".join(group["source_record_id"]),
                "year": (
                    int(group["year"].dropna().min())
                    if group["year"].notna().any()
                    else ""
                ),
                "title": best["title"],
                "journal": best["journal"],
                "doi": best["doi"],
                "abstract": abstract,
                "abstract_sha256": sha256(abstract.encode("utf-8")).hexdigest(),
            }
        )
    records["paper_id"] = records["source_record_id"].map(record_to_paper)
    return records, pd.DataFrame(papers)


def first_match(pattern: re.Pattern[str], text: str) -> tuple[str, int, int]:
    match = pattern.search(text)
    if not match:
        return "", -1, -1
    return match.group(0), match.start(), match.end()


def first_affirmed_match(
    pattern: re.Pattern[str], text: str
) -> tuple[str, int, int]:
    """Return the first match not explicitly negated in its local clause."""
    for match in pattern.finditer(text):
        surface = match.group(0)
        if "redox" in surface.casefold():
            before = text[max(0, match.start() - 55) : match.start()].casefold()
            after = text[match.end() : min(len(text), match.end() + 30)].casefold()
            if re.search(
                r"\b(?:without|no|absence of|lack of|free of)\s+"
                r"(?:\w+[ -]?){0,3}$",
                before,
            ) or re.match(r"\s*(?:-|\b)(?:free|inactive|inert|absent)\b", after):
                continue
        return surface, match.start(), match.end()
    return "", -1, -1


def cue_is_contrastive(text: str, start: int, end: int) -> bool:
    if start < 0:
        return False
    before = text[max(0, start - 70) : start].casefold()
    after = text[end : min(len(text), end + 180)].casefold()
    return bool(
        re.search(
            r"(?:different from|unlike|in contrast to|rather than|as opposed to)\s+(?:\w+[ -]?){0,3}$",
            before,
        )
        or re.match(
            r"(?s)[^.!?]{0,130}\b"
            r"(?:eliminated|excluded|absent|negligible|not observed|suppressed)\b",
            after,
        )
    )


def scope_papers(papers: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for paper in papers.itertuples(index=False):
        abstract = clean(paper.abstract)
        tg_surface, tg_start, tg_end = first_match(TG_CUE, abstract)
        tg_core_surface, tg_core_start, tg_core_end = first_match(
            TG_CORE_CUE, abstract
        )
        tg_ambiguous_surface, tg_ambiguous_start, tg_ambiguous_end = first_match(
            TG_AMBIGUOUS_DEVICE_CUE, abstract
        )
        tg_exclusion_surface, tg_exclusion_start, tg_exclusion_end = first_match(
            TG_EXCLUSION_CUE, abstract
        )
        tg_mention_surface, tg_mention_start, tg_mention_end = first_match(
            TG_MENTION_ONLY_CUE, abstract
        )
        ite_strong_surface, ite_strong_start, ite_strong_end = first_match(
            ITE_STRONG_CUE, abstract
        )
        ite_weak_surface, ite_weak_start, ite_weak_end = first_match(
            ITE_WEAK_CUE, abstract
        )
        ite_context_surface, _, _ = first_match(ITE_LIQUID_ION_CONTEXT, abstract)
        ite_soft_surface, _, _ = first_match(ITE_SOFT_MEDIUM_CUE, abstract)
        ite_mobile_ion_surface, _, _ = first_match(ITE_MOBILE_ION_CUE, abstract)
        ite_exclusion_surface, _, _ = first_match(
            ITE_ADJACENT_EXCLUSION_CUE, abstract
        )
        ite_mention_surface, _, _ = first_match(ITE_MENTION_ONLY_CUE, abstract)
        faradaic_surface, faradaic_start, faradaic_end = first_affirmed_match(
            FARADAIC_CUE, abstract
        )
        coupled_strong_surface, coupled_strong_start, coupled_strong_end = first_match(
            COUPLED_STRONG_CUE, abstract
        )
        coupled_general_surface, coupled_general_start, coupled_general_end = first_affirmed_match(
            COUPLED_CUE, abstract
        )
        coupled_surface = coupled_strong_surface or coupled_general_surface
        coupled_start = (
            coupled_strong_start
            if coupled_strong_surface
            else coupled_general_start
        )
        coupled_end = (
            coupled_strong_end
            if coupled_strong_surface
            else coupled_general_end
        )
        solid_surface, solid_start, solid_end = first_match(SOLID_TE_CUE, abstract)

        strong_ite_signal = bool(ite_strong_surface) and not cue_is_contrastive(
            abstract, ite_strong_start, ite_strong_end
        )
        weak_ite_signal = (
            bool(ite_weak_surface)
            and bool(
                ite_context_surface
                or (ite_soft_surface and ite_mobile_ion_surface)
            )
            and not cue_is_contrastive(abstract, ite_weak_start, ite_weak_end)
        )
        ite_signal = strong_ite_signal or weak_ite_signal
        strong_ite = (
            strong_ite_signal
            and not bool(ite_exclusion_surface)
            and not bool(ite_mention_surface)
        )
        weak_ite = (
            weak_ite_signal
            and not bool(ite_exclusion_surface)
            and not bool(ite_mention_surface)
        )
        ite_core = strong_ite or weak_ite

        # "Thermocell" and "thermoelectrochemical cell" are not assigned to TG
        # by name alone: they require an explicit redox/Faradaic span.  In
        # contrast, an explicit "thermogalvanic cell/effect" is direct TG text.
        tg_content_surface = tg_core_surface or (
            tg_ambiguous_surface if faradaic_surface else ""
        )
        tg_content_start = (
            tg_core_start
            if tg_core_surface
            else (tg_ambiguous_start if faradaic_surface else -1)
        )
        tg_content_end = (
            tg_core_end
            if tg_core_surface
            else (tg_ambiguous_end if faradaic_surface else -1)
        )
        tg_core = (
            bool(tg_content_surface)
            and not bool(tg_exclusion_surface)
            and not bool(tg_mention_surface)
            and not cue_is_contrastive(abstract, tg_content_start, tg_content_end)
        )
        overlap = paper.source_membership == "iTE|TG"

        if not abstract:
            decision = "missing_abstract"
            layer = "holdout"
            mechanism_class = "unclear"
            task_relevance = "unresolved"
            cue_type, cue_surface, cue_start, cue_end = "", "", -1, -1
        elif overlap:
            decision = "shared_retrieval_holdout"
            layer = "holdout"
            mechanism_class = (
                "hybrid"
                if ite_signal and (tg_core or faradaic_surface)
                else (
                    ("TG_redox_explicit" if faradaic_surface else "TG_device_term_only")
                    if tg_core
                    else ("iTE_nonfaradaic" if ite_core else "unclear")
                )
            )
            task_relevance = "core_holdout" if (ite_core or tg_core) else "adjacent"
            cue_type, cue_surface, cue_start, cue_end = (
                "shared_retrieval_not_independent",
                tg_content_surface or ite_strong_surface or ite_weak_surface,
                (
                    tg_content_start
                    if tg_content_surface
                    else (ite_strong_start if ite_strong_surface else ite_weak_start)
                ),
                (
                    tg_content_end
                    if tg_content_surface
                    else (ite_strong_end if ite_strong_surface else ite_weak_end)
                ),
            )
        elif tg_surface and (tg_exclusion_surface or tg_mention_surface):
            decision = "TG_retrieval_measurement_or_mention_holdout"
            layer = "holdout"
            mechanism_class = "unclear"
            task_relevance = "measurement_or_mention_adjacent"
            cue_type, cue_surface, cue_start, cue_end = (
                "TG_measurement_separate_technology_or_list_mention",
                tg_exclusion_surface or tg_mention_surface,
                tg_exclusion_start if tg_exclusion_surface else tg_mention_start,
                tg_exclusion_end if tg_exclusion_surface else tg_mention_end,
            )
        elif tg_core and ite_signal:
            decision = "hybrid_coupled_holdout"
            layer = "holdout"
            mechanism_class = "hybrid"
            task_relevance = "core_holdout"
            cue_type, cue_surface, cue_start, cue_end = (
                "iTE_and_TG_content_both_explicit",
                tg_content_surface,
                tg_content_start,
                tg_content_end,
            )
        elif ite_core and (faradaic_surface or coupled_surface):
            decision = "hybrid_coupled_holdout"
            layer = "holdout"
            mechanism_class = "hybrid"
            task_relevance = "core_holdout"
            cue_type, cue_surface, cue_start, cue_end = (
                "faradaic_or_TG_coupling_explicit",
                faradaic_surface or coupled_surface,
                (
                    faradaic_start
                    if faradaic_surface
                    else coupled_start
                ),
                (
                    faradaic_end
                    if faradaic_surface
                    else coupled_end
                ),
            )
        elif tg_core:
            decision = (
                "TG_core_redox_explicit"
                if faradaic_surface
                else "TG_core_device_term_only"
            )
            layer = "TG"
            mechanism_class = (
                "TG_redox_explicit"
                if faradaic_surface
                else "TG_device_term_only"
            )
            task_relevance = "core"
            cue_type, cue_surface, cue_start, cue_end = (
                (
                    "TG_device_with_redox_explicit"
                    if faradaic_surface
                    else "TG_device_or_effect_explicit_without_redox_in_abstract"
                ),
                tg_content_surface,
                tg_content_start,
                tg_content_end,
            )
        elif ite_core:
            decision = "iTE_nonfaradaic_core"
            layer = "iTE"
            mechanism_class = "iTE_nonfaradaic"
            task_relevance = "core"
            cue_type, cue_surface, cue_start, cue_end = (
                "iTE_strong_explicit" if strong_ite else "iTE_qualified_mechanism",
                ite_strong_surface if strong_ite else ite_weak_surface,
                ite_strong_start if strong_ite else ite_weak_start,
                ite_strong_end if strong_ite else ite_weak_end,
            )
        elif paper.source_membership == "TG" and tg_surface:
            decision = "TG_retrieval_adjacent"
            layer = "holdout"
            mechanism_class = "unclear"
            task_relevance = "adjacent"
            cue_type, cue_surface, cue_start, cue_end = (
                "TG_term_without_core_contract",
                tg_surface,
                tg_start,
                tg_end,
            )
        elif ite_strong_surface or ite_weak_surface:
            decision = "iTE_mechanism_adjacent_or_contrast"
            layer = "holdout"
            mechanism_class = "unclear"
            task_relevance = "mechanism_adjacent"
            cue_type, cue_surface, cue_start, cue_end = (
                "iTE_cue_failed_core_contract",
                ite_strong_surface or ite_weak_surface,
                ite_strong_start if ite_strong_surface else ite_weak_start,
                ite_strong_end if ite_strong_surface else ite_weak_end,
            )
        elif solid_surface:
            decision = "solid_or_adjacent_thermoelectric"
            layer = "holdout"
            mechanism_class = "unclear"
            task_relevance = "adjacent"
            cue_type, cue_surface, cue_start, cue_end = (
                "solid_TE_cue",
                solid_surface,
                solid_start,
                solid_end,
            )
        else:
            decision = "retrieval_adjacent_or_out_of_scope"
            layer = "holdout"
            mechanism_class = "unclear"
            task_relevance = "unrelated_or_unresolved"
            cue_type, cue_surface, cue_start, cue_end = "", "", -1, -1

        row = paper._asdict()
        row.update(
            {
                "scope_decision": decision,
                "analysis_layer": layer,
                "mechanism_class": mechanism_class,
                "task_relevance": task_relevance,
                "scope_cue_type": cue_type,
                "scope_evidence_surface": cue_surface,
                "scope_char_start": cue_start,
                "scope_char_end": cue_end,
                "overlap_source_record": overlap,
                "strict_independent_analysis": layer in {"iTE", "TG"} and not overlap,
                "scope_rule_version": "strict_independent_content_v3",
                "ite_content_evidence_surface": (
                    ite_strong_surface or ite_weak_surface
                ),
                "tg_content_evidence_surface": tg_content_surface,
                "faradaic_evidence_surface": faradaic_surface,
                "faradaic_explicit_in_abstract": bool(faradaic_surface),
                "tg_device_term_without_explicit_redox": bool(tg_core)
                and not bool(faradaic_surface),
                "scope_exclusion_surface": (
                    (tg_exclusion_surface or tg_mention_surface)
                    if tg_surface
                    else (ite_exclusion_surface or ite_mention_surface)
                ),
                "scope_human_review": "pending",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def sentence_spans(text: str) -> list[dict[str, object]]:
    # Protect decimal points and common scientific abbreviations while preserving
    # string length, so all returned offsets still address the untouched abstract.
    protected = list(text)
    protected_patterns = [
        re.compile(r"(?<=\d)\.(?=\d)"),
        re.compile(r"(?<=[A-Za-z])\.(?=[A-Za-z])"),
        re.compile(r"(?:\b[A-Za-z]\.){2,}"),
        re.compile(
            r"\b(?:i\.e\.|e\.g\.|et al\.|ca\.|vs\.|etc\.|approx\.|no\.|"
            r"figs?\.|eqs?\.|refs?\.)",
            re.I,
        ),
    ]
    for pattern in protected_patterns:
        for protected_match in pattern.finditer(text):
            for position in range(protected_match.start(), protected_match.end()):
                if protected[position] == ".":
                    protected[position] = "\ue000"
    protected_text = "".join(protected)
    rows = []
    for index, match in enumerate(SENTENCE_RE.finditer(protected_text), start=1):
        raw = text[match.start() : match.end()]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        start = match.start() + leading
        end = match.start() + trailing
        if end <= start:
            continue
        rows.append(
            {
                "sentence_id": index,
                "sentence_start": start,
                "sentence_end": end,
                "sentence_text": text[start:end],
            }
        )
    return rows


def normalized_label(surface: str) -> tuple[str, str]:
    value = clean(surface)
    operations: list[str] = []
    replaced = value.replace("–", "-").replace("—", "-").replace("−", "-")
    if replaced != value:
        operations.append("unicode_dash_to_ascii")
    value = replaced
    greek_map = {
        "α": "alpha",
        "β": "beta",
        "γ": "gamma",
        "δ": "delta",
        "Δ": "delta",
    }
    for source, target in greek_map.items():
        if source in value:
            value = value.replace(source, target)
            operations.append("greek_transliteration")
    lowered = value.casefold()
    if lowered != value:
        operations.append("lowercase")
    value = lowered
    hyphenated = re.sub(r"(?<=\w)-(?=\w)", " ", value)
    if hyphenated != value:
        operations.append("hyphen_to_space")
    value = re.sub(r"[(),;:]", " ", hyphenated)
    value = re.sub(r"\s+", " ", value).strip(" .")
    words = value.split()
    normalized_words = [PLURAL_NORMALIZATION.get(word, word) for word in words]
    if normalized_words != words:
        operations.append("simple_plural_to_singular")
    value = " ".join(normalized_words)
    return value, "; ".join(dict.fromkeys(operations)) or "identity"


def token_head(normalized_token: str) -> str:
    parts = re.split(r"[-/ :]", normalized_token.casefold())
    return parts[-1] if parts else normalized_token.casefold()


def invalid_modifier(token: str) -> bool:
    parts = set(token.split())
    return (
        not token
        or bool(parts & BOUNDARY_WORDS)
        or bool(UNIT_RE.fullmatch(token))
        or bool(re.fullmatch(r"\d+(?:\.\d+)?", token))
    )


def looks_like_formula(surface: str) -> bool:
    compact = re.sub(r"\s+", "", surface)
    if re.search(r"[A-Za-z]+\d[+\-/A-Za-z0-9()]*", compact):
        return True
    if re.fullmatch(r"[A-Z]{2,8}(?::[A-Z]{2,8})?", compact):
        # Alphabetic abbreviations are not concepts. Chemical formulae without
        # numerals are still captured by the element-symbol pattern below (NaI).
        return False
    return bool(re.fullmatch(r"(?:[A-Z][a-z]?\d*){2,}[+\-]*", compact))


ACRONYM_BLOCKLIST = {
    "ITEC",
    "ITECS",
    "TGC",
    "TGCS",
    "SEM",
    "TEM",
    "NMR",
    "XRD",
    "XPS",
    "DFT",
    "EIS",
}

HINGE_SHARED_CATEGORIES = {
    "material_or_structure",
    "mechanism_or_process",
}
HINGE_OTHER_CATEGORIES = HINGE_SHARED_CATEGORIES | {
    "outcome_or_property",
    "literal_formula",
}
HINGE_GENERIC_LABELS = {
    "interaction",
    "transition",
    "difference",
    "cell",
    "ion",
    "pair",
    "power",
    "current",
    "density",
    "coefficient",
}


def extract_candidates(paper: object) -> list[dict[str, object]]:
    abstract = clean(paper.abstract)
    rows: list[dict[str, object]] = []
    if not abstract:
        return rows

    for sentence in sentence_spans(abstract):
        sentence_text = sentence["sentence_text"]
        sentence_start = int(sentence["sentence_start"])
        tokens: list[dict[str, object]] = []
        for match in TOKEN_RE.finditer(sentence_text):
            raw = match.group(0)
            normalized, _ = normalized_label(raw)
            tokens.append(
                {
                    "surface": raw,
                    "normalized": normalized,
                    "start": sentence_start + match.start(),
                    "end": sentence_start + match.end(),
                }
            )

        for index, token in enumerate(tokens):
            head = token_head(str(token["normalized"]))
            category = HEAD_CATEGORY.get(head)
            if not category:
                continue

            start_index = index
            for left_index in range(index - 1, max(-1, index - 4), -1):
                left = tokens[left_index]
                right = tokens[left_index + 1]
                gap = abstract[int(left["end"]) : int(right["start"])]
                left_norm = str(left["normalized"])
                if re.search(r"[,;:.!?()]", gap) or invalid_modifier(left_norm):
                    break
                start_index = left_index

            start = int(tokens[start_index]["start"])
            end = int(token["end"])
            surface = abstract[start:end]
            label, operations = normalized_label(surface)
            if not label:
                continue
            if " " not in label and label not in SINGLETON_ALLOWED:
                continue
            rows.append(
                {
                    "paper_id": paper.paper_id,
                    "analysis_layer": paper.analysis_layer,
                    "source_membership": paper.source_membership,
                    "year": paper.year,
                    "title": paper.title,
                    "doi": paper.doi,
                    "sentence_id": sentence["sentence_id"],
                    "sentence_text": sentence_text,
                    "sentence_char_start": sentence["sentence_start"],
                    "sentence_char_end": sentence["sentence_end"],
                    "surface_text": surface,
                    "normalized_label": label,
                    "normalization_operations": operations,
                    "lexical_category": category,
                    "head_token": head,
                    "char_start": start,
                    "char_end": end,
                    "extractor_pattern": "head_noun_phrase",
                }
            )

        # Generic fallback for a spelled-out hyphenated scientific keyword.  It
        # avoids maintaining case-specific entity lists (for example a preferred
        # host molecule) while keeping the occurrence fully extractive.
        for token in tokens:
            surface = str(token["surface"])
            token_start = int(token["start"])
            token_end = int(token["end"])
            label, operations = normalized_label(surface)
            hyphen_parts = surface.split("-")
            if (
                "-" not in surface
                or not re.fullmatch(
                    r"[A-Za-zα-ωΑ-Ω]{3,}(?:-[A-Za-zα-ωΑ-Ω]{3,})+",
                    surface,
                )
                or len(label) < 5
                or any(len(part) < 3 for part in hyphen_parts)
                or any(len(part) > 1 and part.isupper() for part in hyphen_parts)
                or token_head(label) in HEAD_CATEGORY
                or invalid_modifier(label)
                or (token_start > 0 and abstract[token_start - 1] == "(")
                or (token_end < len(abstract) and abstract[token_end] == ")")
            ):
                continue
            rows.append(
                {
                    "paper_id": paper.paper_id,
                    "analysis_layer": paper.analysis_layer,
                    "source_membership": paper.source_membership,
                    "year": paper.year,
                    "title": paper.title,
                    "doi": paper.doi,
                    "sentence_id": sentence["sentence_id"],
                    "sentence_text": sentence_text,
                    "sentence_char_start": sentence["sentence_start"],
                    "sentence_char_end": sentence["sentence_end"],
                    "surface_text": surface,
                    "normalized_label": label,
                    "normalization_operations": operations,
                    "lexical_category": "untyped_extractive_keyword",
                    "head_token": token_head(label),
                    "char_start": token_start,
                    "char_end": token_end,
                    "extractor_pattern": "generic_hyphenated_keyword",
                }
            )

        # Formula/acronym entities are independent literal occurrences.
        for token in tokens:
            surface = str(token["surface"])
            token_start = int(token["start"])
            token_end = int(token["end"])
            if (
                not looks_like_formula(surface)
                or surface.upper().strip("+-") in ACRONYM_BLOCKLIST
                or (token_start > 0 and abstract[token_start - 1] == "(")
                or (token_end < len(abstract) and abstract[token_end] == ")")
            ):
                continue
            label, operations = normalized_label(surface)
            rows.append(
                {
                    "paper_id": paper.paper_id,
                    "analysis_layer": paper.analysis_layer,
                    "source_membership": paper.source_membership,
                    "year": paper.year,
                    "title": paper.title,
                    "doi": paper.doi,
                    "sentence_id": sentence["sentence_id"],
                    "sentence_text": sentence_text,
                    "sentence_char_start": sentence["sentence_start"],
                    "sentence_char_end": sentence["sentence_end"],
                    "surface_text": surface,
                    "normalized_label": label,
                    "normalization_operations": operations,
                    "lexical_category": "literal_formula",
                    "head_token": label,
                    "char_start": token_start,
                    "char_end": token_end,
                    "extractor_pattern": "literal_formula",
                }
            )
    return rows


def select_concepts(
    papers: pd.DataFrame, candidate_rows: list[dict[str, object]], limit: int = 20
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not candidate_rows:
        return pd.DataFrame(), pd.DataFrame()
    candidates = pd.DataFrame(candidate_rows).drop_duplicates(
        ["paper_id", "normalized_label", "char_start", "char_end", "lexical_category"]
    )
    document_frequency = (
        candidates.groupby("normalized_label")["paper_id"].nunique().to_dict()
    )
    paper_occurrence_count = (
        candidates.groupby(["paper_id", "normalized_label"]).size().to_dict()
    )
    category_priority = {
        "mechanism_or_process": 4.0,
        "material_or_structure": 3.8,
        "outcome_or_property": 3.0,
        "literal_formula": 2.8,
        "untyped_extractive_keyword": 2.6,
        "evidence_method": 2.0,
        "device_or_context": 1.5,
    }
    candidates["document_frequency"] = candidates["normalized_label"].map(
        document_frequency
    )
    candidates["paper_occurrence_count"] = candidates.apply(
        lambda row: paper_occurrence_count[
            (row["paper_id"], row["normalized_label"])
        ],
        axis=1,
    )
    candidates["token_count"] = candidates["normalized_label"].str.split().str.len()
    candidates["selection_score"] = candidates.apply(
        lambda row: round(
            category_priority.get(row["lexical_category"], 1.0)
            + 0.30 * min(math.log1p(int(row["paper_occurrence_count"])), 2.0)
            + 0.06 * min(int(row["token_count"]), 4),
            4,
        ),
        axis=1,
    )

    selected_labels: dict[str, set[str]] = defaultdict(set)
    for paper_id, group in candidates.groupby("paper_id", sort=False):
        label_rows = (
            group.sort_values(
                [
                    "selection_score",
                    "paper_occurrence_count",
                    "token_count",
                    "char_start",
                ],
                ascending=[False, False, False, True],
            )
            .drop_duplicates("normalized_label")
            .to_dict("records")
        )
        chosen: list[dict[str, object]] = []
        for row in label_rows:
            label = str(row["normalized_label"])
            label_tokens = set(label.split())
            nested_conflict = False
            for existing in chosen:
                if row["head_token"] != existing["head_token"]:
                    continue
                # A longer occurrence in a different sentence must not erase a
                # shorter exact endpoint used by a local predicate elsewhere.
                if row["sentence_id"] != existing["sentence_id"]:
                    continue
                existing_tokens = set(str(existing["normalized_label"]).split())
                if label_tokens < existing_tokens or existing_tokens < label_tokens:
                    nested_conflict = True
                    break
            if nested_conflict:
                continue
            chosen.append(row)
            selected_labels[paper_id].add(label)
            if len(chosen) >= limit:
                break

    selected_occurrences = candidates[
        candidates.apply(
            lambda row: row["normalized_label"] in selected_labels[row["paper_id"]],
            axis=1,
        )
    ].copy()
    selected_occurrences.insert(
        5,
        "concept_occurrence_id",
        [
            stable_id(
                "CO",
                row.paper_id,
                row.normalized_label,
                row.char_start,
                row.char_end,
            )
            for row in selected_occurrences.itertuples(index=False)
        ],
    )
    selected_occurrences["global_concept_id"] = selected_occurrences[
        "normalized_label"
    ].map(lambda label: stable_id("GC", label))
    selected_occurrences["layer_node_id"] = selected_occurrences.apply(
        lambda row: stable_id("LN", row["analysis_layer"], row["normalized_label"]),
        axis=1,
    )
    selected_occurrences["span_exact_match"] = selected_occurrences.apply(
        lambda row: row["surface_text"]
        == papers.set_index("paper_id").loc[row["paper_id"], "abstract"][
            int(row["char_start"]) : int(row["char_end"])
        ],
        axis=1,
    )
    selected_occurrences["semantic_addition_allowed"] = False
    selected_occurrences["selection_scope"] = "single_abstract_only"
    selected_occurrences["cross_paper_frequency_used_for_selection"] = False
    selected_occurrences["verifier_status"] = selected_occurrences[
        "span_exact_match"
    ].map({True: "span_valid_pending_semantic_review", False: "invalid_span"})

    primary = (
        selected_occurrences.sort_values(
            [
                "paper_id",
                "normalized_label",
                "selection_score",
                "char_start",
            ],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(["paper_id", "normalized_label"])
        .copy()
    )
    occurrence_counts = (
        selected_occurrences.groupby(["paper_id", "normalized_label"])
        .size()
        .rename("occurrence_count")
    )
    primary = primary.merge(
        occurrence_counts,
        on=["paper_id", "normalized_label"],
        how="left",
    )
    primary.insert(
        5,
        "paper_concept_id",
        [
            stable_id("PC", row.paper_id, row.normalized_label)
            for row in primary.itertuples(index=False)
        ],
    )
    return selected_occurrences.reset_index(drop=True), primary.reset_index(drop=True)


def normalize_predicate(surface: str) -> str:
    for pattern, normalized in PREDICATE_NORMALIZATION:
        if pattern.fullmatch(surface):
            return normalized
    return clean(surface).casefold().replace(" ", "_")


def assertion_status(sentence: str, predicate_start: int) -> str:
    before = sentence[:predicate_start].casefold()
    clause_before = re.split(
        r"(?:;|,\s*(?:while|whereas|but|however)\b)", before
    )[-1]
    local_before = clause_before[-70:]
    negation_scope = re.sub(r"\bnot only\b", "", local_before)
    if re.search(
        r"\b(?:not|never|neither|without)\b(?:\W+\w+){0,5}\W*$",
        negation_scope,
    ):
        return "negated"
    if re.search(r"\bto(?:\s+\w+){0,3}\s*$", before):
        if re.search(
            r"\b(?:found|shown|observed|demonstrated|reported|confirmed)\s+to\s*$",
            before,
        ):
            return "observed_assertion"
        return "purpose_or_design"
    if re.search(
        r"\b(?:aim|aims|aimed|aiming|seek|seeks|seeking|suggest|suggests|"
        r"suggested|hypothesize|hypothesizes|hypothesized|will)\b",
        clause_before,
    ):
        return "hypothetical_or_epistemic"
    if re.search(
        r"\b(?:can|may|might|could|would|should|possibly|potentially|potential|capable)\b",
        clause_before,
    ):
        return "hypothetical_or_modal"
    return "observed_assertion"


def predicate_risk_flags(
    sentence: str,
    match: re.Match[str],
    source: pd.Series,
    target: pd.Series,
    predicate_matches: list[re.Match[str]],
    sentence_start: int,
) -> dict[str, bool]:
    predicate = normalize_predicate(match.group(0))
    local_start = int(source["char_end"]) - sentence_start
    local_end = int(target["char_start"]) - sentence_start
    source_gap = match.start() - local_start
    target_gap = local_end - match.end()
    endpoint_gap_text = sentence[max(0, local_start) : max(0, local_end)]
    subject_tail = sentence[max(0, local_start) : match.start()].casefold()
    target_prefix = sentence[match.end() : max(match.end(), local_end)].casefold()
    before = sentence[max(0, match.start() - 45) : match.start()].casefold()
    after = sentence[match.end() : min(len(sentence), match.end() + 45)].casefold()

    ambiguous_nominal = predicate in {
        "increase",
        "decrease",
        "form",
        "limit",
        "control",
        "drive",
    }
    nominal_context = bool(
        re.search(r"\b(?:the|an|a|this|that|such|net|rate|level)\s+$", before)
        or (
            predicate in {"increase", "decrease", "form"}
            and re.match(r"\s+(?:in|of)\b", after)
        )
        or (predicate == "limit" and re.match(r"\s+and\b", after))
    )
    hyphenated = (
        match.start() > 0 and sentence[match.start() - 1] == "-"
    ) or (match.end() < len(sentence) and sentence[match.end()] == "-")
    other_predicate_between = any(
        other.start() >= local_start
        and other.end() <= local_end
        and other.start() != match.start()
        for other in predicate_matches
    )
    previous_predicates = [
        other for other in predicate_matches if other.end() <= local_start
    ]
    coordinated_inherited_subject = False
    if previous_predicates:
        previous = previous_predicates[-1]
        bridge = sentence[previous.end() : match.start()].casefold()
        coordinated_inherited_subject = (
            local_start - previous.end() <= 80
            and bool(re.search(r"(?:,|\band\b|\bwhile\b|\bbut\b)", bridge))
        )
    return {
        "risk_nominal_predicate": ambiguous_nominal and nominal_context,
        "risk_hyphenated_predicate": hyphenated,
        "risk_cross_clause": bool(
            re.search(r"[,;]|\b(?:while|whereas|but|however)\b", endpoint_gap_text)
        ),
        "risk_other_predicate_between_endpoints": other_predicate_between,
        "risk_long_endpoint_gap": source_gap > 60 or target_gap > 60,
        "risk_coordinated_inherited_subject": coordinated_inherited_subject,
        "risk_compound_subject_after_selected_source": bool(
            re.search(r"\band\b", subject_tail)
        )
        and not bool(re.search(r"\bbetween\b[^,;]*\band\b", subject_tail)),
        "risk_intervening_target_head": bool(
            re.search(
                r"\b(?:pathways?|routes?|means|methods?|strateg(?:y|ies)|mechanisms?)\b",
                target_prefix,
            )
        ),
    }


def extract_relations(
    papers: pd.DataFrame, occurrences: pd.DataFrame
) -> pd.DataFrame:
    if occurrences.empty:
        return pd.DataFrame()
    paper_lookup = papers.set_index("paper_id")
    rows: list[dict[str, object]] = []
    for paper_id, group in occurrences.groupby("paper_id", sort=False):
        abstract = paper_lookup.loc[paper_id, "abstract"]
        for sentence_id, sentence_group in group.groupby("sentence_id", sort=False):
            sentence_start = int(sentence_group["sentence_char_start"].iloc[0])
            sentence_text = str(sentence_group["sentence_text"].iloc[0])
            predicate_matches = list(PREDICATE_RE.finditer(sentence_text))
            for match in predicate_matches:
                predicate_start = sentence_start + match.start()
                predicate_end = sentence_start + match.end()
                left = sentence_group[
                    sentence_group["char_end"].astype(int) <= predicate_start
                ].copy()
                right = sentence_group[
                    sentence_group["char_start"].astype(int) >= predicate_end
                ].copy()
                allowed_relation_categories = {
                    "mechanism_or_process",
                    "outcome_or_property",
                    "material_or_structure",
                    "literal_formula",
                }
                left = left[
                    left["lexical_category"].isin(allowed_relation_categories)
                ]
                right = right[
                    right["lexical_category"].isin(allowed_relation_categories)
                ]
                if left.empty or right.empty:
                    continue
                left["span_length"] = left["char_end"].astype(int) - left[
                    "char_start"
                ].astype(int)
                right["span_length"] = right["char_end"].astype(int) - right[
                    "char_start"
                ].astype(int)
                semantic_priority = {
                    "mechanism_or_process": 4,
                    "outcome_or_property": 3,
                    "material_or_structure": 2,
                    "literal_formula": 1,
                    "device_or_context": 0,
                    "evidence_method": -1,
                }
                left["semantic_priority"] = left["lexical_category"].map(
                    semantic_priority
                ).fillna(0)
                right["semantic_priority"] = right["lexical_category"].map(
                    semantic_priority
                ).fillna(0)
                # Prefer an explicit process/property in the local clause. Fall
                # back to the nearest material only when no such concept exists.
                left = left[
                    predicate_start - left["char_end"].astype(int) <= 180
                ]
                right = right[
                    right["char_start"].astype(int) - predicate_end <= 180
                ]
                if left.empty or right.empty:
                    continue
                source = left.sort_values(
                    ["semantic_priority", "char_end", "span_length"],
                    ascending=[False, False, False],
                ).iloc[0]
                target = right.sort_values(
                    ["semantic_priority", "char_start", "span_length"],
                    ascending=[False, True, False],
                ).iloc[0]
                if source["global_concept_id"] == target["global_concept_id"]:
                    continue
                surface = match.group(0)
                if normalize_predicate(surface) == "provide":
                    gap_to_target = sentence_text[
                        match.end() : int(target["char_start"]) - sentence_start
                    ].casefold()
                    if "perspective" in gap_to_target:
                        continue
                status = assertion_status(sentence_text, match.start())
                risk_flags = predicate_risk_flags(
                    sentence_text,
                    match,
                    source,
                    target,
                    predicate_matches,
                    sentence_start,
                )
                risk_reasons = [
                    name for name, present in risk_flags.items() if present
                ]
                strict_gate = (
                    status == "observed_assertion"
                    and source["analysis_layer"] in {"iTE", "TG"}
                    and not risk_reasons
                )
                rows.append(
                    {
                        "relation_id": stable_id(
                            "AR",
                            paper_id,
                            source["concept_occurrence_id"],
                            surface,
                            target["concept_occurrence_id"],
                        ),
                        "paper_id": paper_id,
                        "analysis_layer": source["analysis_layer"],
                        "source_membership": source["source_membership"],
                        "year": source["year"],
                        "title": source["title"],
                        "doi": source["doi"],
                        "sentence_id": sentence_id,
                        "evidence_sentence": sentence_text,
                        "sentence_char_start": sentence_start,
                        "sentence_char_end": sentence_start + len(sentence_text),
                        "source_occurrence_id": source["concept_occurrence_id"],
                        "source_global_concept_id": source["global_concept_id"],
                        "source_layer_node_id": source["layer_node_id"],
                        "source_surface": source["surface_text"],
                        "source_normalized_label": source["normalized_label"],
                        "source_char_start": int(source["char_start"]),
                        "source_char_end": int(source["char_end"]),
                        "predicate_surface": surface,
                        "predicate_normalized": normalize_predicate(surface),
                        "predicate_char_start": predicate_start,
                        "predicate_char_end": predicate_end,
                        "target_occurrence_id": target["concept_occurrence_id"],
                        "target_global_concept_id": target["global_concept_id"],
                        "target_layer_node_id": target["layer_node_id"],
                        "target_surface": target["surface_text"],
                        "target_normalized_label": target["normalized_label"],
                        "target_char_start": int(target["char_start"]),
                        "target_char_end": int(target["char_end"]),
                        "assertion_status": status,
                        **risk_flags,
                        "risk_reasons": "; ".join(risk_reasons),
                        "strict_syntax_eligible": strict_gate,
                        "human_semantic_review": "pending",
                        "graph_eligible": False,
                        "verifier_status": (
                            "strict_syntax_gate_pass_pending_semantic_review"
                            if strict_gate
                            else "relation_review_required"
                        ),
                    }
                )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates("relation_id")


def build_sentence_pairs(
    papers: pd.DataFrame, occurrences: pd.DataFrame, relations: pd.DataFrame
) -> pd.DataFrame:
    if occurrences.empty:
        return pd.DataFrame()
    relation_pairs: set[tuple[str, int, str, str]] = set()
    if not relations.empty:
        eligible = relations[relations["strict_syntax_eligible"]]
        for row in eligible.itertuples(index=False):
            relation_pairs.add(
                (
                    row.paper_id,
                    int(row.sentence_id),
                    min(row.source_global_concept_id, row.target_global_concept_id),
                    max(row.source_global_concept_id, row.target_global_concept_id),
                )
            )

    rows: list[dict[str, object]] = []
    for (paper_id, sentence_id), group in occurrences.groupby(
        ["paper_id", "sentence_id"], sort=False
    ):
        layer = group["analysis_layer"].iloc[0]
        if layer not in {"iTE", "TG"}:
            continue
        # Limit dense sentences using the extractive selection score only.
        concepts = (
            group.sort_values(
                ["selection_score", "paper_occurrence_count", "char_start"],
                ascending=[False, False, True],
            )
            .drop_duplicates("global_concept_id")
            .head(8)
            .to_dict("records")
        )
        for left, right in combinations(concepts, 2):
            if left["global_concept_id"] > right["global_concept_id"]:
                left, right = right, left
            relation_supported = (
                paper_id,
                int(sentence_id),
                left["global_concept_id"],
                right["global_concept_id"],
            ) in relation_pairs
            rows.append(
                {
                    "sentence_pair_id": stable_id(
                        "SP",
                        paper_id,
                        sentence_id,
                        left["global_concept_id"],
                        right["global_concept_id"],
                    ),
                    "paper_id": paper_id,
                    "analysis_layer": layer,
                    "source_membership": left["source_membership"],
                    "year": left["year"],
                    "title": left["title"],
                    "doi": left["doi"],
                    "sentence_id": sentence_id,
                    "evidence_sentence": left["sentence_text"],
                    "left_global_concept_id": left["global_concept_id"],
                    "left_layer_node_id": left["layer_node_id"],
                    "left_label": left["normalized_label"],
                    "left_surface": left["surface_text"],
                    "left_char_start": int(left["char_start"]),
                    "left_char_end": int(left["char_end"]),
                    "right_global_concept_id": right["global_concept_id"],
                    "right_layer_node_id": right["layer_node_id"],
                    "right_label": right["normalized_label"],
                    "right_surface": right["surface_text"],
                    "right_char_start": int(right["char_start"]),
                    "right_char_end": int(right["char_end"]),
                    "pair_key": f"{left['global_concept_id']}::{right['global_concept_id']}",
                    "evidence_scope": "same_sentence_cooccurrence_not_causal",
                    "strict_syntax_relation_supported": relation_supported,
                }
            )
    return pd.DataFrame(rows).drop_duplicates("sentence_pair_id") if rows else pd.DataFrame()


def joined(values: pd.Series, limit: int = 1000) -> str:
    return "; ".join(list(dict.fromkeys(clean(value) for value in values if clean(value)))[:limit])


def build_pair_bank(sentence_pairs: pd.DataFrame, layer: str) -> pd.DataFrame:
    frame = sentence_pairs[sentence_pairs["analysis_layer"].eq(layer)].copy()
    if frame.empty:
        return frame
    bank = (
        frame.groupby(
            [
                "pair_key",
                "left_global_concept_id",
                "left_label",
                "right_global_concept_id",
                "right_label",
            ],
            as_index=False,
        )
        .agg(
            paper_count=("paper_id", "nunique"),
            sentence_count=("sentence_pair_id", "nunique"),
            strict_syntax_relation_paper_count=(
                "paper_id",
                lambda values: 0,
            ),
            first_year=("year", "min"),
            last_year=("year", "max"),
            supporting_paper_ids=("paper_id", joined),
            supporting_dois=("doi", joined),
            supporting_titles=("title", lambda values: joined(values, limit=5)),
            example_evidence_sentence=("evidence_sentence", "first"),
            example_left_surface=("left_surface", "first"),
            example_right_surface=("right_surface", "first"),
        )
    )
    strict_counts = (
        frame[frame["strict_syntax_relation_supported"]]
        .groupby("pair_key")["paper_id"]
        .nunique()
    )
    bank["strict_syntax_relation_paper_count"] = (
        bank["pair_key"].map(strict_counts).fillna(0).astype(int)
    )
    bank.insert(
        0,
        "pair_id",
        [stable_id("IP" if layer == "iTE" else "TP", key) for key in bank["pair_key"]],
    )
    bank.insert(1, "analysis_layer", layer)
    return bank.sort_values(
        ["strict_syntax_relation_paper_count", "paper_count", "sentence_count", "pair_key"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def direct_pair_overlaps(ite: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    joined_frame = ite.merge(
        tg,
        on=[
            "pair_key",
            "left_global_concept_id",
            "left_label",
            "right_global_concept_id",
            "right_label",
        ],
        suffixes=("_ite", "_tg"),
    )
    if joined_frame.empty:
        return joined_frame
    joined_frame.insert(
        0,
        "overlap_id",
        [stable_id("XO", key) for key in joined_frame["pair_key"]],
    )
    joined_frame["interpretation"] = "same_normalized_pair_observed_independently_in_both_layers"
    return joined_frame


def build_pair_support_evidence(
    sentence_pairs: pd.DataFrame,
    relations: pd.DataFrame,
    papers: pd.DataFrame,
    ite_pairs: pd.DataFrame,
    tg_pairs: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize pair provenance into atomic, non-positional source tuples.

    Candidate rows reference pair IDs.  This table is the authoritative bridge
    from a pair ID to an exact paper, sentence-pair row, and optional relation
    row; independently joined paper/DOI/title strings are never used as tuples.
    """
    if sentence_pairs.empty:
        return pd.DataFrame()
    pair_id_lookup = {
        (row.analysis_layer, row.pair_key): row.pair_id
        for frame in (ite_pairs, tg_pairs)
        for row in frame.itertuples(index=False)
    }
    paper_lookup = papers.set_index("paper_id").to_dict("index")

    relation_groups: dict[tuple[str, str, str, str], list[dict[str, object]]] = (
        defaultdict(list)
    )
    if not relations.empty:
        for relation in relations.to_dict("records"):
            relation_pair_key = "::".join(
                sorted(
                    [
                        relation["source_global_concept_id"],
                        relation["target_global_concept_id"],
                    ]
                )
            )
            relation_groups[
                (
                    relation["analysis_layer"],
                    relation["paper_id"],
                    relation["sentence_id"],
                    relation_pair_key,
                )
            ].append(relation)

    rows: list[dict[str, object]] = []
    for pair_evidence in sentence_pairs.to_dict("records"):
        pair_id = pair_id_lookup[
            (pair_evidence["analysis_layer"], pair_evidence["pair_key"])
        ]
        matching_relations = relation_groups.get(
            (
                pair_evidence["analysis_layer"],
                pair_evidence["paper_id"],
                pair_evidence["sentence_id"],
                pair_evidence["pair_key"],
            ),
            [],
        )
        if not matching_relations:
            matching_relations = [None]
        paper = paper_lookup[pair_evidence["paper_id"]]
        for relation in matching_relations:
            relation_id = "" if relation is None else relation["relation_id"]
            evidence_scope = (
                "same_sentence_cooccurrence_only"
                if relation is None
                else (
                    "strict_syntax_relation_candidate"
                    if bool(relation["strict_syntax_eligible"])
                    else "non_strict_relation_candidate"
                )
            )
            rows.append(
                {
                    "pair_evidence_id": stable_id(
                        "PE",
                        pair_id,
                        pair_evidence["sentence_pair_id"],
                        relation_id or "cooccurrence_only",
                    ),
                    "pair_id": pair_id,
                    "analysis_layer": pair_evidence["analysis_layer"],
                    "pair_key": pair_evidence["pair_key"],
                    "sentence_pair_id": pair_evidence["sentence_pair_id"],
                    "relation_id": relation_id,
                    "paper_id": pair_evidence["paper_id"],
                    "source_record_ids": paper["source_record_ids"],
                    "doi": paper["doi"],
                    "title": paper["title"],
                    "abstract_sha256": paper["abstract_sha256"],
                    "sentence_id": pair_evidence["sentence_id"],
                    "evidence_sentence": pair_evidence["evidence_sentence"],
                    "left_global_concept_id": pair_evidence[
                        "left_global_concept_id"
                    ],
                    "left_surface": pair_evidence["left_surface"],
                    "left_char_start": pair_evidence["left_char_start"],
                    "left_char_end": pair_evidence["left_char_end"],
                    "right_global_concept_id": pair_evidence[
                        "right_global_concept_id"
                    ],
                    "right_surface": pair_evidence["right_surface"],
                    "right_char_start": pair_evidence["right_char_start"],
                    "right_char_end": pair_evidence["right_char_end"],
                    "relation_source_surface": (
                        "" if relation is None else relation["source_surface"]
                    ),
                    "relation_source_char_start": (
                        "" if relation is None else relation["source_char_start"]
                    ),
                    "relation_source_char_end": (
                        "" if relation is None else relation["source_char_end"]
                    ),
                    "predicate_surface": (
                        "" if relation is None else relation["predicate_surface"]
                    ),
                    "predicate_char_start": (
                        "" if relation is None else relation["predicate_char_start"]
                    ),
                    "predicate_char_end": (
                        "" if relation is None else relation["predicate_char_end"]
                    ),
                    "relation_target_surface": (
                        "" if relation is None else relation["target_surface"]
                    ),
                    "relation_target_char_start": (
                        "" if relation is None else relation["target_char_start"]
                    ),
                    "relation_target_char_end": (
                        "" if relation is None else relation["target_char_end"]
                    ),
                    "strict_syntax_eligible": (
                        False
                        if relation is None
                        else bool(relation["strict_syntax_eligible"])
                    ),
                    "graph_eligible": (
                        False if relation is None else bool(relation["graph_eligible"])
                    ),
                    "evidence_scope": evidence_scope,
                }
            )
    frame = pd.DataFrame(rows).drop_duplicates("pair_evidence_id")
    return frame.sort_values(
        ["analysis_layer", "pair_id", "paper_id", "sentence_id", "relation_id"]
    ).reset_index(drop=True)


def tiered_shared_node_pair_candidates(
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    concepts: pd.DataFrame,
    relations: pd.DataFrame,
) -> pd.DataFrame:
    """Enumerate every cross-layer pair combination around an exact shared node.

    Evidence tier is identity-blind and depends only on whether each incident
    pair has a strict-syntax relation candidate.  No paper/control/program
    identity, novelty label, or compatibility judgment enters selection or rank.
    The full table is intentionally untruncated; task-focus flags are annotations,
    not gates.
    """
    if ite.empty or tg.empty:
        return pd.DataFrame()

    layer_concept_df = (
        concepts[concepts["analysis_layer"].isin(["iTE", "TG"])]
        .groupby(["analysis_layer", "global_concept_id"])["paper_id"]
        .nunique()
        .to_dict()
    )
    concept_category = (
        concepts.groupby("global_concept_id")["lexical_category"]
        .agg(lambda values: Counter(values).most_common(1)[0][0])
        .to_dict()
    )
    strict_relation_lookup: dict[tuple[str, str], dict[str, object]] = {}
    human_relation_lookup: dict[tuple[str, str], dict[str, object]] = {}
    if not relations.empty:
        relation_frame = relations.copy()
        relation_frame["pair_key"] = relation_frame.apply(
            lambda row: "::".join(
                sorted(
                    [
                        row["source_global_concept_id"],
                        row["target_global_concept_id"],
                    ]
                )
            ),
            axis=1,
        )
        for relation_mask, lookup in [
            (relation_frame["strict_syntax_eligible"], strict_relation_lookup),
            (relation_frame["graph_eligible"], human_relation_lookup),
        ]:
            for key, group in relation_frame[relation_mask].groupby(
                ["analysis_layer", "pair_key"], sort=False
            ):
                lookup[key] = {
                    "relation_ids": joined(group["relation_id"]),
                    "paper_ids": joined(group["paper_id"]),
                    "paper_count": int(group["paper_id"].nunique()),
                    "evidence": joined(
                        group.apply(
                            lambda row: (
                                f"{row['source_surface']} --{row['predicate_surface']}--> "
                                f"{row['target_surface']} || {row['evidence_sentence']}"
                            ),
                            axis=1,
                        ),
                    ),
                }

    ite_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    tg_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    node_labels: dict[str, str] = {}
    for record in ite.to_dict("records"):
        ite_by_node[record["left_global_concept_id"]].append(record)
        ite_by_node[record["right_global_concept_id"]].append(record)
        node_labels[record["left_global_concept_id"]] = record["left_label"]
        node_labels[record["right_global_concept_id"]] = record["right_label"]
    for record in tg.to_dict("records"):
        tg_by_node[record["left_global_concept_id"]].append(record)
        tg_by_node[record["right_global_concept_id"]].append(record)
        node_labels.setdefault(record["left_global_concept_id"], record["left_label"])
        node_labels.setdefault(record["right_global_concept_id"], record["right_label"])

    ite_pair_keys = set(ite["pair_key"])
    tg_pair_keys = set(tg["pair_key"])

    rows: list[dict[str, object]] = []
    for shared_id in sorted(set(ite_by_node) & set(tg_by_node)):
        shared_label = node_labels.get(shared_id, "")
        shared_category = concept_category.get(shared_id, "")
        shared_focus = (
            shared_category in HINGE_SHARED_CATEGORIES
            and shared_label not in HINGE_GENERIC_LABELS
        )
        ite_pairs = sorted(
            ite_by_node[shared_id],
            key=lambda row: (
                int(row["strict_syntax_relation_paper_count"]),
                int(row["paper_count"]),
                int(row["sentence_count"]),
                row["pair_id"],
            ),
            reverse=True,
        )
        tg_pairs = sorted(
            tg_by_node[shared_id],
            key=lambda row: (
                int(row["strict_syntax_relation_paper_count"]),
                int(row["paper_count"]),
                int(row["sentence_count"]),
                row["pair_id"],
            ),
            reverse=True,
        )
        for ite_pair in ite_pairs:
            for tg_pair in tg_pairs:
                # Exact same whole-pair matches are direct overlaps, reported in
                # their own table; a shared-node candidate requires two distinct
                # incident pairs.
                if ite_pair["pair_key"] == tg_pair["pair_key"]:
                    continue
                ite_other_id = (
                    ite_pair["right_global_concept_id"]
                    if ite_pair["left_global_concept_id"] == shared_id
                    else ite_pair["left_global_concept_id"]
                )
                ite_other_label = (
                    ite_pair["right_label"]
                    if ite_pair["left_global_concept_id"] == shared_id
                    else ite_pair["left_label"]
                )
                tg_other_id = (
                    tg_pair["right_global_concept_id"]
                    if tg_pair["left_global_concept_id"] == shared_id
                    else tg_pair["left_global_concept_id"]
                )
                tg_other_label = (
                    tg_pair["right_label"]
                    if tg_pair["left_global_concept_id"] == shared_id
                    else tg_pair["left_label"]
                )
                if ite_other_id == tg_other_id:
                    continue

                ite_other_category = concept_category.get(ite_other_id, "")
                tg_other_category = concept_category.get(tg_other_id, "")
                other_focus = (
                    ite_other_category in HINGE_OTHER_CATEGORIES
                    and tg_other_category in HINGE_OTHER_CATEGORIES
                    and ite_other_label not in HINGE_GENERIC_LABELS
                    and tg_other_label not in HINGE_GENERIC_LABELS
                )
                ite_relation_count = int(
                    ite_pair["strict_syntax_relation_paper_count"]
                )
                tg_relation_count = int(
                    tg_pair["strict_syntax_relation_paper_count"]
                )
                ite_human_relation_evidence = human_relation_lookup.get(
                    ("iTE", ite_pair["pair_key"]), {}
                )
                tg_human_relation_evidence = human_relation_lookup.get(
                    ("TG", tg_pair["pair_key"]), {}
                )
                ite_human_relation_count = int(
                    ite_human_relation_evidence.get("paper_count", 0)
                )
                tg_human_relation_count = int(
                    tg_human_relation_evidence.get("paper_count", 0)
                )
                ite_relation = ite_relation_count > 0
                tg_relation = tg_relation_count > 0
                ite_side_level = (
                    3
                    if ite_human_relation_count > 0
                    else (2 if ite_relation else 1)
                )
                tg_side_level = (
                    3
                    if tg_human_relation_count > 0
                    else (2 if tg_relation else 1)
                )
                evidence_floor = min(ite_side_level, tg_side_level)
                evidence_ceiling = max(ite_side_level, tg_side_level)
                if evidence_floor >= 3:
                    evidence_grade = "G3_dual_human_confirmed_relations"
                    evidence_grade_order = 0
                elif evidence_floor >= 2:
                    evidence_grade = "G2_dual_strict_syntax_candidates"
                    evidence_grade_order = 1
                elif evidence_ceiling >= 2:
                    evidence_grade = "G1_single_strict_syntax_candidate"
                    evidence_grade_order = 2
                else:
                    evidence_grade = "G0_cooccurrence_only"
                    evidence_grade_order = 3

                if ite_relation and tg_relation:
                    tier = "A_dual_strict_syntax_candidates"
                    tier_order = 1
                    relation_side = "both"
                    tier_reason = "both_incident_pairs_have_strict_syntax_relation_support"
                elif ite_relation or tg_relation:
                    tier = "B_single_strict_syntax_candidate"
                    tier_order = 2
                    relation_side = "iTE" if ite_relation else "TG"
                    tier_reason = "one_incident_pair_has_strict_syntax_relation_support"
                else:
                    tier = "C_cooccurrence_only"
                    tier_order = 3
                    relation_side = "none"
                    tier_reason = "neither_incident_pair_has_strict_syntax_relation_support"

                closure_key = "::".join(sorted([ite_other_id, tg_other_id]))
                closure_id = stable_id("CL", closure_key)
                ite_relation_evidence = strict_relation_lookup.get(
                    ("iTE", ite_pair["pair_key"]), {}
                )
                tg_relation_evidence = strict_relation_lookup.get(
                    ("TG", tg_pair["pair_key"]), {}
                )

                rows.append(
                    {
                        "candidate_id": stable_id(
                            "TC",
                            shared_id,
                            ite_pair["pair_id"],
                            tg_pair["pair_id"],
                        ),
                        "evidence_tier": tier,
                        "evidence_tier_order": tier_order,
                        "evidence_tier_reason": tier_reason,
                        "strict_syntax_supported_side": relation_side,
                        "ite_side_evidence_level": ite_side_level,
                        "tg_side_evidence_level": tg_side_level,
                        "evidence_floor": evidence_floor,
                        "evidence_ceiling": evidence_ceiling,
                        "evidence_grade": evidence_grade,
                        "evidence_grade_order": evidence_grade_order,
                        "shared_global_concept_id": shared_id,
                        "shared_label": shared_label,
                        "shared_category": shared_category,
                        "shared_node_focus_eligible": shared_focus,
                        "other_endpoints_focus_eligible": other_focus,
                        "focus_eligible": shared_focus and other_focus,
                        "shared_ite_document_frequency": layer_concept_df.get(
                            ("iTE", shared_id), 0
                        ),
                        "shared_tg_document_frequency": layer_concept_df.get(
                            ("TG", shared_id), 0
                        ),
                        "shared_ite_incident_pair_degree": len(ite_by_node[shared_id]),
                        "shared_tg_incident_pair_degree": len(tg_by_node[shared_id]),
                        "ite_pair_id": ite_pair["pair_id"],
                        "ite_pair_key": ite_pair["pair_key"],
                        "ite_pair_label": (
                            f"{ite_pair['left_label']} + {ite_pair['right_label']}"
                        ),
                        "ite_other_global_concept_id": ite_other_id,
                        "ite_other_label": ite_other_label,
                        "ite_other_category": ite_other_category,
                        "ite_pair_paper_count": int(ite_pair["paper_count"]),
                        "ite_pair_sentence_count": int(ite_pair["sentence_count"]),
                        "ite_pair_strict_syntax_relation_paper_count": ite_relation_count,
                        "ite_pair_human_confirmed_relation_paper_count": ite_human_relation_count,
                        "ite_strict_relation_ids": ite_relation_evidence.get(
                            "relation_ids", ""
                        ),
                        "ite_human_confirmed_relation_ids": ite_human_relation_evidence.get(
                            "relation_ids", ""
                        ),
                        "ite_authoritative_provenance_fk": ite_pair["pair_id"],
                        "tg_pair_id": tg_pair["pair_id"],
                        "tg_pair_key": tg_pair["pair_key"],
                        "tg_pair_label": (
                            f"{tg_pair['left_label']} + {tg_pair['right_label']}"
                        ),
                        "tg_other_global_concept_id": tg_other_id,
                        "tg_other_label": tg_other_label,
                        "tg_other_category": tg_other_category,
                        "tg_pair_paper_count": int(tg_pair["paper_count"]),
                        "tg_pair_sentence_count": int(tg_pair["sentence_count"]),
                        "tg_pair_strict_syntax_relation_paper_count": tg_relation_count,
                        "tg_pair_human_confirmed_relation_paper_count": tg_human_relation_count,
                        "tg_strict_relation_ids": tg_relation_evidence.get(
                            "relation_ids", ""
                        ),
                        "tg_human_confirmed_relation_ids": tg_human_relation_evidence.get(
                            "relation_ids", ""
                        ),
                        "tg_authoritative_provenance_fk": tg_pair["pair_id"],
                        "closure_group_id": closure_id,
                        "cross_endpoint_pair_key": closure_key,
                        "cross_endpoint_pair": (
                            f"{ite_other_label} + {tg_other_label}"
                        ),
                        "cross_endpoint_status_in_iTE": (
                            "already_observed_in_iTE"
                            if closure_key in ite_pair_keys
                            else "not_observed_in_frozen_iTE_abstract_corpus"
                        ),
                        "cross_endpoint_status_in_TG": (
                            "already_observed_in_TG"
                            if closure_key in tg_pair_keys
                            else "not_observed_in_frozen_TG_abstract_corpus"
                        ),
                        "human_relation_review_status": (
                            "pending" if ite_relation or tg_relation else "not_applicable"
                        ),
                        "cross_paper_compatibility_status": "untested",
                        "cross_endpoint_evaluation_status": "not_tested",
                        "novelty_status": "not_assessed",
                        "novelty_claim_allowed": False,
                        "scientific_claim_status": "retrieval_candidate_only",
                        "candidate_interpretation": (
                            "two_distinct_pairs_share_one_exact_node_no_cross_paper_causality"
                        ),
                    }
                )

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).drop_duplicates("candidate_id")
    frame["minimum_relation_support"] = frame[
        [
            "ite_pair_strict_syntax_relation_paper_count",
            "tg_pair_strict_syntax_relation_paper_count",
        ]
    ].min(axis=1)
    frame["total_relation_support"] = frame[
        [
            "ite_pair_strict_syntax_relation_paper_count",
            "tg_pair_strict_syntax_relation_paper_count",
        ]
    ].sum(axis=1)
    frame["minimum_human_confirmed_relation_support"] = frame[
        [
            "ite_pair_human_confirmed_relation_paper_count",
            "tg_pair_human_confirmed_relation_paper_count",
        ]
    ].min(axis=1)
    frame["total_human_confirmed_relation_support"] = frame[
        [
            "ite_pair_human_confirmed_relation_paper_count",
            "tg_pair_human_confirmed_relation_paper_count",
        ]
    ].sum(axis=1)
    frame["minimum_pair_paper_count"] = frame[
        ["ite_pair_paper_count", "tg_pair_paper_count"]
    ].min(axis=1)
    frame["sum_pair_paper_count"] = frame[
        ["ite_pair_paper_count", "tg_pair_paper_count"]
    ].sum(axis=1)
    frame["minimum_pair_sentence_count"] = frame[
        ["ite_pair_sentence_count", "tg_pair_sentence_count"]
    ].min(axis=1)
    frame["sum_pair_sentence_count"] = frame[
        ["ite_pair_sentence_count", "tg_pair_sentence_count"]
    ].sum(axis=1)
    frame["shared_minimum_document_frequency"] = frame[
        ["shared_ite_document_frequency", "shared_tg_document_frequency"]
    ].min(axis=1)
    frame["closure_path_count"] = frame.groupby("closure_group_id")[
        "candidate_id"
    ].transform("nunique")
    frame["shared_candidate_path_count"] = frame.groupby(
        "shared_global_concept_id"
    )["candidate_id"].transform("nunique")

    support_sort_columns = [
        "shared_global_concept_id",
        "evidence_floor",
        "evidence_ceiling",
        "minimum_human_confirmed_relation_support",
        "total_human_confirmed_relation_support",
        "minimum_relation_support",
        "total_relation_support",
        "minimum_pair_paper_count",
        "sum_pair_paper_count",
        "minimum_pair_sentence_count",
        "sum_pair_sentence_count",
        "ite_pair_id",
        "tg_pair_id",
    ]
    support_sorted = frame.sort_values(
        support_sort_columns,
        ascending=[
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            True,
        ],
    )
    within_rank = support_sorted.groupby("shared_global_concept_id").cumcount() + 1
    frame["within_shared_node_support_rank"] = within_rank.reindex(frame.index).astype(int)
    within_tier_rank = (
        support_sorted.groupby(
            ["shared_global_concept_id", "evidence_tier"]
        ).cumcount()
        + 1
    )
    frame["within_shared_node_tier_support_rank"] = within_tier_rank.reindex(
        frame.index
    ).astype(int)
    frame["focus_within_shared_node_support_rank"] = pd.Series(
        pd.NA, index=frame.index, dtype="Int64"
    )
    frame["focus_within_shared_node_tier_support_rank"] = pd.Series(
        pd.NA, index=frame.index, dtype="Int64"
    )
    focus_sorted = frame[frame["focus_eligible"]].sort_values(
        support_sort_columns,
        ascending=[
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            True,
        ],
    )
    focus_rank = focus_sorted.groupby("shared_global_concept_id").cumcount() + 1
    frame.loc[focus_sorted.index, "focus_within_shared_node_support_rank"] = (
        focus_rank.astype("Int64")
    )
    focus_tier_rank = (
        focus_sorted.groupby(
            ["shared_global_concept_id", "evidence_tier"]
        ).cumcount()
        + 1
    )
    frame.loc[
        focus_sorted.index, "focus_within_shared_node_tier_support_rank"
    ] = focus_tier_rank.astype("Int64")

    # The audit table has no global top-N score.  Stable ordering is based on
    # evidence tier, exact shared-node ID, and pair IDs so that hub frequency or
    # a known paper cannot silently dominate the head of the file.
    frame = frame.sort_values(
        [
            "evidence_grade_order",
            "shared_global_concept_id",
            "ite_pair_id",
            "tg_pair_id",
        ],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)
    frame.insert(0, "audit_order", range(1, len(frame) + 1))
    return frame


def shared_node_evidence_summary(
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    concepts: pd.DataFrame,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    """Return one identity-blind evidence summary row per exact shared pair node."""
    if ite.empty or tg.empty:
        return pd.DataFrame()
    concept_category = (
        concepts.groupby("global_concept_id")["lexical_category"]
        .agg(lambda values: Counter(values).most_common(1)[0][0])
        .to_dict()
    )
    layer_df = (
        concepts[concepts["analysis_layer"].isin(["iTE", "TG"])]
        .groupby(["analysis_layer", "global_concept_id"])["paper_id"]
        .nunique()
        .to_dict()
    )
    labels: dict[str, str] = {}
    for frame in (ite, tg):
        for row in frame.itertuples(index=False):
            labels[row.left_global_concept_id] = row.left_label
            labels[row.right_global_concept_id] = row.right_label
    ite_nodes = set(ite["left_global_concept_id"]) | set(ite["right_global_concept_id"])
    tg_nodes = set(tg["left_global_concept_id"]) | set(tg["right_global_concept_id"])
    candidate_groups = (
        {key: group for key, group in candidates.groupby("shared_global_concept_id")}
        if not candidates.empty
        else {}
    )
    rows: list[dict[str, object]] = []
    for shared_id in sorted(ite_nodes & tg_nodes):
        shared_label = labels.get(shared_id, "")
        shared_category = concept_category.get(shared_id, "")
        ite_incident = ite[
            ite["left_global_concept_id"].eq(shared_id)
            | ite["right_global_concept_id"].eq(shared_id)
        ]
        tg_incident = tg[
            tg["left_global_concept_id"].eq(shared_id)
            | tg["right_global_concept_id"].eq(shared_id)
        ]
        ite_relation_count = int(
            ite_incident["strict_syntax_relation_paper_count"].gt(0).sum()
        )
        tg_relation_count = int(
            tg_incident["strict_syntax_relation_paper_count"].gt(0).sum()
        )
        if ite_relation_count and tg_relation_count:
            raw_node_tier = "A_dual_strict_syntax_candidates"
            raw_tier_order = 1
        elif ite_relation_count or tg_relation_count:
            raw_node_tier = "B_single_strict_syntax_candidate"
            raw_tier_order = 2
        else:
            raw_node_tier = "C_cooccurrence_only"
            raw_tier_order = 3
        group = candidate_groups.get(shared_id)
        tier_counts = (
            group["evidence_tier"].value_counts().to_dict()
            if group is not None
            else {}
        )
        focus_group = group[group["focus_eligible"]] if group is not None else None
        ite_highest_side_level = (
            int(group["ite_side_evidence_level"].max())
            if group is not None and not group.empty
            else (2 if ite_relation_count else 1)
        )
        tg_highest_side_level = (
            int(group["tg_side_evidence_level"].max())
            if group is not None and not group.empty
            else (2 if tg_relation_count else 1)
        )
        if group is None or group.empty:
            all_best_grade = "Q_no_nontrivial_candidate"
            all_best_order = 4
        else:
            all_best_order = int(group["evidence_grade_order"].min())
            all_best_grade = group.loc[
                group["evidence_grade_order"].idxmin(), "evidence_grade"
            ]
        if focus_group is None or focus_group.empty:
            focus_best_grade = "Q_endpoint_quarantine_or_no_path"
            focus_best_order = 4
        else:
            focus_best_order = int(focus_group["evidence_grade_order"].min())
            focus_best_grade = focus_group.loc[
                focus_group["evidence_grade_order"].idxmin(), "evidence_grade"
            ]
        best_group = (
            None
            if group is None or group.empty
            else group.sort_values(
                ["within_shared_node_support_rank", "candidate_id"]
            )
        )
        best_focus_group = (
            None
            if focus_group is None or focus_group.empty
            else focus_group.sort_values(
                ["focus_within_shared_node_support_rank", "candidate_id"]
            )
        )
        rows.append(
            {
                "shared_global_concept_id": shared_id,
                "shared_label": shared_label,
                "shared_category": shared_category,
                "shared_node_focus_eligible": (
                    shared_category in HINGE_SHARED_CATEGORIES
                    and shared_label not in HINGE_GENERIC_LABELS
                ),
                "raw_node_strict_syntax_tier": raw_node_tier,
                "raw_node_strict_syntax_tier_order": raw_tier_order,
                "all_candidate_best_evidence_grade": all_best_grade,
                "all_candidate_best_evidence_grade_order": all_best_order,
                "focus_candidate_best_evidence_grade": focus_best_grade,
                "focus_candidate_best_evidence_grade_order": focus_best_order,
                "shared_ite_document_frequency": layer_df.get(("iTE", shared_id), 0),
                "shared_tg_document_frequency": layer_df.get(("TG", shared_id), 0),
                "ite_incident_pair_count": len(ite_incident),
                "tg_incident_pair_count": len(tg_incident),
                "ite_relation_supported_incident_pair_count": ite_relation_count,
                "tg_relation_supported_incident_pair_count": tg_relation_count,
                "ite_highest_side_evidence_level": ite_highest_side_level,
                "tg_highest_side_evidence_level": tg_highest_side_level,
                "all_candidate_combination_count": 0 if group is None else len(group),
                "focus_node_nontrivial_path_count": (
                    0
                    if group is None
                    or not (
                        shared_category in HINGE_SHARED_CATEGORIES
                        and shared_label not in HINGE_GENERIC_LABELS
                    )
                    else len(group)
                ),
                "focus_candidate_combination_count": (
                    0 if focus_group is None else len(focus_group)
                ),
                "focus_endpoint_quarantine_path_count": (
                    0
                    if group is None
                    or not (
                        shared_category in HINGE_SHARED_CATEGORIES
                        and shared_label not in HINGE_GENERIC_LABELS
                    )
                    else len(group) - (0 if focus_group is None else len(focus_group))
                ),
                "tier_A_candidate_count": tier_counts.get(
                    "A_dual_strict_syntax_candidates", 0
                ),
                "tier_B_candidate_count": tier_counts.get(
                    "B_single_strict_syntax_candidate", 0
                ),
                "tier_C_candidate_count": tier_counts.get("C_cooccurrence_only", 0),
                "best_candidate_id": (
                    "" if best_group is None else best_group.iloc[0]["candidate_id"]
                ),
                "best_focus_candidate_id": (
                    ""
                    if best_focus_group is None
                    else best_focus_group.iloc[0]["candidate_id"]
                ),
                "human_relation_review_status": (
                    "pending" if ite_relation_count or tg_relation_count else "not_applicable"
                ),
                "cross_paper_compatibility_status": "untested",
                "novelty_status": "not_assessed",
                "release_status": (
                    "outside_material_mechanism_focus"
                    if not (
                        shared_category in HINGE_SHARED_CATEGORIES
                        and shared_label not in HINGE_GENERIC_LABELS
                    )
                    else (
                        "eligible"
                        if focus_group is not None and not focus_group.empty
                        else (
                            "endpoint_quarantine"
                            if group is not None and not group.empty
                            else "no_nontrivial_path"
                        )
                    )
                ),
                "release_reason": (
                    "shared_node_outside_declared_material_mechanism_categories"
                    if not (
                        shared_category in HINGE_SHARED_CATEGORIES
                        and shared_label not in HINGE_GENERIC_LABELS
                    )
                    else (
                        "at_least_one_distinct_pair_path_passes_endpoint_gate"
                        if focus_group is not None and not focus_group.empty
                        else (
                            "all_distinct_paths_fail_other_endpoint_category_or_generic_gate"
                            if group is not None and not group.empty
                            else "only_same_pair_or_same_other_endpoint_paths_exist"
                        )
                    )
                ),
            }
        )
    frame = pd.DataFrame(rows)
    frame["shared_minimum_document_frequency"] = frame[
        ["shared_ite_document_frequency", "shared_tg_document_frequency"]
    ].min(axis=1)
    # Stable ID order keeps this an audit inventory rather than a pseudo-score.
    frame = frame.sort_values("shared_global_concept_id").reset_index(drop=True)
    frame.insert(0, "node_audit_order", range(1, len(frame) + 1))
    return frame


def build_balanced_focus_review_queue(
    candidates: pd.DataFrame,
    cooccurrence_paths_per_shared_node: int = 3,
) -> pd.DataFrame:
    """Build an identity-blind, node-balanced queue from the focus view.

    Every A/B path is retained.  C is sampled within each exact shared node,
    never by a global top-N that would mostly return high-degree hubs.
    """
    if candidates.empty:
        return pd.DataFrame()
    focus = candidates[candidates["focus_eligible"]].copy()
    if focus.empty:
        return focus
    relation_backed = focus["evidence_tier"].isin(
        ["A_dual_strict_syntax_candidates", "B_single_strict_syntax_candidate"]
    )
    balanced_c = focus["evidence_tier"].eq("C_cooccurrence_only") & focus[
        "focus_within_shared_node_tier_support_rank"
    ].le(cooccurrence_paths_per_shared_node)
    queue = focus[relation_backed | balanced_c].copy()
    queue["round_robin_round"] = queue[
        "focus_within_shared_node_tier_support_rank"
    ].astype("Int64")
    queue["review_selection_reason"] = queue["evidence_tier"].map(
        {
            "A_dual_strict_syntax_candidates": "retain_all_dual_strict_syntax_paths",
            "B_single_strict_syntax_candidate": "retain_all_single_strict_syntax_paths",
            "C_cooccurrence_only": (
                f"within_shared_node_top_{cooccurrence_paths_per_shared_node}_cooccurrence_paths"
            ),
        }
    )
    queue["selection_policy_id"] = (
        "identity_blind_v1_all_A_B_plus_C_round_robin_"
        f"{cooccurrence_paths_per_shared_node}_per_shared_node"
    )
    queue["review_selected"] = True
    queue = queue.sort_values(
        [
            "evidence_tier_order",
            "round_robin_round",
            "shared_global_concept_id",
            "candidate_id",
        ]
    ).reset_index(drop=True)
    queue.insert(0, "review_queue_order", range(1, len(queue) + 1))
    return queue


def build_relation_incident_review_queue(
    candidates: pd.DataFrame,
    relations: pd.DataFrame,
    papers: pd.DataFrame,
) -> pd.DataFrame:
    """Return atomic original-abstract evidence for every focus A/B relation edge."""
    if candidates.empty or relations.empty:
        return pd.DataFrame()
    focus_relation_paths = candidates[
        candidates["focus_eligible"]
        & candidates["evidence_tier"].isin(
            ["A_dual_strict_syntax_candidates", "B_single_strict_syntax_candidate"]
        )
    ]
    if focus_relation_paths.empty:
        return pd.DataFrame()

    incidence_paths: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    incidence_tiers: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for row in focus_relation_paths.itertuples(index=False):
        if int(row.ite_pair_strict_syntax_relation_paper_count) > 0:
            key = (
                "iTE",
                row.shared_global_concept_id,
                row.ite_pair_id,
                row.ite_pair_key,
            )
            incidence_paths[key].add(row.candidate_id)
            incidence_tiers[key].add(row.evidence_tier)
        if int(row.tg_pair_strict_syntax_relation_paper_count) > 0:
            key = (
                "TG",
                row.shared_global_concept_id,
                row.tg_pair_id,
                row.tg_pair_key,
            )
            incidence_paths[key].add(row.candidate_id)
            incidence_tiers[key].add(row.evidence_tier)

    strict_relations = relations[relations["strict_syntax_eligible"]].copy()
    strict_relations["pair_key"] = strict_relations.apply(
        lambda row: "::".join(
            sorted(
                [
                    row["source_global_concept_id"],
                    row["target_global_concept_id"],
                ]
            )
        ),
        axis=1,
    )
    relation_groups = {
        key: group
        for key, group in strict_relations.groupby(
            ["analysis_layer", "pair_key"], sort=False
        )
    }
    paper_abstract = papers.set_index("paper_id")["abstract"].to_dict()
    rows: list[dict[str, object]] = []
    for incidence_key in sorted(incidence_paths):
        layer, shared_id, pair_id, pair_key = incidence_key
        group = relation_groups.get((layer, pair_key))
        if group is None:
            continue
        for relation in group.itertuples(index=False):
            rows.append(
                {
                    "relation_incidence_id": stable_id(
                        "RI", layer, shared_id, pair_id, relation.relation_id
                    ),
                    "analysis_layer": layer,
                    "shared_global_concept_id": shared_id,
                    "shared_label": next(
                        (
                            row.shared_label
                            for row in focus_relation_paths.itertuples(index=False)
                            if row.shared_global_concept_id == shared_id
                        ),
                        "",
                    ),
                    "pair_id": pair_id,
                    "pair_key": pair_key,
                    "relation_id": relation.relation_id,
                    "paper_id": relation.paper_id,
                    "title": relation.title,
                    "doi": relation.doi,
                    "source_surface": relation.source_surface,
                    "source_normalized_label": relation.source_normalized_label,
                    "predicate_surface": relation.predicate_surface,
                    "predicate_normalized": relation.predicate_normalized,
                    "target_surface": relation.target_surface,
                    "target_normalized_label": relation.target_normalized_label,
                    "evidence_sentence": relation.evidence_sentence,
                    "original_abstract": paper_abstract.get(relation.paper_id, ""),
                    "source_is_shared_node": (
                        relation.source_global_concept_id == shared_id
                    ),
                    "target_is_shared_node": (
                        relation.target_global_concept_id == shared_id
                    ),
                    "candidate_path_count": len(incidence_paths[incidence_key]),
                    "candidate_ids": "; ".join(sorted(incidence_paths[incidence_key])),
                    "candidate_evidence_tiers": "; ".join(
                        sorted(incidence_tiers[incidence_key])
                    ),
                    "machine_strict_syntax_eligible": True,
                    "human_semantic_review": "pending",
                    "cross_paper_compatibility_status": "untested",
                }
            )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).drop_duplicates("relation_incidence_id")
    frame = frame.sort_values(
        ["analysis_layer", "shared_global_concept_id", "paper_id", "relation_id"]
    ).reset_index(drop=True)
    frame.insert(0, "review_order", range(1, len(frame) + 1))
    return frame


def audit_tiered_candidate_layer(
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    candidates: pd.DataFrame,
    node_summary: pd.DataFrame,
    review_queue: pd.DataFrame,
) -> dict[str, object]:
    """Mechanical checks for completeness, tier logic, and identity isolation."""
    ite_by_id = ite.set_index("pair_id").to_dict("index")
    tg_by_id = tg.set_index("pair_id").to_dict("index")
    ite_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    tg_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in ite.to_dict("records"):
        ite_by_node[record["left_global_concept_id"]].append(record)
        ite_by_node[record["right_global_concept_id"]].append(record)
    for record in tg.to_dict("records"):
        tg_by_node[record["left_global_concept_id"]].append(record)
        tg_by_node[record["right_global_concept_id"]].append(record)

    expected_shared_nodes = set(ite_by_node) & set(tg_by_node)
    expected_candidate_count = 0
    for shared_id in expected_shared_nodes:
        for ite_pair in ite_by_node[shared_id]:
            for tg_pair in tg_by_node[shared_id]:
                if ite_pair["pair_key"] == tg_pair["pair_key"]:
                    continue
                ite_other = (
                    ite_pair["right_global_concept_id"]
                    if ite_pair["left_global_concept_id"] == shared_id
                    else ite_pair["left_global_concept_id"]
                )
                tg_other = (
                    tg_pair["right_global_concept_id"]
                    if tg_pair["left_global_concept_id"] == shared_id
                    else tg_pair["left_global_concept_id"]
                )
                if ite_other != tg_other:
                    expected_candidate_count += 1

    tier_logic_failures = 0
    grade_logic_failures = 0
    shared_endpoint_failures = 0
    direct_pair_leakage = 0
    same_other_endpoint_failures = 0
    missing_relation_evidence_ids = 0
    for row in candidates.itertuples(index=False):
        ite_pair = ite_by_id[row.ite_pair_id]
        tg_pair = tg_by_id[row.tg_pair_id]
        if row.shared_global_concept_id not in {
            ite_pair["left_global_concept_id"],
            ite_pair["right_global_concept_id"],
        } or row.shared_global_concept_id not in {
            tg_pair["left_global_concept_id"],
            tg_pair["right_global_concept_id"],
        }:
            shared_endpoint_failures += 1
        if ite_pair["pair_key"] == tg_pair["pair_key"]:
            direct_pair_leakage += 1
        if row.ite_other_global_concept_id == row.tg_other_global_concept_id:
            same_other_endpoint_failures += 1
        ite_relation = int(
            row.ite_pair_strict_syntax_relation_paper_count
        ) > 0
        tg_relation = int(row.tg_pair_strict_syntax_relation_paper_count) > 0
        expected_tier = (
            "A_dual_strict_syntax_candidates"
            if ite_relation and tg_relation
            else (
                "B_single_strict_syntax_candidate"
                if ite_relation or tg_relation
                else "C_cooccurrence_only"
            )
        )
        if row.evidence_tier != expected_tier:
            tier_logic_failures += 1
        expected_ite_level = (
            3
            if int(row.ite_pair_human_confirmed_relation_paper_count) > 0
            else (2 if ite_relation else 1)
        )
        expected_tg_level = (
            3
            if int(row.tg_pair_human_confirmed_relation_paper_count) > 0
            else (2 if tg_relation else 1)
        )
        expected_floor = min(expected_ite_level, expected_tg_level)
        expected_ceiling = max(expected_ite_level, expected_tg_level)
        expected_grade = (
            "G3_dual_human_confirmed_relations"
            if expected_floor >= 3
            else (
                "G2_dual_strict_syntax_candidates"
                if expected_floor >= 2
                else (
                    "G1_single_strict_syntax_candidate"
                    if expected_ceiling >= 2
                    else "G0_cooccurrence_only"
                )
            )
        )
        if not (
            row.ite_side_evidence_level == expected_ite_level
            and row.tg_side_evidence_level == expected_tg_level
            and row.evidence_floor == expected_floor
            and row.evidence_ceiling == expected_ceiling
            and row.evidence_grade == expected_grade
        ):
            grade_logic_failures += 1
        if ite_relation and not clean(row.ite_strict_relation_ids):
            missing_relation_evidence_ids += 1
        if tg_relation and not clean(row.tg_strict_relation_ids):
            missing_relation_evidence_ids += 1

    focus = candidates[candidates["focus_eligible"]]
    expected_queue_ids = set(
        focus[
            focus["evidence_tier"].isin(
                [
                    "A_dual_strict_syntax_candidates",
                    "B_single_strict_syntax_candidate",
                ]
            )
            | (
                focus["evidence_tier"].eq("C_cooccurrence_only")
                & focus["focus_within_shared_node_tier_support_rank"].le(3)
            )
        ]["candidate_id"]
    )
    actual_queue_ids = set(review_queue["candidate_id"]) if not review_queue.empty else set()
    forbidden_identity_columns = [
        column
        for column in candidates.columns
        if any(token in column.lower() for token in ["known_case", "control", "program", "curated"])
    ]
    checks = {
        "full_candidate_table_is_untruncated": len(candidates)
        == expected_candidate_count,
        "candidate_ids_are_unique": candidates["candidate_id"].is_unique,
        "every_candidate_shared_node_is_an_endpoint_on_both_sides": shared_endpoint_failures
        == 0,
        "direct_pair_overlaps_are_separate": direct_pair_leakage == 0,
        "candidate_other_endpoints_are_distinct": same_other_endpoint_failures == 0,
        "tier_assignment_matches_pair_relation_support": tier_logic_failures == 0,
        "evidence_grade_matches_strict_and_human_support": grade_logic_failures == 0,
        "relation_backed_paths_have_atomic_relation_ids": missing_relation_evidence_ids
        == 0,
        "shared_node_inventory_is_complete": len(node_summary)
        == len(expected_shared_nodes),
        "shared_node_inventory_ids_are_unique": node_summary[
            "shared_global_concept_id"
        ].is_unique,
        "balanced_review_queue_matches_frozen_rule": actual_queue_ids
        == expected_queue_ids,
        "known_case_or_control_identity_absent_from_candidate_schema": not forbidden_identity_columns,
        "novelty_is_not_assessed_in_candidate_layer": candidates[
            "novelty_status"
        ].eq("not_assessed").all(),
        "compatibility_is_not_asserted_in_candidate_layer": candidates[
            "cross_paper_compatibility_status"
        ].eq("untested").all(),
    }
    failure_counts = {
        "candidate_count_difference": len(candidates) - expected_candidate_count,
        "duplicate_candidate_ids": int(candidates["candidate_id"].duplicated().sum()),
        "shared_endpoint_failures": shared_endpoint_failures,
        "direct_pair_leakage": direct_pair_leakage,
        "same_other_endpoint_failures": same_other_endpoint_failures,
        "tier_logic_failures": tier_logic_failures,
        "grade_logic_failures": grade_logic_failures,
        "missing_relation_evidence_ids": missing_relation_evidence_ids,
        "shared_node_count_difference": len(node_summary) - len(expected_shared_nodes),
        "balanced_review_queue_symmetric_difference": len(
            actual_queue_ids.symmetric_difference(expected_queue_ids)
        ),
        "forbidden_identity_columns": forbidden_identity_columns,
    }
    return {"checks": checks, "failure_counts": failure_counts}


def audit_pair_support_evidence(
    pair_evidence: pd.DataFrame,
    sentence_pairs: pd.DataFrame,
    relations: pd.DataFrame,
    papers: pd.DataFrame,
    ite_pairs: pd.DataFrame,
    tg_pairs: pd.DataFrame,
    candidates: pd.DataFrame,
) -> dict[str, object]:
    """Verify every normalized pair-evidence foreign key and bound source tuple."""
    pair_bank = pd.concat([ite_pairs, tg_pairs], ignore_index=True)
    valid_pair_ids = set(pair_bank["pair_id"])
    valid_sentence_pair_ids = set(sentence_pairs["sentence_pair_id"])
    valid_relation_ids = set(relations["relation_id"]) if not relations.empty else set()
    paper_lookup = papers.set_index("paper_id").to_dict("index")
    sentence_lookup = sentence_pairs.set_index("sentence_pair_id").to_dict("index")
    relation_lookup = (
        relations.set_index("relation_id").to_dict("index")
        if not relations.empty
        else {}
    )

    pair_fk_failures = 0
    sentence_fk_failures = 0
    relation_fk_failures = 0
    paper_tuple_failures = 0
    sentence_tuple_failures = 0
    relation_tuple_failures = 0
    for row in pair_evidence.itertuples(index=False):
        if row.pair_id not in valid_pair_ids:
            pair_fk_failures += 1
        if row.sentence_pair_id not in valid_sentence_pair_ids:
            sentence_fk_failures += 1
            continue
        paper = paper_lookup.get(row.paper_id)
        if paper is None or not (
            clean(row.doi) == clean(paper["doi"])
            and clean(row.title) == clean(paper["title"])
            and clean(row.source_record_ids) == clean(paper["source_record_ids"])
            and clean(row.abstract_sha256) == clean(paper["abstract_sha256"])
        ):
            paper_tuple_failures += 1
        sentence = sentence_lookup[row.sentence_pair_id]
        if not (
            row.paper_id == sentence["paper_id"]
            and row.analysis_layer == sentence["analysis_layer"]
            and row.pair_key == sentence["pair_key"]
            and row.sentence_id == sentence["sentence_id"]
            and row.evidence_sentence == sentence["evidence_sentence"]
        ):
            sentence_tuple_failures += 1
        if clean(row.relation_id):
            if row.relation_id not in valid_relation_ids:
                relation_fk_failures += 1
                continue
            relation = relation_lookup[row.relation_id]
            relation_pair_key = "::".join(
                sorted(
                    [
                        relation["source_global_concept_id"],
                        relation["target_global_concept_id"],
                    ]
                )
            )
            if not (
                row.paper_id == relation["paper_id"]
                and row.analysis_layer == relation["analysis_layer"]
                and row.sentence_id == relation["sentence_id"]
                and row.pair_key == relation_pair_key
                and bool(row.strict_syntax_eligible)
                == bool(relation["strict_syntax_eligible"])
                and bool(row.graph_eligible) == bool(relation["graph_eligible"])
            ):
                relation_tuple_failures += 1

    observed_strict_counts = (
        pair_evidence[pair_evidence["strict_syntax_eligible"]]
        .groupby("pair_id")["paper_id"]
        .nunique()
        .to_dict()
    )
    strict_count_failures = sum(
        int(row.strict_syntax_relation_paper_count)
        != int(observed_strict_counts.get(row.pair_id, 0))
        for row in pair_bank.itertuples(index=False)
    )
    candidate_pair_fk_failures = int(
        (~candidates["ite_pair_id"].isin(valid_pair_ids)).sum()
        + (~candidates["tg_pair_id"].isin(valid_pair_ids)).sum()
    )
    missing_pair_evidence = len(valid_pair_ids - set(pair_evidence["pair_id"]))
    checks = {
        "pair_evidence_ids_are_unique": pair_evidence["pair_evidence_id"].is_unique,
        "every_pair_bank_row_has_atomic_evidence": missing_pair_evidence == 0,
        "all_pair_evidence_pair_foreign_keys_resolve": pair_fk_failures == 0,
        "all_sentence_pair_foreign_keys_resolve": sentence_fk_failures == 0,
        "all_relation_foreign_keys_resolve": relation_fk_failures == 0,
        "paper_doi_title_source_hash_are_bound_in_one_tuple": paper_tuple_failures == 0,
        "sentence_evidence_tuple_matches_source_row": sentence_tuple_failures == 0,
        "relation_evidence_tuple_matches_source_row": relation_tuple_failures == 0,
        "pair_strict_support_counts_reconstruct_from_atomic_evidence": strict_count_failures
        == 0,
        "candidate_pair_foreign_keys_resolve": candidate_pair_fk_failures == 0,
    }
    failure_counts = {
        "duplicate_pair_evidence_ids": int(
            pair_evidence["pair_evidence_id"].duplicated().sum()
        ),
        "missing_pair_evidence": missing_pair_evidence,
        "pair_fk_failures": pair_fk_failures,
        "sentence_fk_failures": sentence_fk_failures,
        "relation_fk_failures": relation_fk_failures,
        "paper_tuple_failures": paper_tuple_failures,
        "sentence_tuple_failures": sentence_tuple_failures,
        "relation_tuple_failures": relation_tuple_failures,
        "strict_count_failures": strict_count_failures,
        "candidate_pair_fk_failures": candidate_pair_fk_failures,
    }
    return {"checks": checks, "failure_counts": failure_counts}


def hinge_candidates(
    ite: pd.DataFrame,
    tg: pd.DataFrame,
    concepts: pd.DataFrame,
    per_node_limit: int = 20,
) -> pd.DataFrame:
    if ite.empty or tg.empty:
        return pd.DataFrame()
    layer_concept_df = (
        concepts[concepts["analysis_layer"].isin(["iTE", "TG"])]
        .groupby(["analysis_layer", "global_concept_id"])["paper_id"]
        .nunique()
        .to_dict()
    )
    concept_category = (
        concepts.groupby("global_concept_id")["lexical_category"]
        .agg(lambda values: Counter(values).most_common(1)[0][0])
        .to_dict()
    )
    ite_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    tg_by_node: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in ite.to_dict("records"):
        ite_by_node[record["left_global_concept_id"]].append(record)
        ite_by_node[record["right_global_concept_id"]].append(record)
    for record in tg.to_dict("records"):
        tg_by_node[record["left_global_concept_id"]].append(record)
        tg_by_node[record["right_global_concept_id"]].append(record)

    tg_pair_keys = set(tg["pair_key"])
    rows: list[dict[str, object]] = []
    for shared_id in sorted(set(ite_by_node) & set(tg_by_node)):
        shared_label = (
            ite_by_node[shared_id][0]["left_label"]
            if ite_by_node[shared_id][0]["left_global_concept_id"] == shared_id
            else ite_by_node[shared_id][0]["right_label"]
        )
        shared_category = concept_category.get(shared_id, "")
        if (
            shared_category not in HINGE_SHARED_CATEGORIES
            or shared_label in HINGE_GENERIC_LABELS
        ):
            continue
        ite_pairs = sorted(
            [
                row
                for row in ite_by_node[shared_id]
                if int(row["strict_syntax_relation_paper_count"]) > 0
            ],
            key=lambda row: (
                row["strict_syntax_relation_paper_count"],
                row["paper_count"],
                row["sentence_count"],
            ),
            reverse=True,
        )[:per_node_limit]
        tg_pairs = sorted(
            [
                row
                for row in tg_by_node[shared_id]
                if int(row["strict_syntax_relation_paper_count"]) > 0
            ],
            key=lambda row: (
                row["strict_syntax_relation_paper_count"],
                row["paper_count"],
                row["sentence_count"],
            ),
            reverse=True,
        )[:per_node_limit]
        for ite_pair in ite_pairs:
            for tg_pair in tg_pairs:
                if ite_pair["pair_key"] == tg_pair["pair_key"]:
                    continue
                ite_other_id = (
                    ite_pair["right_global_concept_id"]
                    if ite_pair["left_global_concept_id"] == shared_id
                    else ite_pair["left_global_concept_id"]
                )
                ite_other_label = (
                    ite_pair["right_label"]
                    if ite_pair["left_global_concept_id"] == shared_id
                    else ite_pair["left_label"]
                )
                tg_other_id = (
                    tg_pair["right_global_concept_id"]
                    if tg_pair["left_global_concept_id"] == shared_id
                    else tg_pair["left_global_concept_id"]
                )
                tg_other_label = (
                    tg_pair["right_label"]
                    if tg_pair["left_global_concept_id"] == shared_id
                    else tg_pair["left_label"]
                )
                if ite_other_id == tg_other_id:
                    continue
                ite_other_category = concept_category.get(ite_other_id, "")
                tg_other_category = concept_category.get(tg_other_id, "")
                if (
                    ite_other_category not in HINGE_OTHER_CATEGORIES
                    or tg_other_category not in HINGE_OTHER_CATEGORIES
                    or ite_other_label in HINGE_GENERIC_LABELS
                    or tg_other_label in HINGE_GENERIC_LABELS
                ):
                    continue
                closure_key = "::".join(sorted([ite_other_id, tg_other_id]))
                ite_asserted = int(ite_pair["strict_syntax_relation_paper_count"]) > 0
                tg_asserted = int(tg_pair["strict_syntax_relation_paper_count"]) > 0
                shared_ite_df = layer_concept_df.get(("iTE", shared_id), 0)
                shared_tg_df = layer_concept_df.get(("TG", shared_id), 0)
                rows.append(
                    {
                        "hinge_id": stable_id(
                            "XH", shared_id, ite_pair["pair_id"], tg_pair["pair_id"]
                        ),
                        "shared_global_concept_id": shared_id,
                        "shared_label": shared_label,
                        "shared_category": shared_category,
                        "shared_ite_document_frequency": shared_ite_df,
                        "shared_tg_document_frequency": shared_tg_df,
                        "shared_total_document_frequency": shared_ite_df + shared_tg_df,
                        "ite_pair_id": ite_pair["pair_id"],
                        "ite_pair_label": f"{ite_pair['left_label']} + {ite_pair['right_label']}",
                        "ite_other_global_concept_id": ite_other_id,
                        "ite_other_label": ite_other_label,
                        "ite_other_category": ite_other_category,
                        "ite_pair_paper_count": ite_pair["paper_count"],
                        "ite_pair_strict_syntax_relation_paper_count": ite_pair[
                            "strict_syntax_relation_paper_count"
                        ],
                        "ite_supporting_paper_ids": ite_pair["supporting_paper_ids"],
                        "ite_example_evidence_sentence": ite_pair[
                            "example_evidence_sentence"
                        ],
                        "tg_pair_id": tg_pair["pair_id"],
                        "tg_pair_label": f"{tg_pair['left_label']} + {tg_pair['right_label']}",
                        "tg_other_global_concept_id": tg_other_id,
                        "tg_other_label": tg_other_label,
                        "tg_other_category": tg_other_category,
                        "tg_pair_paper_count": tg_pair["paper_count"],
                        "tg_pair_strict_syntax_relation_paper_count": tg_pair[
                            "strict_syntax_relation_paper_count"
                        ],
                        "tg_supporting_paper_ids": tg_pair["supporting_paper_ids"],
                        "tg_example_evidence_sentence": tg_pair[
                            "example_evidence_sentence"
                        ],
                        "both_pairs_have_strict_syntax_support": ite_asserted
                        and tg_asserted,
                        "at_least_one_pair_has_strict_syntax_support": ite_asserted
                        or tg_asserted,
                        "cross_endpoint_pair": f"{ite_other_label} + {tg_other_label}",
                        "cross_endpoint_status_in_TG": (
                            "already_observed_in_TG"
                            if closure_key in tg_pair_keys
                            else "not_observed_in_frozen_TG_abstract_corpus"
                        ),
                        "candidate_interpretation": "retrieval_only_not_scientific_compatibility_or_causality",
                        "evidence_scope": "two_relation_backed_pairs_share_exact_extractive_concept_cross_endpoint_link_untested",
                    }
                )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).drop_duplicates("hinge_id")
    frame["minimum_pair_paper_count"] = frame[
        ["ite_pair_paper_count", "tg_pair_paper_count"]
    ].min(axis=1)
    frame["sum_pair_paper_count"] = frame[
        ["ite_pair_paper_count", "tg_pair_paper_count"]
    ].sum(axis=1)
    frame["shared_minimum_document_frequency"] = frame[
        ["shared_ite_document_frequency", "shared_tg_document_frequency"]
    ].min(axis=1)
    frame = frame.sort_values(
        [
            "both_pairs_have_strict_syntax_support",
            "at_least_one_pair_has_strict_syntax_support",
            "minimum_pair_paper_count",
            "sum_pair_paper_count",
            "shared_minimum_document_frequency",
            "shared_total_document_frequency",
            "hinge_id",
        ],
        ascending=[False, False, False, False, False, False, True],
    ).reset_index(drop=True)
    frame.insert(0, "evidence_rank", range(1, len(frame) + 1))
    return frame


def build_paper_audit(
    papers: pd.DataFrame,
    occurrences: pd.DataFrame,
    primary: pd.DataFrame,
    relations: pd.DataFrame,
) -> pd.DataFrame:
    concept_counts = primary.groupby("paper_id").size() if not primary.empty else pd.Series(dtype=int)
    occurrence_counts = occurrences.groupby("paper_id").size() if not occurrences.empty else pd.Series(dtype=int)
    relation_counts = relations.groupby("paper_id").size() if not relations.empty else pd.Series(dtype=int)
    syntax_candidate_counts = (
        relations[relations["strict_syntax_eligible"]].groupby("paper_id").size()
        if not relations.empty
        else pd.Series(dtype=int)
    )
    invalid_spans = (
        occurrences[~occurrences["span_exact_match"]].groupby("paper_id").size()
        if not occurrences.empty
        else pd.Series(dtype=int)
    )
    audit = papers.copy()
    audit["selected_concept_count"] = audit["paper_id"].map(concept_counts).fillna(0).astype(int)
    audit["concept_occurrence_count"] = audit["paper_id"].map(occurrence_counts).fillna(0).astype(int)
    audit["explicit_relation_count"] = audit["paper_id"].map(relation_counts).fillna(0).astype(int)
    audit["strict_syntax_candidate_count"] = (
        audit["paper_id"].map(syntax_candidate_counts).fillna(0).astype(int)
    )
    audit["invalid_span_count"] = audit["paper_id"].map(invalid_spans).fillna(0).astype(int)
    audit["all_concept_spans_exact"] = audit["invalid_span_count"].eq(0)
    audit["review_status"] = audit.apply(
        lambda row: (
            "missing_abstract_requires_recovery"
            if not clean(row["abstract"])
            else (
                "direct_scope_low_concept_coverage"
                if row["analysis_layer"] in {"iTE", "TG"}
                and row["selected_concept_count"] < 3
                else (
                    "invalid_span_blocker"
                    if row["invalid_span_count"] > 0
                    else "ready_for_manual_abstract_check"
                )
            )
        ),
        axis=1,
    )
    return audit


def build_abstract_check_queue(
    paper_audit: pd.DataFrame,
    concepts: pd.DataFrame,
    relations: pd.DataFrame,
) -> pd.DataFrame:
    """Create one human-review row per paper with all extractive evidence attached."""
    concept_evidence: dict[str, str] = {}
    if not concepts.empty:
        for paper_id, group in concepts.groupby("paper_id", sort=False):
            entries = []
            for row in group.sort_values(["char_start", "char_end"]).itertuples(index=False):
                entries.append(
                    f"{row.surface_text} -> {row.normalized_label} "
                    f"[{row.lexical_category}; {row.char_start}:{row.char_end}]"
                )
            concept_evidence[paper_id] = " || ".join(entries)

    relation_evidence: dict[str, str] = {}
    if not relations.empty:
        for paper_id, group in relations.groupby("paper_id", sort=False):
            entries = []
            for row in group.sort_values(
                ["sentence_id", "predicate_char_start"]
            ).itertuples(index=False):
                entries.append(
                    f"{row.source_surface} --{row.predicate_surface}--> "
                    f"{row.target_surface} [{row.assertion_status}; "
                    f"sentence {row.sentence_id}]"
                )
            relation_evidence[paper_id] = " || ".join(entries)

    queue = paper_audit.copy()
    queue["concept_evidence"] = queue["paper_id"].map(concept_evidence).fillna("")
    queue["relation_evidence"] = queue["paper_id"].map(relation_evidence).fillna("")
    queue["automated_evidence_check"] = queue.apply(
        lambda row: (
            "missing_abstract"
            if not clean(row["abstract"])
            else (
                "blocker"
                if int(row["invalid_span_count"]) > 0
                else "exact_spans_verified"
            )
        ),
        axis=1,
    )
    queue["human_semantic_review"] = queue["abstract"].map(
        lambda value: "pending" if clean(value) else "blocked_missing_abstract"
    )
    queue["review_priority"] = queue.apply(
        lambda row: (
            "1_direct_with_relation"
            if row["analysis_layer"] in {"iTE", "TG"}
            and int(row["explicit_relation_count"]) > 0
            else (
                "2_direct_without_relation"
                if row["analysis_layer"] in {"iTE", "TG"}
                else (
                    "3_holdout"
                    if clean(row["abstract"])
                    else "4_missing_abstract"
                )
            )
        ),
        axis=1,
    )
    return queue.sort_values(["review_priority", "paper_id"]).reset_index(drop=True)


def build_qa_report(
    papers: pd.DataFrame,
    occurrences: pd.DataFrame,
    relations: pd.DataFrame,
    sentence_pairs: pd.DataFrame,
    ite_pairs: pd.DataFrame,
    tg_pairs: pd.DataFrame,
    overlaps: pd.DataFrame,
) -> dict[str, object]:
    paper_lookup = papers.set_index("paper_id")

    concept_span_failures = 0
    normalization_failures = 0
    semantic_addition_flag_failures = 0
    for row in occurrences.itertuples(index=False):
        abstract = str(paper_lookup.loc[row.paper_id, "abstract"])
        if abstract[int(row.char_start) : int(row.char_end)] != row.surface_text:
            concept_span_failures += 1
        regenerated, _ = normalized_label(row.surface_text)
        if regenerated != row.normalized_label:
            normalization_failures += 1
        if bool(row.semantic_addition_allowed):
            semantic_addition_flag_failures += 1

    relation_span_failures = 0
    relation_order_failures = 0
    graph_contract_failures = 0
    for row in relations.itertuples(index=False):
        abstract = str(paper_lookup.loc[row.paper_id, "abstract"])
        span_checks = [
            abstract[int(row.sentence_char_start) : int(row.sentence_char_end)]
            == row.evidence_sentence,
            abstract[int(row.source_char_start) : int(row.source_char_end)]
            == row.source_surface,
            abstract[int(row.predicate_char_start) : int(row.predicate_char_end)]
            == row.predicate_surface,
            abstract[int(row.target_char_start) : int(row.target_char_end)]
            == row.target_surface,
        ]
        if not all(span_checks):
            relation_span_failures += 1
        if not (
            int(row.sentence_char_start)
            <= int(row.source_char_start)
            < int(row.source_char_end)
            <= int(row.predicate_char_start)
            < int(row.predicate_char_end)
            <= int(row.target_char_start)
            < int(row.target_char_end)
            <= int(row.sentence_char_end)
        ):
            relation_order_failures += 1
        if bool(row.strict_syntax_eligible) and not (
            row.assertion_status == "observed_assertion"
            and row.analysis_layer in {"iTE", "TG"}
            and not clean(row.risk_reasons)
        ):
            graph_contract_failures += 1

    sentence_pair_failures = 0
    for row in sentence_pairs.itertuples(index=False):
        abstract = str(paper_lookup.loc[row.paper_id, "abstract"])
        expected_key = "::".join(
            sorted([row.left_global_concept_id, row.right_global_concept_id])
        )
        if not (
            abstract[int(row.left_char_start) : int(row.left_char_end)]
            == row.left_surface
            and abstract[int(row.right_char_start) : int(row.right_char_end)]
            == row.right_surface
            and row.left_surface in row.evidence_sentence
            and row.right_surface in row.evidence_sentence
            and row.pair_key == expected_key
            and row.analysis_layer in {"iTE", "TG"}
        ):
            sentence_pair_failures += 1

    layer_node_cross_domain_failures = int(
        (
            occurrences.groupby("layer_node_id")["analysis_layer"].nunique() > 1
        ).sum()
    )
    global_label_failures = int(
        (
            occurrences.groupby("global_concept_id")["normalized_label"].nunique()
            > 1
        ).sum()
    )
    overlap_assigned_to_direct = int(
        (
            papers["overlap_source_record"]
            & papers["analysis_layer"].isin(["iTE", "TG"])
        ).sum()
    )
    alphabetic_acronym_failures = int(
        occurrences.apply(
            lambda row: row["lexical_category"] == "literal_formula"
            and bool(re.fullmatch(r"[A-Z]{2,8}", str(row["surface_text"]))),
            axis=1,
        ).sum()
    )
    hyphenated_abbreviation_failures = int(
        occurrences.apply(
            lambda row: row["extractor_pattern"] == "generic_hyphenated_keyword"
            and any(
                len(part) < 3 or (len(part) > 1 and part.isupper())
                for part in str(row["surface_text"]).split("-")
            ),
            axis=1,
        ).sum()
    )
    cross_paper_selection_failures = int(
        occurrences["cross_paper_frequency_used_for_selection"].astype(bool).sum()
    )

    checks = {
        "all_concept_spans_exact": concept_span_failures == 0,
        "normalization_reproducible_from_surface": normalization_failures == 0,
        "semantic_addition_disabled_for_every_occurrence": semantic_addition_flag_failures
        == 0,
        "all_relation_spans_exact": relation_span_failures == 0,
        "all_relations_ordered_within_one_sentence": relation_order_failures == 0,
        "strict_syntax_gate_contains_only_direct_observed_assertions": graph_contract_failures
        == 0,
        "unreviewed_relations_are_not_inserted_into_graph": not bool(
            relations["graph_eligible"].any()
        ),
        "all_sentence_pairs_trace_to_one_abstract_sentence": sentence_pair_failures == 0,
        "layer_node_ids_are_domain_isolated": layer_node_cross_domain_failures == 0,
        "global_ids_map_to_one_normalized_surface": global_label_failures == 0,
        "overlap_source_papers_excluded_from_both_strict_banks": overlap_assigned_to_direct
        == 0,
        "alphabetic_abbreviations_not_extracted_as_formulae": alphabetic_acronym_failures == 0,
        "hyphenated_abbreviations_not_selected_as_keywords": hyphenated_abbreviation_failures
        == 0,
        "concept_selection_is_single_abstract_only": cross_paper_selection_failures
        == 0,
    }
    failure_counts = {
        "concept_span_failures": concept_span_failures,
        "normalization_failures": normalization_failures,
        "semantic_addition_flag_failures": semantic_addition_flag_failures,
        "relation_span_failures": relation_span_failures,
        "relation_order_failures": relation_order_failures,
        "graph_contract_failures": graph_contract_failures,
        "sentence_pair_failures": sentence_pair_failures,
        "layer_node_cross_domain_failures": layer_node_cross_domain_failures,
        "global_label_failures": global_label_failures,
        "overlap_assigned_to_direct_bank": overlap_assigned_to_direct,
        "alphabetic_acronym_failures": alphabetic_acronym_failures,
        "hyphenated_abbreviation_failures": hyphenated_abbreviation_failures,
        "cross_paper_selection_failures": cross_paper_selection_failures,
    }
    return {
        "qa_contract": "mechanical_provenance_checks_not_human_scientific_entailment",
        "all_checks_pass": all(checks.values()),
        "checks": checks,
        "failure_counts": failure_counts,
        "pair_bank_counts": {"iTE": len(ite_pairs), "TG": len(tg_pairs)},
    }


def write_readme(
    records: pd.DataFrame,
    papers: pd.DataFrame,
    occurrences: pd.DataFrame,
    primary: pd.DataFrame,
    relations: pd.DataFrame,
    sentence_pairs: pd.DataFrame,
    ite_pairs: pd.DataFrame,
    tg_pairs: pd.DataFrame,
    overlaps: pd.DataFrame,
    tiered_candidates: pd.DataFrame,
    node_summary: pd.DataFrame,
    review_queue: pd.DataFrame,
    relation_review_queue: pd.DataFrame,
    hinges: pd.DataFrame,
) -> None:
    scope_counts = papers["scope_decision"].value_counts()
    focus_node_paths = tiered_candidates[
        tiered_candidates["shared_node_focus_eligible"]
    ]
    focus_candidates = focus_node_paths[focus_node_paths["focus_eligible"]]
    endpoint_quarantine = focus_node_paths[~focus_node_paths["focus_eligible"]]
    focus_nodes = node_summary[node_summary["shared_node_focus_eligible"]]
    grade_counts = focus_candidates["evidence_grade"].value_counts()
    focus_node_grade_counts = focus_nodes[
        "focus_candidate_best_evidence_grade"
    ].value_counts()
    lines = [
        "# Clean-room abstract concept and pair layer",
        "",
        "This build uses only title/metadata for registry and the original abstract for",
        "scope evidence, concepts, relations, and pairs. It does not read any prior",
        "concept map, mechanism card, complementarity program, transfer lever, preferred",
        "paper, positive-control rule, or curated bridge.",
        "",
        "## Corpus",
        "",
        f"- Frozen source records: {len(records):,}",
        f"- DOI/title-deduplicated papers: {len(papers):,}",
        f"- Papers with abstracts: {papers['abstract'].map(bool).sum():,}",
        f"- Missing abstracts: {(~papers['abstract'].map(bool)).sum():,}",
        f"- Strict independent iTE non-faradaic papers: {(papers['analysis_layer'] == 'iTE').sum():,}",
        f"- Strict independent TG papers: {(papers['analysis_layer'] == 'TG').sum():,}",
        f"  - Explicit redox/Faradaic span in abstract: {((papers['analysis_layer'] == 'TG') & (papers['mechanism_class'] == 'TG_redox_explicit')).sum():,}",
        f"  - Explicit TG device/effect term but no redox span in abstract: {((papers['analysis_layer'] == 'TG') & (papers['mechanism_class'] == 'TG_device_term_only')).sum():,}",
        f"- Holdout/adjacent papers: {(papers['analysis_layer'] == 'holdout').sum():,}",
        "",
        "### Scope decisions",
        "",
    ]
    lines.extend(f"- `{name}`: {count:,}" for name, count in scope_counts.items())
    lines.extend(
        [
            "",
            "## Extractive evidence",
            "",
            f"- Selected paper-concept assignments: {len(primary):,}",
            f"- Exact concept occurrences: {len(occurrences):,}",
            f"- Explicit predicate relations: {len(relations):,}",
            f"- Strict syntax-gated relation candidates: {relations['strict_syntax_eligible'].sum() if not relations.empty else 0:,}",
            f"- Same-sentence co-occurrence rows: {len(sentence_pairs):,}",
            f"- iTE pair bank: {len(ite_pairs):,}",
            f"- TG pair bank: {len(tg_pairs):,}",
            f"- Direct cross-layer pair overlaps: {len(overlaps):,}",
            f"- Exact shared pair-endpoint nodes, all categories: {len(node_summary):,}",
            f"- Untruncated distinct-pair paths around all shared nodes: {len(tiered_candidates):,}",
            f"- Material/mechanism focus nodes: {len(focus_nodes):,}",
            f"- Nontrivial paths around those focus nodes, before other-endpoint gate: {len(focus_node_paths):,}",
            f"- Endpoint-pass material/mechanism focus paths: {len(focus_candidates):,}",
            f"- Endpoint-quarantined focus-node paths retained for audit: {len(endpoint_quarantine):,}",
            f"  - G3, both sides human-confirmed: {grade_counts.get('G3_dual_human_confirmed_relations', 0):,}",
            f"  - G2, strict-syntax candidates on both sides: {grade_counts.get('G2_dual_strict_syntax_candidates', 0):,}",
            f"  - G1, strict-syntax candidate on one side: {grade_counts.get('G1_single_strict_syntax_candidate', 0):,}",
            f"  - G0, co-occurrence only on both sides: {grade_counts.get('G0_cooccurrence_only', 0):,}",
            f"- Focus-node best evidence G3/G2/G1/G0/Q: "
            f"{focus_node_grade_counts.get('G3_dual_human_confirmed_relations', 0):,}/"
            f"{focus_node_grade_counts.get('G2_dual_strict_syntax_candidates', 0):,}/"
            f"{focus_node_grade_counts.get('G1_single_strict_syntax_candidate', 0):,}/"
            f"{focus_node_grade_counts.get('G0_cooccurrence_only', 0):,}/"
            f"{focus_node_grade_counts.get('Q_endpoint_quarantine_or_no_path', 0):,}",
            f"- Balanced focus review queue: {len(review_queue):,}",
            f"- Atomic relation-incidence review rows: {len(relation_review_queue):,}",
            f"- Legacy strict bilateral focus view (`hinge_candidates.csv`): {len(hinges):,}",
            "",
            "## Contracts",
            "",
            "- Every concept occurrence has an exact abstract surface, sentence, and character offsets.",
            "- Normalization cannot add scientific terms; `semantic_addition_allowed` is always false.",
            "- Layer node IDs are domain-qualified. Global concept IDs only align morphology-normalized exact surfaces.",
            "- Papers retrieved by both searches are held out from both strict banks, even when their content is relevant.",
            "- Scope separates iTE non-faradaic, TG with explicit redox, TG named by device/effect only, hybrid, adjacent, and unresolved records.",
            "- Concept selection is performed inside each abstract only; cross-paper frequency is descriptive and never changes which concepts are selected.",
            "- Explicit relations require source span, visible predicate, and target span in one sentence.",
            "- Negated/modal/epistemic assertions and syntax-risk relations do not enter the strict candidate set.",
            "- No relation enters an observed graph before separate human semantic review.",
            "- Same-sentence pairs are marked non-causal and kept separate from asserted relations.",
            "- Side levels are L3 human-confirmed relation, L2 strict-syntax candidate, and L1 same-sentence co-occurrence; G3/G2/G1/G0 is the symmetric two-side evidence floor/ceiling combination.",
            "- This base build is an unreviewed machine snapshot: it never reads a review overlay, deliberately keeps every relation `graph_eligible=false`, and therefore reserves but cannot currently emit G3.",
            "- The A/B/C alias is assigned only from strict-syntax support (A both, B one, C neither); G-grade is authoritative and neither scheme is compatibility, novelty, or scientific quality.",
            "- The full candidate mother table is untruncated and has stable audit order, not a global top-N rank.",
            "- The focus flag is a declared material/mechanism endpoint view and never deletes rows from the all-node mother table.",
            "- The balanced review queue retains every A/B path and at most three C paths per exact shared node; known paper or control identity is not used.",
            "- Novelty and cross-paper compatibility remain explicitly unassessed/untested.",
            "- Direct same-pair overlaps are reported separately and never converted into shared-node paths.",
            "- No positive control, known-case label, or proposed program participates in extraction, tier assignment, or review selection.",
            "",
            "## Files",
            "",
            "- `paper_registry.csv`: clean DOI/title registry and source membership.",
            "- `paper_scope_audit.csv`: every paper, scope evidence, coverage, and manual-check status.",
            "- `abstract_check_queue.csv`: every original abstract with its extracted concepts and relations for one-by-one review.",
            "- `concept_occurrences.csv`: every retained exact abstract span.",
            "- `paper_concepts.csv`: one primary occurrence per paper/concept.",
            "- `abstract_relations.csv`: explicit same-sentence source-predicate-target assertions.",
            "- `same_sentence_pairs.csv`: non-causal concept co-occurrence evidence.",
            "- `ite_pair_bank.csv` and `tg_pair_bank.csv`: independently built pair layers.",
            "- `direct_pair_overlaps.csv`: independently observed exact pair overlaps.",
            "- `tiered_shared_node_pair_candidates_full.csv`: untruncated all-node audit mother table.",
            "- `tiered_focus_node_pair_paths_full.csv`: all nontrivial paths around material/mechanism shared nodes before the other-endpoint gate.",
            "- `tiered_shared_node_pair_candidates_focus.csv`: endpoint-pass material/mechanism focus view, still untruncated.",
            "- `tiered_focus_endpoint_quarantine.csv`: focus-node paths failing only the declared other-endpoint gate; retained, not deleted.",
            "- `all_shared_node_evidence_summary.csv`: one row for every exact shared pair endpoint in all categories.",
            "- `shared_node_evidence_summary.csv`: the 64-row material/mechanism shared-node view, including Q quarantine nodes.",
            "- `balanced_focus_review_queue.csv`: identity-blind A/B complete plus node-balanced C review queue.",
            "- `relation_incident_review_queue.csv`: atomic original-abstract evidence behind focus A/B relation edges.",
            "- `pair_support_evidence.csv`: authoritative atomic pair-to-paper/sentence/relation provenance tuples.",
            "- Candidate tables contain pair/relation foreign keys but no positional paper/DOI/title/sentence aggregates; provenance must resolve through `pair_support_evidence.csv`.",
            "- `relation_semantic_adjudication.csv` and `semantic_reviewed_*`: separate AI sentence-review overlay; it never changes base G grades or production graph eligibility and remains pending human confirmation.",
            "- `hinge_candidates.csv`: legacy strict bilateral focus view, equivalent to the focus A subset in this build.",
            "- `top_hinge_candidates.csv`: backward-compatible copy of the legacy strict view; do not interpret as a global search head.",
            "- `run_manifest.json`: input hashes, script hash, and counts.",
            "- `qa_report.json`: executable provenance and isolation invariants.",
            "",
            "## Important limitation",
            "",
            "This is a conservative extractive baseline. Exact spans and predicates are",
            "machine-verified, but scientific entailment remains pending human abstract-level",
            "review. Lower recall is preferred to adding unsupported semantic labels.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    records, papers = read_sources()
    papers = scope_papers(papers)

    candidate_rows: list[dict[str, object]] = []
    for paper in papers.itertuples(index=False):
        candidate_rows.extend(extract_candidates(paper))
    occurrences, primary = select_concepts(papers, candidate_rows)
    relations = extract_relations(papers, occurrences)
    sentence_pairs = build_sentence_pairs(papers, occurrences, relations)
    ite_pairs = build_pair_bank(sentence_pairs, "iTE")
    tg_pairs = build_pair_bank(sentence_pairs, "TG")
    overlaps = direct_pair_overlaps(ite_pairs, tg_pairs)
    pair_support_evidence = build_pair_support_evidence(
        sentence_pairs, relations, papers, ite_pairs, tg_pairs
    )
    tiered_candidates = tiered_shared_node_pair_candidates(
        ite_pairs, tg_pairs, primary, relations
    )
    all_node_summary = shared_node_evidence_summary(
        ite_pairs, tg_pairs, primary, tiered_candidates
    )
    focus_node_summary = all_node_summary[
        all_node_summary["shared_node_focus_eligible"]
    ].reset_index(drop=True)
    focus_node_paths = tiered_candidates[
        tiered_candidates["shared_node_focus_eligible"]
    ].reset_index(drop=True)
    focus_candidates = focus_node_paths[
        focus_node_paths["focus_eligible"]
    ].reset_index(drop=True)
    focus_endpoint_quarantine = focus_node_paths[
        ~focus_node_paths["focus_eligible"]
    ].reset_index(drop=True)
    review_queue = build_balanced_focus_review_queue(tiered_candidates)
    relation_review_queue = build_relation_incident_review_queue(
        tiered_candidates, relations, papers
    )
    hinges = hinge_candidates(ite_pairs, tg_pairs, primary)
    paper_audit = build_paper_audit(papers, occurrences, primary, relations)
    abstract_check_queue = build_abstract_check_queue(
        paper_audit, primary, relations
    )
    qa_report = build_qa_report(
        papers,
        occurrences,
        relations,
        sentence_pairs,
        ite_pairs,
        tg_pairs,
        overlaps,
    )
    tiered_qa = audit_tiered_candidate_layer(
        ite_pairs,
        tg_pairs,
        tiered_candidates,
        all_node_summary,
        review_queue,
    )
    pair_evidence_qa = audit_pair_support_evidence(
        pair_support_evidence,
        sentence_pairs,
        relations,
        papers,
        ite_pairs,
        tg_pairs,
        tiered_candidates,
    )
    qa_report["checks"].update(tiered_qa["checks"])
    qa_report["checks"].update(pair_evidence_qa["checks"])
    qa_report["failure_counts"].update(tiered_qa["failure_counts"])
    qa_report["failure_counts"].update(pair_evidence_qa["failure_counts"])
    eligibility_source = (
        Path(__file__).read_text(encoding="utf-8")
        .split("def tiered_shared_node_pair_candidates", 1)[1]
        .split("def shared_node_evidence_summary", 1)[0]
        .lower()
    )
    known_identity_literals = [
        literal
        for literal in ["p0283", "p0337", "cyclodextrin", "triiodide"]
        if literal in eligibility_source
    ]
    qa_report["checks"][
        "known_cd_case_literals_absent_from_tier_eligibility_code"
    ] = not known_identity_literals
    qa_report["failure_counts"][
        "known_cd_case_literals_in_tier_eligibility_code"
    ] = known_identity_literals
    qa_report["all_checks_pass"] = all(qa_report["checks"].values())

    records.to_csv(OUT / "source_record_registry.csv", index=False)
    papers.to_csv(OUT / "paper_registry.csv", index=False)
    paper_audit.to_csv(OUT / "paper_scope_audit.csv", index=False)
    abstract_check_queue.to_csv(OUT / "abstract_check_queue.csv", index=False)
    occurrences.to_csv(OUT / "concept_occurrences.csv", index=False)
    primary.to_csv(OUT / "paper_concepts.csv", index=False)
    relations.to_csv(OUT / "abstract_relations.csv", index=False)
    sentence_pairs.to_csv(OUT / "same_sentence_pairs.csv", index=False)
    ite_pairs.to_csv(OUT / "ite_pair_bank.csv", index=False)
    tg_pairs.to_csv(OUT / "tg_pair_bank.csv", index=False)
    overlaps.to_csv(OUT / "direct_pair_overlaps.csv", index=False)
    pair_support_evidence.to_csv(OUT / "pair_support_evidence.csv", index=False)
    tiered_candidates.to_csv(
        OUT / "tiered_shared_node_pair_candidates_full.csv", index=False
    )
    focus_node_paths.to_csv(
        OUT / "tiered_focus_node_pair_paths_full.csv", index=False
    )
    focus_candidates.to_csv(
        OUT / "tiered_shared_node_pair_candidates_focus.csv", index=False
    )
    focus_endpoint_quarantine.to_csv(
        OUT / "tiered_focus_endpoint_quarantine.csv", index=False
    )
    all_node_summary.to_csv(
        OUT / "all_shared_node_evidence_summary.csv", index=False
    )
    focus_node_summary.to_csv(OUT / "shared_node_evidence_summary.csv", index=False)
    review_queue.to_csv(OUT / "balanced_focus_review_queue.csv", index=False)
    relation_review_queue.to_csv(
        OUT / "relation_incident_review_queue.csv", index=False
    )
    hinges.to_csv(OUT / "hinge_candidates.csv", index=False)
    hinges.head(500).to_csv(OUT / "top_hinge_candidates.csv", index=False)

    manifest = {
        "pipeline": "cleanroom_abstract_pair_layer_v3",
        "inputs": {
            filename: {
                "allowed_columns_sha256": source_contract_sha256(
                    SOURCE_DIR / filename
                ),
                "allowed_columns": SOURCE_COLUMNS,
                "rows": int(
                    len(
                        pd.read_csv(
                            SOURCE_DIR / filename,
                            usecols=["文章名"],
                        )
                    )
                ),
            }
            for filename, _ in SOURCES
        },
        "script_sha256": file_sha256(Path(__file__)),
        "forbidden_inputs": [
            "final_concept_layer/*concept*",
            "ite_tg_complementarity/*",
            "task_typed_concept_layer/*",
            "pair_projection/*",
        ],
        "tiered_evidence_contract": {
            "side_levels": {
                "L3": "at_least_one_graph_eligible_human_confirmed_incident_relation",
                "L2": "at_least_one_strict_syntax_incident_relation_candidate",
                "L1": "same_sentence_incident_pair_only",
            },
            "current_stage": "machine_unreviewed_snapshot",
            "G3_reachable_in_this_base_builder": False,
            "human_review_overlay_read_by_this_base_builder": False,
            "human_or_semantic_review_must_be_a_separate_posthoc_layer": True,
            "grades": {
                "G3": "both_sides_L3",
                "G2": "both_sides_at_least_L2",
                "G1": "one_side_at_least_L2_other_side_L1",
                "G0": "both_sides_L1",
                "Q": "no_endpoint_pass_nontrivial_path",
            },
            "full_all_node_table_untruncated": True,
            "global_top_n_ranking_used": False,
            "within_node_support_order_fields": [
                "evidence_floor_desc",
                "evidence_ceiling_desc",
                "minimum_human_confirmed_relation_support_desc",
                "total_human_confirmed_relation_support_desc",
                "minimum_strict_syntax_relation_support_desc",
                "total_strict_syntax_relation_support_desc",
                "minimum_pair_paper_count_desc",
                "sum_pair_paper_count_desc",
                "minimum_pair_sentence_count_desc",
                "sum_pair_sentence_count_desc",
                "pair_ids_stable_tiebreak",
            ],
            "fields_forbidden_from_tier_or_support_order": [
                "paper_id",
                "doi",
                "title",
                "year",
                "shared_document_frequency",
                "known_case_status",
                "positive_control_status",
                "novelty_status",
                "cross_endpoint_observed_status",
            ],
            "known_case_affects_tier_or_selection": False,
            "review_queue_policy": "all_endpoint_pass_A_B_plus_C_top3_within_each_shared_node_tier",
            "scientific_claim_status": "retrieval_only_cross_endpoint_not_tested",
        },
        "source_evidence_contract": {
            "authoritative_table": "pair_support_evidence.csv",
            "candidate_foreign_keys": ["ite_pair_id", "tg_pair_id"],
            "aggregate_paper_doi_title_sentence_fields_present_in_candidate_table": False,
            "positional_zip_of_aggregate_strings_allowed": False,
            "qa_foreign_key_resolution_required": True,
        },
        "counts": {
            "source_records": len(records),
            "papers": len(papers),
            "iTE_direct_papers": int(papers["analysis_layer"].eq("iTE").sum()),
            "TG_direct_papers": int(papers["analysis_layer"].eq("TG").sum()),
            "concept_occurrences": len(occurrences),
            "paper_concepts": len(primary),
            "relations": len(relations),
            "strict_syntax_relation_candidates": int(relations["strict_syntax_eligible"].sum())
            if not relations.empty
            else 0,
            "human_reviewed_graph_relations": int(relations["graph_eligible"].sum())
            if not relations.empty
            else 0,
            "same_sentence_pairs": len(sentence_pairs),
            "iTE_pairs": len(ite_pairs),
            "TG_pairs": len(tg_pairs),
            "direct_pair_overlaps": len(overlaps),
            "pair_support_evidence_rows": len(pair_support_evidence),
            "all_exact_shared_pair_endpoint_nodes": len(all_node_summary),
            "material_mechanism_focus_shared_nodes": len(focus_node_summary),
            "all_node_nontrivial_candidate_paths": len(tiered_candidates),
            "focus_node_nontrivial_paths_before_endpoint_gate": len(focus_node_paths),
            "focus_endpoint_pass_candidate_paths": len(focus_candidates),
            "focus_endpoint_quarantine_paths": len(focus_endpoint_quarantine),
            "focus_G3_paths": int(
                focus_candidates["evidence_grade"]
                .eq("G3_dual_human_confirmed_relations")
                .sum()
            ),
            "focus_G2_paths": int(
                focus_candidates["evidence_grade"]
                .eq("G2_dual_strict_syntax_candidates")
                .sum()
            ),
            "focus_G1_paths": int(
                focus_candidates["evidence_grade"]
                .eq("G1_single_strict_syntax_candidate")
                .sum()
            ),
            "focus_G0_paths": int(
                focus_candidates["evidence_grade"].eq("G0_cooccurrence_only").sum()
            ),
            "balanced_focus_review_queue": len(review_queue),
            "relation_incident_review_rows": len(relation_review_queue),
            "hinge_candidates": len(hinges),
        },
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )
    (OUT / "qa_report.json").write_text(
        json.dumps(
            qa_report, ensure_ascii=False, indent=2, default=json_default
        )
        + "\n",
        encoding="utf-8",
    )
    write_readme(
        records,
        papers,
        occurrences,
        primary,
        relations,
        sentence_pairs,
        ite_pairs,
        tg_pairs,
        overlaps,
        tiered_candidates,
        all_node_summary,
        review_queue,
        relation_review_queue,
        hinges,
    )
    if not qa_report["all_checks_pass"]:
        raise AssertionError(
            "Clean-room QA contract failed; inspect cleanroom_abstract_pair_layer/qa_report.json"
        )
    print((OUT / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
