import math
import re
from collections import Counter, defaultdict
from itertools import combinations, product
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
DATA_DIR = Path("/Users/ryan/Documents/Codex/2026-07-15/r/work")
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)
OUT = WORK / "tg_adoption_iter"
OUT.mkdir(exist_ok=True)

TG_PATH = DATA_DIR / "TG_first333_material_mechanism.csv"
ITE1_PATH = DATA_DIR / "iTE1_first1000_material_mechanism.csv"
ITE2_PATH = DATA_DIR / "iTE2_first711_material_mechanism.csv"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "font.size": 7,
    "axes.spines.right": False,
    "axes.spines.top": False,
})


GENERIC = {
    "thermogalvanic cell", "thermogalvanic effect", "thermoelectric generator",
    "ionic thermoelectric generator", "thermoelectric performance", "temperature gradient",
    "temperature gradients", "heat harvesting", "energy harvesting", "waste heat",
    "redox couple", "redox ions", "hydrogel", "electrolyte", "thermocell",
    "power density", "seebeck coefficient", "ionic conductivity", "thermal energy",
    "low grade heat", "low-grade heat", "flexible device", "wearable device",
    "self-powered sensor", "body heat", "aqueous electrolyte", "polymer matrix",
    "soret effect", "eastman entropy change", "charge-transfer resistances remain largely unchanged",
    "ionic liquid", "ionic liquids", "ionic radius", "ionic bonding", "ionic radii",
    "covalent/ionic bonding", "mixed ionic/covalent", "mixed ionic-covalent",
    "halide ionic", "perovskites ionic", "zintl phase", "rare-earth ionic radius",
}

BACKGROUND_ONLY_CONCEPTS = {
    "wearable biointerface thermocell",
    "Soret thermodiffusion coupling",
}

TYPE_PRIORITY = [
    ("redox_chemistry", [
        r"ferri/?ferrocyanide", r"fe\(cn\)", r"fe2\+/?fe3\+", r"fe3\+/?fe2\+",
        r"iodide/?triiodide", r"i-/i3", r"cu/?cu2\+", r"zn.*iod", r"organic redox",
        r"tempo", r"viologen", r"quinone", r"pyrazine", r"opposite.*redox",
    ]),
    ("solvation_entropy", [
        r"selective .*solvation", r"solvation entropy", r"solvent.*entropy",
        r"hydration entropy", r"fe.*nitrile solvation", r"fe.*clo4 interaction",
        r"water activity", r"water binding", r"host-guest", r"crown", r"cyclodextrin",
        r"high-entropy", r"high entropy", r"salting-out", r"solvation-shell",
    ]),
    ("transport_mechanism", [
        r"thermodiffusion", r"soret", r"ion migration", r"ion transport",
        r"ion diffusion", r"cation-selective", r"selective ion transport",
        r"nanochannel", r"ion channel", r"thermoosmosis", r"mass transfer",
        r"diffusion resistance", r"viscosity",
    ]),
    ("phase_or_species_transition", [
        r"phase transition", r"solid-liquid phase", r"phase-change", r"precipitation",
        r"crystallization", r"species redistribution", r"configurational entropy",
    ]),
    ("gel_microstructure", [
        r"organohydrogel", r"eutogel", r"double-network", r"dynamic-crosslinked",
        r"gel confinement", r"polymer-water", r"polymer entropy", r"chaotropic",
        r"ion-induced crystallization", r"aligned nanochannel", r"nanofiber",
        r"bacterial cellulose", r"cellulose scaffold", r"alginate hydrogel",
        r"zwitterionic", r"water-state", r"water state", r"hydrogel mechanics",
    ]),
    ("electrode_interface", [
        r"charge-transfer", r"redox kinetics", r"electrode kinetics", r"hierarchical electrode",
        r"porous electrode", r"carbon electrode", r"mxene electrode", r"interfacial contact",
        r"reaction area", r"prussian", r"hexacyanoferrate", r"redox electrode",
    ]),
    ("device_function", [
        r"electrochemical refrigeration", r"thermal charging", r"energy storage",
        r"sweat ion", r"wound monitoring", r"smart dressing", r"identity recognition",
        r"strain sensing", r"temperature sensing", r"photothermal", r"solar evaporation",
        r"pv cooling", r"microchannel", r"liquid-flow",
    ]),
    ("material_system", [
        r"mxene", r"pedot:pss", r"pedot", r"cellulose", r"gelma", r"pva", r"pam",
        r"alginate", r"gelatin", r"ionic liquid", r"deep eutectic", r"ethylene glycol",
        r"glycerol", r"nitrile solvent", r"mxene.*hydrogel", r"ionogel",
    ]),
]


MANUAL_CONCEPTS = {
    "ferri/ferrocyanide redox chemistry": ("redox_chemistry", r"ferri|ferrocyanide|fe\(cn\)|\[fe\(cn\)6\]"),
    "Fe2+/Fe3+ solvation redox chemistry": ("redox_chemistry", r"fe2\+|fe3\+|ferric|ferrous|iron-based"),
    "iodide/triiodide redox chemistry": ("redox_chemistry", r"iodide|triiodide|i-/i3|polyiodide"),
    "organic redox molecular design": ("redox_chemistry", r"tempo|viologen|quinone|pyrazine|organic redox"),
    "Cu-based n/p redox thermocell": ("redox_chemistry", r"cu2\+.*h\+.*so4|cu-based.*n-p|cu-based.*thermopower"),
    "hexacyanoferrate redox electrode": ("electrode_interface", r"prussian|hexacyanoferrate|cohcf|copper hexacyanoferrate|redox electrode"),
    "selective solvation entropy engineering": ("solvation_entropy", r"selective .*solvation|solvation entropy|solvent.*entropy|nitrile solvation"),
    "redox-solvation hybrid entropy": ("solvation_entropy", r"redox-solvation|hybrid entropy|redox solvation"),
    "solvation-shell remodeling": ("solvation_entropy", r"solvation shell|solvation shells"),
    "solvent-shell water/DES regulation": ("solvation_entropy", r"water-containing deep eutectic|deep eutectic solvent strategy|des/water|redox solvent shell|redox solvation shell"),
    "supramolecular host-guest redox entropy": ("solvation_entropy", r"(host-guest|host guest|cyclodextrin|alpha-cd|beta-cyclodextrin|guest encapsulation).*(redox|triiodide|iodide|thermocell|thermoelectric|hydrogel)|alpha-cd/i3"),
    "crown-ether cation complexation": ("solvation_entropy", r"crown ether|crown-ether|18-crown-6"),
    "crown-ether-mediated ion migration": ("transport_mechanism", r"crown-ether-mediated ion migration|crown ether.*ion migration|crown-ether.*ion migration"),
    "high-entropy redox/ion coupling": ("solvation_entropy", r"high-entropy|high entropy|multi-cation|multi-ion|multicomponent.*ion"),
    "redox entropy tuning": ("solvation_entropy", r"redox entropy|entropy change|reaction entropy"),
    "ion-pair complexation control": ("solvation_entropy", r"complexation|ion association|coordination|ion-pair|ion pair"),
    "Soret thermodiffusion coupling": ("transport_mechanism", r"thermodiffusion|soret|thermal diffusion"),
    "cation/anion thermodiffusion asymmetry": ("transport_mechanism", r"anion thermodiffusion|cation.*thermodiffusion|bidirectional cationic anchoring|cationic anchoring|crown ether complexation enhances thermal diffusion"),
    "bidirectional cationic anchoring thermodiffusion": ("transport_mechanism", r"bidirectional cationic anchoring|bidirectionally anchored cations|cationic anchoring strategy"),
    "selective-ion-doping bidirectional thermopower": ("transport_mechanism", r"bidirectionally tunable thermopower|selective ion doping|selective-ion doping"),
    "polarized-membrane ionic thermal potential": ("transport_mechanism", r"polarized electrospun membrane|enhanced ionic thermal potential|thermal potential of ion-exchange membranes"),
    "ion-selectivity membrane transport": ("transport_mechanism", r"ion selectivity|ion-selectivity|selective ion|cation-selective|membrane"),
    "soft mixed ionic-electronic coupling": ("transport_mechanism", r"(mixed ionic-electronic|mixed ion-electron|ionic-electronic|electronic ionic).*(pedot|polymer|cellulose|ionogel|hydrogel|carbon nanotube|cnt|swnt|bisulfate|conductive polymer)"),
    "nanochannel-confined ion transport": ("transport_mechanism", r"(nanochannel|nanofluidic|ion channel|subnanometer channel|conical nanochannel|confined ion channel|charged nanochannel|graphene nanochannel).*(electrolyte|ionic thermoelectric|soret|thermodiffusion|mxene|cellulose|membrane|nanofluidic)|photothermoelectric.*mxene confined ion channels"),
    "moisture-gradient ion transport": ("transport_mechanism", r"moisture-gradient|humidity|moisture.*ion|water.*ion transport"),
    "ion-dipole interaction transport": ("transport_mechanism", r"(ion-dipole|electrostatic interaction).*(hydrogel|ionogel|ionic thermoelectric|thermocell|gel)"),
    "phase-transition entropy amplification": ("phase_or_species_transition", r"phase transition|solid-liquid|phase-change|crystallization"),
    "GelMA ion-induced crystallization": ("phase_or_species_transition", r"gelma.*ioninduced crystallization|gelma.*ion-induced crystallization|ioninduced crystallization|ion-induced crystallization"),
    "configurational entropy gel design": ("phase_or_species_transition", r"configurational entropy.*(gel|hydrogel|redox|hydration-shell|solvation shell)|configurational entropy difference"),
    "thermosensitive crystallization salting-out": ("phase_or_species_transition", r"thermosensitive crystallization|salting-out.*crystallization|crystallization.*salting-out"),
    "hydrogel volume-phase transition thermocell": ("phase_or_species_transition", r"volume phase transition.*hydrogel|hydrogel nanoparticle volume phase transition|thermoresponsive.*hydrogel.*phase"),
    "precipitation-driven species redistribution": ("phase_or_species_transition", r"precipitation-driven|temperature-dependent precipitation|precipitation changes redox|species redistribution"),
    "anti-freezing organohydrogel design": ("gel_microstructure", r"anti-freez|antifreez|subzero|organohydrogel|ethylene glycol|glycerol"),
    "chaotropic polymer-water disruption": ("gel_microstructure", r"chaotropic|polymer-water|hydrogen bonding"),
    "salting-out confined ion gel": ("gel_microstructure", r"salting-out|salting out|confined ion transport|solvent-exchange salting"),
    "water-state regulated MXene hydrogel": ("gel_microstructure", r"water state regulation|water-state|water state.*mxene|mxene.*water binding|water binding.*mxene"),
    "zwitterionic hydrogel ion regulation": ("gel_microstructure", r"zwitterionic|sbma|sulfobetaine|bipolar thermoelectricity"),
    "dynamic crosslinked gel network": ("gel_microstructure", r"dynamic-crosslinked|double-network|cross-linked|crosslinked"),
    "interpenetrating-network thermogalvanic hydrogel": ("gel_microstructure", r"interpenetrating network|interpenetrating networks|ipn hydrogel"),
    "coupling-enhanced hydrogel thermoelectric effect": ("gel_microstructure", r"coupling enhanced thermoelectric effect|coupling-enhanced thermoelectric effect"),
    "double-network hydrogel mechanics": ("gel_microstructure", r"double-network hydrogel|double network hydrogel"),
    "cellulose nanofiber scaffold": ("gel_microstructure", r"cellulose|nanocellulose|bacterial cellulose|cotton"),
    "gel-confined redox transport": ("gel_microstructure", r"gel confinement|gel network|polymer network|hydrogel.*redox"),
    "3D ion-channel hydration network": ("gel_microstructure", r"three-dimensional ion channels hydration|3d ion channels hydration|three-dimensional ion channel|3d ion channel"),
    "3D-printable shape-customized hydrogel thermocell": ("gel_microstructure", r"3d printable|shape-customized hydrogel|shape customized hydrogel"),
    "MXene-reinforced thermogalvanic gel": ("material_system", r"mxene|ti3c2"),
    "deep-eutectic eutogel electrolyte": ("material_system", r"deep-eutectic|deep eutectic|eutogel"),
    "imidazolium ionic-liquid phase transition electrolyte": ("material_system", r"(imidazolium|ionic liquid).*(phase transition|solid-liquid|phase change|thermocell|thermogalvanic)|phase.*ionic liquid.*thermocell"),
    "hierarchical porous electrode interface": ("electrode_interface", r"hierarchical electrode|porous electrode|aerogel electrode"),
    "metal-oxide nanostructured electrode": ("electrode_interface", r"metal oxide nanostructured electrode|metal oxide nanostructured electrodes|metal oxide.*electrode"),
    "carbon-electrode redox interface": ("electrode_interface", r"carbon electrode|carbon electrodes|carbon cloth|carbon framework"),
    "etched carbon-cloth redox interface": ("electrode_interface", r"etched carbon cloth|etched carbon-cloth"),
    "charge-transfer resistance engineering": ("electrode_interface", r"charge-transfer|charge transfer|redox kinetics|electrode kinetics"),
    "p/n thermogalvanic series design": ("device_function", r"p/n|p-type|n-type|opposite.*seebeck|opposite.*temperature"),
    "photothermal thermogalvanic integration": ("device_function", r"photothermal|solar|evaporation|steam|light"),
    "localized photothermal layer": ("device_function", r"photothermal layer|photothermal heating|nir photothermal"),
    "electrochemical refrigeration thermocell": ("device_function", r"refrigeration|cooling"),
    "thermal charging redox storage": ("device_function", r"thermal charging|energy storage|charging cell|storage"),
    "thermal management thermogalvanic gel": ("device_function", r"thermal management of electronics|electronics cooling|thermal management.*thermogalvanic|simultaneous waste heat recovery and thermal management"),
    "smart-wound thermogalvanic dressing": ("device_function", r"smart wound monitoring|accelerated healing|thermogalvanic cell dressing"),
    "thermal-resistance cell architecture": ("device_function", r"thermal resistance network|internal thermal resistance|electrode temperature changes|triply periodic minimal surface|tpms|natural convection"),
    "evaporation-assisted concentration gradient": ("transport_mechanism", r"water evaporation-enhanced|ambient evaporation|electrolyte concentration gradient|temperature-regulated electrolyte gradient|continuous redox desalination"),
    "molecular-chaperone redox-gradient stabilization": ("solvation_entropy", r"molecular chaperone|sustains redox concentration gradients|so42-/so32-|sulfate/sulfite"),
    "SAM-stabilized electrostatic electrocatalysis": ("electrode_interface", r"self-assembled monolayer|sams electrocatalyze|electrostatically charged sam|gold passivation"),
    "thermoresponsive micellization p/n conversion": ("phase_or_species_transition", r"micellization|thermoresponsive diblock|p-n conversion|invert hot/cold redox"),
    "photocatalytic redox-gradient regeneration": ("device_function", r"photocatalytically enhanced|photocatalytic hydrogen|hydrogen/oxygen generation maintains redox-ion concentration gradient"),
    "quasi-solid granular electrolyte matrix": ("material_system", r"sand grains|granular|quasi-solid.*sand|desert sand"),
    "carboxylated chitosan redox additive": ("material_system", r"carboxylated chitosan|chitosan additive"),
    "CPV-iTEC solar cascade coupling": ("device_function", r"cpv-itec|concentrated photovoltaic|pi-type multichannels|pv panel"),
    "alkaline-fuel-cell waste-heat cascade": ("device_function", r"alkaline fuel cell|afc waste heat|thermal-electric cascade"),
    "porous/pin-electrode thermal-gradient architecture": ("electrode_interface", r"thick porous/pin electrodes|pin electrodes|internal electrode temperature gradients|effective voltage"),
    "multimodal interfacial heat-transfer sensing": ("device_function", r"multimodal fingertip|dynamic interfacial heat-transfer|material fingerprint|grip pressure.*thermogalvanic|smart pen|handwriting"),
    "redox-layer ionic-gradient cell": ("transport_mechanism", r"double-layer.*redox gel|spatially separated redox gel|engineered ionic gradients|ion concentration gradients|redox-ion concentration gradient"),
    "Ni-bipyridine hydration-shell entropy": ("solvation_entropy", r"ni\\(bpy\\)|nickel-bipyridine|hydration-shell behavior|configurational entropy difference"),
    "Cu-ethylenediamine chelation entropy": ("redox_chemistry", r"cu\\(en\\)|ethylenediamine|cu/en chelation|cu\\(en\\)2"),
    "solar-thermal liquid thermogalvanic generator": ("device_function", r"solar liquid thermogalvanic|spectrally selective solar absorbers|solar-thermal-to-electric"),
    "printed thermogalvanic module integration": ("device_function", r"fully printed|additive printing|laser-drilled spacer|printed tgm|printed thermogalvanic"),
    "polymer-regulated HQ/BQ equilibrium": ("solvation_entropy", r"hydroquinone-benzoquinone|hq/bq|selectively transports hq|self-regulates ph"),
    "radiative-cooling thermogalvanic night generator": ("device_function", r"radiative sky cooling|radiative cooling creates nighttime|nighttime electricity"),
    "redox-split chemical heterogeneity": ("transport_mechanism", r"redox-split|chemical heterogeneity|localized hot-side oxidation|weakly coordinating anions"),
    "resistance-gated thermogalvanic wearable": ("device_function", r"resistance-gated|deformation-reduced interfacial resistance|hydrogel wristband"),
    "Li-ion TREC electrode-selection thermodynamics": ("electrode_interface", r"li-ion-based thermogalvanic|li-ion trec|lithiation-state dependence|electrode thermogalvanic coefficient"),
    "decomposition-layer thermogalvanic profiling": ("electrode_interface", r"decomposition layer|thermogalvanic profiles reveal|lipon coating|thin-film si"),
    "self-assembled aerogel sheet electrode": ("electrode_interface", r"self-assembled porous aerogel|aerogel sheet electrode|porous aerogel sheet"),
    "convection-resolved resistance decomposition": ("transport_mechanism", r"rotating disk electrode|convective mass transfer|diffusion resistance while solution|resistance components"),
    "supporting-electrolyte viscosity/resistance tradeoff": ("transport_mechanism", r"supporting electrolyte lowers solution resistance|raises charge-transfer/diffusion resistance|naclo4 supporting electrolyte"),
    "Gutmann-donor ionic-cluster thermodiffusion": ("transport_mechanism", r"gutmann donor|mononuclear ionic cluster|n-type thermoelectric ionogel"),
    "thermodiffusion-assisted n-type thermogalvanic cell": ("transport_mechanism", r"n-type thermodiffusion-assisted thermogalvanic|thermodiffusion-assisted thermogalvanic"),
    "thermal-potential-induced redox reaction": ("redox_chemistry", r"thermal potential induced redox|thermal-potential induced redox"),
    "antisolvent high-entropy liquid-flow thermocell": ("solvation_entropy", r"antisolvent engineering.*high-entropy|high-entropy liquid flow thermocell|high entropy liquid flow thermocell"),
    "electrostatic-interaction cationic hydrogel": ("gel_microstructure", r"electrostatic interaction in cationic hydrogels|cationic hydrogel.*electrostatic interaction"),
    "PEM proton-coupled thermoelectrochemical converter": ("transport_mechanism", r"pem-based|h2/h2o electrodes|coupled proton transport|gas compositions"),
    "biphase-solvation liquid thermocell": ("solvation_entropy", r"aqueous biphase|biphasic.*thermocell|different electrode solvation environments|suppresses convection"),
    "biomass-derived porous carbon electrode": ("electrode_interface", r"mandarin-peel|biomass-derived|nitrogen-doped porosity|porous carbon thermocell"),
    "polymer-electrolyte Soret spectroscopy": ("transport_mechanism", r"thermal-gradient ftir|ftir-atr|salt concentration gradients used to measure diffusion|polymer electrolyte.*soret"),
    "wearable biointerface thermocell": ("device_function", r"wound|dressing|skin|body heat|facial|e-skin|sweat"),
    "microfluidic redox-solvation thermocell": ("device_function", r"microchannel|liquid-flow|flow thermocell|redox-solvation"),
}


CURATED_RARE_CONCEPTS = {
    "thermal-resistance cell architecture",
    "evaporation-assisted concentration gradient",
    "molecular-chaperone redox-gradient stabilization",
    "SAM-stabilized electrostatic electrocatalysis",
    "thermoresponsive micellization p/n conversion",
    "photocatalytic redox-gradient regeneration",
    "quasi-solid granular electrolyte matrix",
    "carboxylated chitosan redox additive",
    "CPV-iTEC solar cascade coupling",
    "alkaline-fuel-cell waste-heat cascade",
    "porous/pin-electrode thermal-gradient architecture",
    "multimodal interfacial heat-transfer sensing",
    "redox-layer ionic-gradient cell",
    "Ni-bipyridine hydration-shell entropy",
    "Cu-ethylenediamine chelation entropy",
    "solar-thermal liquid thermogalvanic generator",
    "printed thermogalvanic module integration",
    "polymer-regulated HQ/BQ equilibrium",
    "radiative-cooling thermogalvanic night generator",
    "redox-split chemical heterogeneity",
    "resistance-gated thermogalvanic wearable",
    "Li-ion TREC electrode-selection thermodynamics",
    "decomposition-layer thermogalvanic profiling",
    "self-assembled aerogel sheet electrode",
    "convection-resolved resistance decomposition",
    "supporting-electrolyte viscosity/resistance tradeoff",
    "PEM proton-coupled thermoelectrochemical converter",
    "biphase-solvation liquid thermocell",
    "biomass-derived porous carbon electrode",
    "polymer-electrolyte Soret spectroscopy",
    "thermal management thermogalvanic gel",
    "water-state regulated MXene hydrogel",
    "crown-ether cation complexation",
    "crown-ether-mediated ion migration",
    "bidirectional cationic anchoring thermodiffusion",
    "selective-ion-doping bidirectional thermopower",
    "polarized-membrane ionic thermal potential",
    "GelMA ion-induced crystallization",
    "interpenetrating-network thermogalvanic hydrogel",
    "coupling-enhanced hydrogel thermoelectric effect",
    "3D ion-channel hydration network",
    "3D-printable shape-customized hydrogel thermocell",
    "metal-oxide nanostructured electrode",
    "etched carbon-cloth redox interface",
    "smart-wound thermogalvanic dressing",
    "Gutmann-donor ionic-cluster thermodiffusion",
    "thermodiffusion-assisted n-type thermogalvanic cell",
    "thermal-potential-induced redox reaction",
    "antisolvent high-entropy liquid-flow thermocell",
    "electrostatic-interaction cationic hydrogel",
}


SOFT_RELEVANT_PATTERN = re.compile(
    r"hydrogel|ionogel|gel |gel-|polymer|pedot|pss|thermodiffusion|soret|redox|"
    r"ionic liquid|electrolyte|moisture|humidity|cellulose|mxene|nanochannel|"
    r"ion channel|wearable|flexible|thermocell|thermogalvanic|thermoelectrochemical|"
    r"thermo-electrochemical|aqueous|solvation|complexation|salt|cation|anion|"
    r"cyclodextrin|crown|host-guest|zwitterionic|eutogel|organohydrogel"
)

SOLID_DESCRIPTOR_PATTERN = re.compile(
    r"perovskite|band gap|boltzmann|zintl|skutterudite|half-heusler|lattice thermal|"
    r"phonon|dft|first-principles|rare-earth|ionic radius|covalent|crystal|semiconductor"
)


def clean_phrase(text):
    text = text.lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"[^a-z0-9+\-/():., ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.;:")
    return text


def concept_type(concept):
    c = concept.lower()
    for typ, patterns in TYPE_PRIORITY:
        if any(re.search(p, c) for p in patterns):
            return typ
    return "material_system"


def extract_phrases(row):
    material = clean_phrase(row.material)
    mechanism = clean_phrase(row.mechanism)
    combined = f"{material}. {mechanism}"
    title_abstract = clean_phrase(f"{row.title} {row.abstract}")
    full_text = f"{title_abstract}. {combined}"
    if row.source != "TG" and SOLID_DESCRIPTOR_PATTERN.search(full_text) and not SOFT_RELEVANT_PATTERN.search(full_text):
        return {}
    concepts = {}

    for label, (typ, pat) in MANUAL_CONCEPTS.items():
        if re.search(pat, full_text):
            concepts[label] = typ

    if "supramolecular host-guest redox entropy" in concepts:
        soft_host_guest = re.search(r"cyclodextrin|alpha-cd|beta-cyclodextrin|triiodide|iodide|i3-|hydrogel|thermocell", full_text)
        solid_host_guest = re.search(r"clathrate|zintl|guest-framework|host structure engineering", full_text)
        if solid_host_guest and not soft_host_guest:
            concepts.pop("supramolecular host-guest redox entropy", None)

    chunks = re.split(r";|,| while | whereas | through | via | by | due to | enabled by | using | with | and ", combined)
    heads = (
        "solvation", "entropy", "complexation", "thermodiffusion", "soret", "crystallization",
        "precipitation", "phase transition", "nanochannel", "ion channel", "redox kinetics",
        "charge-transfer", "anti-freezing", "chaotropic", "mxene", "eutogel", "organohydrogel",
        "microchannel", "photothermal", "refrigeration", "thermal charging", "moisture-gradient",
    )
    for chunk in chunks:
        chunk = chunk.strip(" .")
        if len(chunk) < 12 or len(chunk) > 82:
            continue
        if chunk in GENERIC:
            continue
        if not any(h in chunk for h in heads):
            continue
        words = chunk.split()
        if len(words) > 8:
            chunk = " ".join(words[-8:])
        if chunk in GENERIC:
            continue
        concepts[chunk] = concept_type(chunk)

    filtered = {}
    for c, typ in concepts.items():
        c = c.strip(" .,:;")
        if c in GENERIC:
            continue
        if len(c.split()) < 2:
            continue
        if len(c) > 90:
            continue
        filtered[c] = typ
    return filtered


def read_source(path, source):
    df = pd.read_csv(path)
    df = df.rename(columns={"文章名": "title", "期刊名": "journal", "DOI": "doi", "年份": "year", "摘要": "abstract", "材料": "material", "机制": "mechanism"})
    df["source"] = source
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"]).copy()
    df["year"] = df["year"].astype(int)
    for col in ["title", "journal", "doi", "abstract", "material", "mechanism"]:
        df[col] = df[col].fillna("")
    df["paper_id"] = [f"{source}_{i:04d}" for i in range(len(df))]
    return df[["paper_id", "source", "year", "title", "journal", "doi", "abstract", "material", "mechanism"]]


def make_paper_concepts():
    papers = pd.concat([
        read_source(TG_PATH, "TG"),
        read_source(ITE1_PATH, "iTE1"),
        read_source(ITE2_PATH, "iTE2"),
    ], ignore_index=True)
    papers = papers[papers["year"].between(1990, 2026)].copy()

    long_rows = []
    for row in papers.itertuples():
        concepts = extract_phrases(row)
        for concept, typ in concepts.items():
            long_rows.append({
                "paper_id": row.paper_id,
                "source": row.source,
                "year": row.year,
                "title": row.title,
                "doi": row.doi,
                "concept": concept,
                "concept_type": typ,
            })
    pc = pd.DataFrame(long_rows).drop_duplicates(["paper_id", "concept"])
    counts = pc.groupby("concept")["paper_id"].nunique()
    keep = pc["concept"].map(counts).between(2, 180) | pc["concept"].isin(CURATED_RARE_CONCEPTS)
    pc = pc[keep].copy()
    return papers, pc


def graph_until(pc, cutoff, source_filter=None):
    d = pc[pc["year"] <= cutoff]
    if source_filter is not None:
        d = d[d["source"].isin(source_filter)]
    G = nx.Graph()
    for paper_id, g in d.groupby("paper_id"):
        concepts = sorted(g["concept"].unique())
        for c in concepts:
            G.add_node(c)
        for u, v in combinations(concepts, 2):
            if G.has_edge(u, v):
                G[u][v]["weight"] += 1
            else:
                G.add_edge(u, v, weight=1)
    return G


def edge_exists_future_tg(pc, u, v, start, end):
    d = pc[(pc["source"] == "TG") & (pc["year"].between(start, end))]
    for _, g in d.groupby("paper_id"):
        s = set(g["concept"])
        if u in s and v in s:
            return 1
    return 0


def first_year(pc, concept, source_group=None, max_year=None):
    d = pc[pc["concept"] == concept]
    if source_group is not None:
        d = d[d["source"].isin(source_group)]
    if max_year is not None:
        d = d[d["year"] <= max_year]
    if d.empty:
        return None
    return int(d["year"].min())


def concept_counts(pc, cutoff):
    d = pc[pc["year"] <= cutoff]
    total = d.groupby("concept")["paper_id"].nunique().to_dict()
    tg = d[d["source"] == "TG"].groupby("concept")["paper_id"].nunique().to_dict()
    ite = d[d["source"].isin(["iTE1", "iTE2"])].groupby("concept")["paper_id"].nunique().to_dict()
    typ = d.groupby("concept")["concept_type"].agg(lambda x: x.value_counts().idxmax()).to_dict()
    return total, tg, ite, typ


def build_embeddings(concepts):
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    X = vectorizer.fit_transform(concepts)
    sim = cosine_similarity(X)
    return {c: i for i, c in enumerate(concepts)}, sim


def pair_features(pc, cutoff, u, v, type_map, concept_to_idx, sim_matrix):
    G_all = graph_until(pc, cutoff)
    G_tg = graph_until(pc, cutoff, ["TG"])
    G_ite = graph_until(pc, cutoff, ["iTE1", "iTE2"])
    return pair_features_from_graphs(pc, cutoff, u, v, type_map, concept_to_idx, sim_matrix, G_all, G_tg, G_ite)


def pair_features_from_graphs(pc, cutoff, u, v, type_map, concept_to_idx, sim_matrix, G_all, G_tg, G_ite):
    def deg(G, c):
        return G.degree(c) if c in G else 0

    common = len(list(nx.common_neighbors(G_all, u, v))) if u in G_all and v in G_all else 0
    try:
        dist = nx.shortest_path_length(G_all, u, v) if u in G_all and v in G_all else 99
    except nx.NetworkXNoPath:
        dist = 99
    try:
        aa = next(nx.adamic_adar_index(G_all, [(u, v)]))[2] if u in G_all and v in G_all else 0
    except ZeroDivisionError:
        aa = 0
    u_ite_first = first_year(pc, u, ["iTE1", "iTE2"], cutoff)
    u_tg_first = first_year(pc, u, ["TG"], cutoff)
    v_tg_first = first_year(pc, v, ["TG"], cutoff)
    lag = 0
    if u_ite_first is not None and u_tg_first is not None:
        lag = max(0, u_tg_first - u_ite_first)
    elif u_ite_first is not None and u_tg_first is None:
        lag = cutoff - u_ite_first + 1
    type_cross = int(type_map.get(u) != type_map.get(v))
    semantic_sim = sim_matrix[concept_to_idx[u], concept_to_idx[v]]
    return {
        "u_degree_all": deg(G_all, u),
        "v_degree_all": deg(G_all, v),
        "u_degree_tg": deg(G_tg, u),
        "v_degree_tg": deg(G_tg, v),
        "u_degree_ite": deg(G_ite, u),
        "v_degree_ite": deg(G_ite, v),
        "common_neighbors": common,
        "adamic_adar": aa,
        "preferential_attachment": deg(G_all, u) * deg(G_all, v),
        "shortest_path": min(dist, 12),
        "semantic_similarity": semantic_sim,
        "cross_type": type_cross,
        "ite_lead_years_for_u": lag,
        "u_seen_in_ite": int(u_ite_first is not None),
        "u_seen_in_tg": int(u_tg_first is not None),
        "v_seen_in_tg": int(v_tg_first is not None),
    }


def candidate_pairs(pc, cutoff, max_pairs=12000):
    total, tg, ite, typ = concept_counts(pc, cutoff)
    all_concepts = sorted(total)
    concept_to_idx, sim_matrix = build_embeddings(all_concepts)
    G_tg = graph_until(pc, cutoff, ["TG"])
    G_all = graph_until(pc, cutoff)
    G_ite = graph_until(pc, cutoff, ["iTE1", "iTE2"])

    donor_types = {"solvation_entropy", "transport_mechanism", "phase_or_species_transition", "gel_microstructure", "electrode_interface"}
    anchor_types = {"redox_chemistry", "gel_microstructure", "material_system", "electrode_interface"}

    donors = [
        c for c in all_concepts
        if ite.get(c, 0) >= 2
        and tg.get(c, 0) <= 6
        and total.get(c, 0) <= 80
        and typ.get(c) in donor_types
        and c not in GENERIC
        and c not in BACKGROUND_ONLY_CONCEPTS
        and (
            (first_year(pc, c, ["TG"], cutoff) is None)
            or (first_year(pc, c, ["iTE1", "iTE2"], cutoff) is not None and first_year(pc, c, ["iTE1", "iTE2"], cutoff) < first_year(pc, c, ["TG"], cutoff))
            or (ite.get(c, 0) > 1.5 * max(1, tg.get(c, 0)))
        )
    ]
    anchors = [
        c for c in all_concepts
        if (tg.get(c, 0) >= 2 or (c in CURATED_RARE_CONCEPTS and tg.get(c, 0) >= 1))
        and total.get(c, 0) <= 120
        and typ.get(c) in anchor_types
        and c not in GENERIC
        and c not in BACKGROUND_ONLY_CONCEPTS
    ]

    rows = []
    seen_unordered = set()
    for u, v in product(donors, anchors):
        if u == v:
            continue
        key = tuple(sorted([u, v]))
        if key in seen_unordered:
            continue
        if typ.get(u) == typ.get(v) and typ.get(u) not in {"gel_microstructure", "material_system"}:
            continue
        if G_tg.has_edge(u, v):
            continue
        sim = sim_matrix[concept_to_idx[u], concept_to_idx[v]]
        if sim > 0.86:
            continue
        try:
            d = nx.shortest_path_length(G_all, u, v) if u in G_all and v in G_all else 99
        except nx.NetworkXNoPath:
            d = 99
        if d == 1:
            continue
        if d > 8 and sim < 0.08:
            continue
        feats = pair_features_from_graphs(pc, cutoff, u, v, typ, concept_to_idx, sim_matrix, G_all, G_tg, G_ite)
        rows.append({
            "cutoff_year": cutoff,
            "concept_i_ite_donor": u,
            "concept_j_tg_anchor": v,
            "i_type": typ.get(u),
            "j_type": typ.get(v),
            **feats,
        })
        seen_unordered.add(key)

    df = pd.DataFrame(rows)
    if len(df) > max_pairs:
        # Keep all likely positives plus hard negatives near the graph/semantic frontier.
        df["_score"] = (
            df["common_neighbors"] * 2
            + df["semantic_similarity"] * 6
            + df["ite_lead_years_for_u"] * 0.08
            - df["shortest_path"] * 0.08
        )
        df = df.sort_values("_score", ascending=False).head(max_pairs).drop(columns="_score")
    return df


def add_labels(pc, samples, horizon):
    start, end = horizon
    labels = []
    examples = []
    for r in samples.itertuples():
        d = pc[(pc["source"] == "TG") & (pc["year"].between(start, end))]
        label = 0
        ex = ""
        for _, g in d.groupby("paper_id"):
            s = set(g["concept"])
            if r.concept_i_ite_donor in s and r.concept_j_tg_anchor in s:
                label = 1
                ex = g["title"].iloc[0]
                break
        labels.append(label)
        examples.append(ex)
    samples = samples.copy()
    samples["future_TG_edge_label"] = labels
    samples["future_example_title"] = examples
    samples["future_window"] = f"{start}-{end}"
    return samples


FEATURE_COLS = [
        "u_degree_all", "v_degree_all", "u_degree_tg", "v_degree_tg", "u_degree_ite", "v_degree_ite",
        "common_neighbors", "adamic_adar", "preferential_attachment", "shortest_path",
        "semantic_similarity", "cross_type", "ite_lead_years_for_u", "u_seen_in_ite",
        "u_seen_in_tg", "v_seen_in_tg",
]


def fit_ml_adoption_model(train_df):
    feature_cols = FEATURE_COLS
    X_train = train_df[feature_cols].fillna(0).to_numpy()
    y_train = train_df["future_TG_edge_label"].to_numpy()
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)

    lr = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=7)
    lr.fit(X_train_s, y_train)

    rf = RandomForestClassifier(
        n_estimators=300,
        min_samples_leaf=4,
        class_weight="balanced_subsample",
        random_state=7,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    return scaler, lr, rf, feature_cols


def predict_ml_adoption(models, df):
    scaler, lr, rf, feature_cols = models
    X = df[feature_cols].fillna(0).to_numpy()
    X_s = scaler.transform(X)
    lr_pred = lr.predict_proba(X_s)[:, 1]
    rf_pred = rf.predict_proba(X)[:, 1]
    return 0.55 * lr_pred + 0.45 * rf_pred


def train_and_score(train_df, test_df):
    models = fit_ml_adoption_model(train_df)
    y_train = train_df["future_TG_edge_label"].to_numpy()
    y_test = test_df["future_TG_edge_label"].to_numpy()
    pred = predict_ml_adoption(models, test_df)

    structural_score = graph_rank_score(test_df)
    metrics = {
        "n_train": len(train_df),
        "train_positive": int(y_train.sum()),
        "n_test": len(test_df),
        "test_positive": int(y_test.sum()),
        "ml_roc_auc": roc_auc_score(y_test, pred) if len(set(y_test)) > 1 else np.nan,
        "ml_average_precision": average_precision_score(y_test, pred) if len(set(y_test)) > 1 else np.nan,
        "graph_roc_auc": roc_auc_score(y_test, structural_score) if len(set(y_test)) > 1 else np.nan,
        "graph_average_precision": average_precision_score(y_test, structural_score) if len(set(y_test)) > 1 else np.nan,
    }
    for k in [10, 25, 50, 100]:
        idx_ml = np.argsort(pred)[::-1][: min(k, len(pred))]
        idx_graph = np.argsort(structural_score)[::-1][: min(k, len(structural_score))]
        metrics[f"ml_precision_at_{k}"] = float(y_test[idx_ml].mean()) if len(idx_ml) else np.nan
        metrics[f"ml_hits_at_{k}"] = int(y_test[idx_ml].sum()) if len(idx_ml) else 0
        metrics[f"graph_precision_at_{k}"] = float(y_test[idx_graph].mean()) if len(idx_graph) else np.nan
        metrics[f"graph_hits_at_{k}"] = int(y_test[idx_graph].sum()) if len(idx_graph) else 0
    out = test_df.copy()
    out["ml_score"] = pred
    out["graph_adoption_score"] = structural_score
    hybrid = 0.75 * pd.Series(structural_score).rank(pct=True).to_numpy() + 0.25 * pd.Series(pred).rank(pct=True).to_numpy()
    out["hybrid_adoption_score"] = hybrid
    if len(set(y_test)) > 1:
        metrics["hybrid_roc_auc"] = roc_auc_score(y_test, hybrid)
        metrics["hybrid_average_precision"] = average_precision_score(y_test, hybrid)
        for k in [10, 25, 50, 100]:
            idx_hybrid = np.argsort(hybrid)[::-1][: min(k, len(hybrid))]
            metrics[f"hybrid_precision_at_{k}"] = float(y_test[idx_hybrid].mean()) if len(idx_hybrid) else np.nan
            metrics[f"hybrid_hits_at_{k}"] = int(y_test[idx_hybrid].sum()) if len(idx_hybrid) else 0
    return out.sort_values("hybrid_adoption_score", ascending=False), metrics, FEATURE_COLS, models


def graph_rank_score(df):
    rank = lambda s: s.fillna(0).rank(pct=True).to_numpy()
    return (
        1.0 * rank(df["preferential_attachment"])
        + 0.35 * rank(df["adamic_adar"])
        + 0.25 * rank(df["common_neighbors"])
        + 0.15 * rank(-df["shortest_path"])
        + 0.10 * rank(df["semantic_similarity"])
    )


def plot_top(scored):
    top = scored.head(18).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.1, 5.0))
    labels = [f"{r.concept_i_ite_donor}\n+ {r.concept_j_tg_anchor}" for r in top.itertuples()]
    colors = ["#5B8DB8" if y else "#C9C9C9" for y in top["future_TG_edge_label"]]
    ax.barh(np.arange(len(top)), top["hybrid_adoption_score"], color=colors, edgecolor="white", linewidth=0.6)
    ax.set_yticks(np.arange(len(top)))
    ax.set_yticklabels(labels, fontsize=5.6)
    ax.set_xlabel("hybrid TG adoption score")
    ax.set_title("Back-tested iTE -> TG concept adoption ranking", loc="left", fontsize=10, fontweight="bold")
    ax.text(0.99, 0.02, "blue = realized in future TG window", transform=ax.transAxes, ha="right", fontsize=6, color="#555")
    fig.savefig(OUT / "tg_adoption_prediction_backtest.svg", bbox_inches="tight")
    fig.savefig(OUT / "tg_adoption_prediction_backtest.pdf", bbox_inches="tight")
    fig.savefig(OUT / "tg_adoption_prediction_backtest.png", bbox_inches="tight", dpi=600)
    fig.savefig(OUT / "tg_adoption_prediction_backtest.tiff", bbox_inches="tight", dpi=600)
    plt.close(fig)


def write_summary(pc, train_df, scored, metrics):
    lines = []
    lines.append("# TG Adoption Prediction Demo")
    lines.append("")
    lines.append("## What Was Predicted")
    lines.append("Candidate links are pairs where an iTE/TD-side donor concept and a TG-side anchor concept were not connected in TG before the cutoff. The label is whether they co-occurred in future TG papers.")
    lines.append("")
    lines.append("## Concept Corpus")
    lines.append(f"- Paper-concept rows: {len(pc)}")
    lines.append(f"- Unique concepts after filtering: {pc['concept'].nunique()}")
    lines.append(f"- TG papers represented: {pc[pc.source == 'TG']['paper_id'].nunique()}")
    lines.append(f"- iTE papers represented: {pc[pc.source != 'TG']['paper_id'].nunique()}")
    lines.append("")
    lines.append("## Backtest Metrics")
    for k, v in metrics.items():
        if isinstance(v, float):
            lines.append(f"- {k}: {v:.4f}")
        else:
            lines.append(f"- {k}: {v}")
    if (OUT / "tg_adoption_window_summary.csv").exists():
        lines.append("")
        lines.append("## Rolling Windows")
        window_df = pd.read_csv(OUT / "tg_adoption_window_summary.csv")
        for r in window_df.itertuples():
            lines.append(f"- cutoff {int(r.cutoff_year)} -> {r.future_window}: {int(r.n_samples)} candidates, {int(r.n_positive)} positives")
    lines.append("")
    lines.append("## Top Back-tested Predictions")
    for r in scored.head(20).itertuples():
        status = "realized" if r.future_TG_edge_label else "not realized"
        lines.append(f"- {r.concept_i_ite_donor} + {r.concept_j_tg_anchor}: hybrid score {r.hybrid_adoption_score:.3f}, {status}")
        if r.future_example_title:
            lines.append(f"  Evidence: {r.future_example_title}")
    lines.append("")
    lines.append("## Demo Limitations")
    lines.append("- This demo uses auditable phrase rules over your LLM-derived material/mechanism fields, not a newly fine-tuned concept extractor.")
    lines.append("- The dataset is small for NMI-style rare-event prediction; use ranking and top-k hit rate rather than overinterpreting AUC.")
    lines.append("- A full version should manually audit 100-200 concept extractions, normalize synonyms, and calibrate the generic-concept degree threshold.")
    (OUT / "tg_adoption_prediction_demo_summary.md").write_text("\n".join(lines), encoding="utf-8")


def score_post2026_candidates(pc, models=None):
    future = candidate_pairs(pc, 2026, max_pairs=16000)
    if future.empty:
        return future
    future = future.copy()
    if models is not None:
        future["ml_score"] = predict_ml_adoption(models, future)
    else:
        future["ml_score"] = np.nan
    future["graph_adoption_score"] = graph_rank_score(future)
    # No future labels exist for post-2026 candidates; use graph score plus a
    # small actionability prior that favours cross-layer mechanism-system links.
    cross_layer = (future["i_type"] != future["j_type"]).astype(float)
    mechanism_donor = future["i_type"].isin([
        "transport_mechanism",
        "solvation_entropy",
        "phase_or_species_transition",
        "electrode_interface",
    ]).astype(float)
    same_material_penalty = (
        (future["i_type"] == "material_system") & (future["j_type"] == "material_system")
    ).astype(float)
    future["actionability_score"] = (
        future["graph_adoption_score"]
        + 0.10 * cross_layer
        + 0.08 * mechanism_donor
        - 0.18 * same_material_penalty
    )
    ml_rank = future["ml_score"].rank(pct=True).fillna(0).to_numpy()
    graph_rank = future["graph_adoption_score"].rank(pct=True).to_numpy()
    future["hybrid_adoption_score"] = 0.75 * graph_rank + 0.25 * ml_rank
    future["hybrid_actionability_score"] = (
        future["hybrid_adoption_score"]
        + 0.10 * cross_layer
        + 0.08 * mechanism_donor
        - 0.18 * same_material_penalty
    )
    future = future.sort_values("hybrid_actionability_score", ascending=False)
    future.to_csv(OUT / "tg_post2026_candidate_directions.csv", index=False)
    return future


def main():
    papers, pc = make_paper_concepts()
    pc.to_csv(OUT / "tg_prediction_typed_concepts.csv", index=False)

    train_parts = []
    window_rows = []
    for cutoff in range(2014, 2022):
        horizon = (cutoff + 1, min(cutoff + 3, 2023))
        s = candidate_pairs(pc, cutoff, max_pairs=9000)
        if s.empty:
            continue
        s = add_labels(pc, s, horizon)
        window_rows.append({
            "cutoff_year": cutoff,
            "future_window": f"{horizon[0]}-{horizon[1]}",
            "n_samples": len(s),
            "n_positive": int(s["future_TG_edge_label"].sum()),
            "positive_rate": float(s["future_TG_edge_label"].mean()) if len(s) else 0,
        })
        train_parts.append(s)
    train_df = pd.concat(train_parts, ignore_index=True).drop_duplicates([
        "cutoff_year", "concept_i_ite_donor", "concept_j_tg_anchor"
    ])
    pd.DataFrame(window_rows).to_csv(OUT / "tg_adoption_window_summary.csv", index=False)
    test_df = add_labels(pc, candidate_pairs(pc, 2022, max_pairs=12000), (2023, 2026))

    train_df.to_csv(OUT / "tg_adoption_train_samples.csv", index=False)
    test_df.to_csv(OUT / "tg_adoption_test_samples_2022_to_2026.csv", index=False)

    if train_df["future_TG_edge_label"].sum() < 2 or test_df["future_TG_edge_label"].sum() < 1:
        raise RuntimeError("Not enough positive future TG links for the demo. Loosen concept filters.")

    scored, metrics, feature_cols, models = train_and_score(train_df, test_df)
    scored.to_csv(OUT / "tg_adoption_scored_candidates_2022_to_2026.csv", index=False)
    pd.DataFrame([metrics]).to_csv(OUT / "tg_adoption_backtest_metrics.csv", index=False)
    post2026 = score_post2026_candidates(pc, models)

    plot_top(scored)
    write_summary(pc, train_df, scored, metrics)
    if not post2026.empty:
        post2026.head(50).to_csv(OUT / "tg_post2026_top50_candidate_directions.csv", index=False)
    print("typed concepts", pc["concept"].nunique(), "train", len(train_df), "test", len(test_df), "test positives", int(test_df["future_TG_edge_label"].sum()))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
