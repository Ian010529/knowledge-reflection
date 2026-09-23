from pathlib import Path
import math
import re
import sys

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS


sys.path.insert(0, "/Users/ryan/Documents/Codex/2026-07-20/t-he/work")
import tg_adoption_prediction_demo as curated


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
DATA_DIR = Path("/Users/ryan/Documents/Codex/2026-07-15/r/work")
OUT = ROOT / "work" / "open_concepts_iter"
OUT.mkdir(exist_ok=True)

SOURCES = [
    (DATA_DIR / "TG_first333_material_mechanism.csv", "TG"),
    (DATA_DIR / "iTE1_first1000_material_mechanism.csv", "iTE1"),
    (DATA_DIR / "iTE2_first711_material_mechanism.csv", "iTE2"),
]

DOMAIN_RE = re.compile(
    r"redox|ion|ionic|cation|anion|solvation|hydration|entropy|soret|thermodiffusion|"
    r"diffusion|migration|transport|conductivity|hydrogel|ionogel|eutogel|eutectic|"
    r"polymer|cellulose|mxene|pedot|pva|pam|gelatin|gelma|electrode|interface|"
    r"charge transfer|charge-transfer|crystallization|phase|water|moisture|humidity|"
    r"nanochannel|channel|complexation|coordination|organohydrogel|chaotropic|"
    r"photothermal|refrigeration|thermal charging|liquid|solvent|membrane|selective|"
    r"ferrocyanide|ferricyanide|iodide|triiodide|quinone|viologen|tempo|pyrazine|"
    r"deep eutectic|ionic liquid|mixed ionic|electronic conductor|thermogalvanic|"
    r"density functional|first principles|x-ray|x ray|diffraction|microscopy|"
    r"spectroscopy|sem|tem|xps|dft|power density|seebeck|thermopower|figure of merit|"
    r"conversion efficiency|mechanical property|electrical property|thermal property"
)

OBVIOUS_ERROR_RE = re.compile(
    r"elsevier rights|rights reserved|copyright|springer nature|licensed under|"
    r"\barticle\b|\babstract\b|\bkeywords\b|\bavailable online\b|"
    r"\b\d{3,}\b|xx+|^\W+$|"
    r"\b(various|practical|potential|possible|important|promising) applications?\b|"
    r"\b(low|higher|lower|improved|enhance|enhances|boosting|control|conversion) ionic\b|"
    r"\b(principles calculation|functional theory density|theory density functional)\b|"
    r"\b(mw|k-1|k-2|cm-1|s/cm|m-1)\b|"
    r"\b(great attention|temperature similar|applications including|applications paper|"
    r"calculations investigate|systems exhibit|hydrogel exhibit|studied temperature|"
    r"working conditions|temperature region|constant temperature|solution temperature|"
    r"temperature heat|temperature field|temperature t-c|equation state|"
    r"application scenarios|application potential|calculations performed|hydrogel exhibits|"
    r"effect thermogalvanic|difference redox|thermoelectric property ionic)\b"
)

BAD_FRAGMENT_RE = re.compile(
    r"^(of|in|on|for|with|from|by|using|based|enabled|towards|toward|and|or|the|a|an)\b|"
    r"\b(of|in|on|for|with|from|by|using|based|enabled|towards|toward|and|or|the|a|an)$|"
    r"^(high|low|enhanced|efficient|novel|new|excellent|superior)\b$"
)

CUSTOM_STOP = set(ENGLISH_STOP_WORDS) | {
    "using",
    "based",
    "enabled",
    "towards",
    "toward",
    "study",
}

NMI_STYLE_NORMALIZATIONS = [
    (r".*\bdensity functional theory\b.*", "density functional theory"),
    (r".*\bdensity functional\b.*", "density functional theory"),
    (r"\bfunctional theory\b", "density functional theory"),
    (r".*\bfirst principles calculation.*", "first principles calculation"),
    (r".*\bprinciples calculations?\b.*", "first principles calculation"),
    (r".*\bfirst principles\b.*", "first principles calculation"),
    (r".*\bx ray photoelectron spectroscopy\b.*", "x ray photoelectron spectroscopy"),
    (r".*\bphotoelectron spectroscopy\b.*", "x ray photoelectron spectroscopy"),
    (r".*\bscanning electron microscopy\b.*", "scanning electron microscopy"),
    (r".*\btransmission electron microscopy\b.*", "transmission electron microscopy"),
    (r".*\belectrochemical impedance spectroscopy\b.*", "electrochemical impedance spectroscopy"),
    (r".*\braman spectroscopy\b.*", "raman spectroscopy"),
    (r".*\binfrared spectroscopy\b.*", "infrared spectroscopy"),
    (r".*\blow thermal conductivity\b.*", "low thermal conductivity"),
    (r".*\b(reduction|reducing) thermal conductivity\b.*", "thermal conductivity reduction"),
    (r".*\bx ray diffraction\b.*", "x ray diffraction"),
    (r"\bx[- ]ray\b", "x ray"),
    (r"\bxrd\b", "x ray diffraction"),
    (r"\bxps\b", "x ray photoelectron spectroscopy"),
    (r"\bsem\b", "scanning electron microscopy"),
    (r"\btem\b", "transmission electron microscopy"),
    (r"\bdft\b", "density functional theory"),
    (r"\bfirst[- ]principles\b", "first principles"),
    (r"\bferri[-/ ]ferrocyanide\b", "ferri/ferrocyanide"),
    (r"\bferricyanide/ferrocyanide\b", "ferri/ferrocyanide"),
    (r"\bferrocyanide/ferricyanide\b", "ferri/ferrocyanide"),
    (r"\bi[-/ ]/i3[-]?\b", "iodide/triiodide"),
    (r"\bpedot[ -]?pss\b", "pedot:pss"),
    (r"\bti3c2tx\b", "ti3c2tx mxene"),
]

SINGULAR_NORMALIZATIONS = [
    (r"\bionic liquids\b", "ionic liquid"),
    (r"\bredox couples\b", "redox couple"),
    (r"\bredox reactions\b", "redox reaction"),
    (r"\bhydrogels\b", "hydrogel"),
    (r"\bionogels\b", "ionogel"),
    (r"\beutogels\b", "eutogel"),
    (r"\belectrodes\b", "electrode"),
    (r"\binterfaces\b", "interface"),
    (r"\bpolymers\b", "polymer"),
    (r"\bnanochannels\b", "nanochannel"),
    (r"\bproperties\b", "property"),
    (r"\bmechanisms\b", "mechanism"),
    (r"\bsolvation shells\b", "solvation shell"),
    (r"\bionic seebeck coefficients\b", "ionic seebeck coefficient"),
]


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = re.sub(r"[^a-z0-9+\-/():., ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


MANUAL_TYPE_BY_NORMALIZED_LABEL = {
    clean_text(label): typ for label, (typ, _pat) in curated.MANUAL_CONCEPTS.items()
}


def normalize_phrase(phrase):
    phrase = clean_text(phrase)
    for pattern, repl in NMI_STYLE_NORMALIZATIONS:
        phrase = re.sub(pattern, repl, phrase)
    phrase = re.sub(r"\b(high performance|high-performance|novel|efficient|enhanced|excellent|superior)\b", " ", phrase)
    for pattern, repl in SINGULAR_NORMALIZATIONS:
        phrase = re.sub(pattern, repl, phrase)
    phrase = re.sub(r"\b(ms cm-1|ms cm|s cm-1|s cm)\b", "conductivity", phrase)
    phrase = re.sub(r"\s+", " ", phrase).strip(" ,.;:-")
    words = phrase.split()
    while words and words[0] in CUSTOM_STOP:
        words = words[1:]
    while words and words[-1] in CUSTOM_STOP:
        words = words[:-1]
    return " ".join(words)


def good_phrase(phrase):
    phrase = normalize_phrase(phrase)
    if not phrase:
        return False
    words = phrase.split()
    if len(words) < 2 or len(words) > 7:
        return False
    if len(phrase) < 9 or len(phrase) > 86:
        return False
    if re.search(r"\b[a-z]+ed\s+(ionic|thermal|electrical|redox|seebeck|conductivity)\b", phrase):
        return False
    if BAD_FRAGMENT_RE.search(phrase):
        return False
    if OBVIOUS_ERROR_RE.search(phrase):
        return False
    if not DOMAIN_RE.search(phrase):
        return False
    if sum(1 for w in words if len(w) <= 2) > 2:
        return False
    if len(set(words)) <= 1:
        return False
    return True


def phrase_type(phrase):
    normalized = clean_text(phrase)
    if normalized in MANUAL_TYPE_BY_NORMALIZED_LABEL:
        return MANUAL_TYPE_BY_NORMALIZED_LABEL[normalized]
    if re.search(r"redox couple|redox reaction|iodide/triiodide|ferri/ferrocyanide|fe2\+/?3|fe2\+/?fe3", phrase):
        return "redox_chemistry"
    if re.search(r"charge transfer|redox kinetics|electrode potential|metal electrode|hot electrode|cold electrode|platinum electrode", phrase):
        return "electrode_interface"
    if re.search(r"solvation shell|reaction entropy|redox entropy|solvation entropy|hydration shell", phrase):
        return "solvation_entropy"
    if re.search(r"eastman entropy|electrostatic interaction", phrase):
        return "solvation_entropy"
    if re.search(r"ion selectivity|ion transport|ion diffusion|thermal migration|transport phenomena|transport pathway|mass transport", phrase):
        return "transport_mechanism"
    if re.search(r"density functional|first principles|machine learning|neural network|support vector", phrase):
        return "computational_method"
    if re.search(r"x ray|diffraction|microscopy|spectroscopy|ftir|raman|photoelectron|impedance|voltammetry|calorimetry", phrase):
        return "characterization_method"
    if re.search(r"seebeck|thermopower|power density|power factor|conversion efficiency|conductivity|figure of merit|mechanical property|electrical property|thermal property|tensile|stability", phrase):
        return "property_metric"
    return curated.concept_type(phrase)


def read_all():
    frames = []
    for path, source in SOURCES:
        frames.append(curated.read_source(path, source))
    papers = pd.concat(frames, ignore_index=True)
    papers = papers[papers["year"].between(1990, 2026)].copy()
    papers["full_text"] = (
        papers["title"].fillna("")
        + ". "
        + papers["abstract"].fillna("")
        + ". "
        + papers["material"].fillna("")
        + ". "
        + papers["mechanism"].fillna("")
    ).map(clean_text)
    return papers


def build_candidate_vocabulary(papers):
    vectorizer = CountVectorizer(
        ngram_range=(2, 5),
        min_df=2,
        max_df=0.22,
        stop_words=list(CUSTOM_STOP),
        token_pattern=r"(?u)\b[a-z][a-z0-9+\-/]{1,}\b",
    )
    X = vectorizer.fit_transform(papers["full_text"])
    terms = np.array(vectorizer.get_feature_names_out())
    df = np.asarray((X > 0).sum(axis=0)).ravel()
    total = len(papers)

    rows = []
    for term, n_docs in zip(terms, df):
        phrase = normalize_phrase(term)
        if not good_phrase(phrase):
            continue
        type_ = phrase_type(phrase)
        idf = math.log((1 + total) / (1 + n_docs)) + 1
        specificity = min(len(set(phrase.split()) - CUSTOM_STOP), 6) / 6
        score = n_docs * idf * (1 + specificity)
        rows.append({"concept": phrase, "concept_type": type_, "doc_freq": int(n_docs), "score": score})

    vocab = pd.DataFrame(rows)
    if vocab.empty:
        return vocab
    vocab = (
        vocab.groupby(["concept", "concept_type"], as_index=False)
        .agg(doc_freq=("doc_freq", "max"), score=("score", "max"))
        .sort_values("score", ascending=False)
    )

    # Add curated concepts so the open layer remains aligned with the interpretable layer.
    curated_rows = []
    for row in papers.itertuples():
        extracted = curated.extract_phrases(row)
        for c, typ in extracted.items():
            c = normalize_phrase(c)
            if c and c not in curated.GENERIC:
                curated_rows.append({"concept": c, "concept_type": phrase_type(c), "doc_freq": 999999, "score": 999999.0})
    if curated_rows:
        cdf = pd.DataFrame(curated_rows).groupby(["concept", "concept_type"], as_index=False).size()
        cdf = cdf.rename(columns={"size": "doc_freq"})
        cdf["score"] = 999999.0
        vocab = pd.concat([vocab, cdf], ignore_index=True).sort_values("score", ascending=False).drop_duplicates("concept")

    return vocab


def split_background_and_recommendation(selected):
    selected = selected.copy()
    high_degree_cutoff = selected["doc_freq"].quantile(0.92)
    min_candidate_score = 100
    overly_generic = selected["concept"].str.fullmatch(
        r"(thermoelectric|thermogalvanic|ionic|thermal|electrical|mechanical|chemical) "
        r"(material|property|performance|device|effect|application|system)s?",
        na=False,
    )
    selected["graph_role"] = "background"
    selected.loc[
        (selected["doc_freq"] <= high_degree_cutoff)
        & ((selected["score"] >= min_candidate_score) | (selected["score"] >= 999999))
        & ~overly_generic
        & ~selected["concept_type"].isin(["characterization_method", "computational_method"]),
        "graph_role",
    ] = "recommendation_candidate"
    return selected


def assign_concepts_to_papers(papers, vocab, max_vocab=1500):
    selected = vocab.sort_values(["score", "doc_freq"], ascending=False).head(max_vocab).copy()
    selected = split_background_and_recommendation(selected)
    concepts = selected["concept"].tolist()
    concept_type = selected.set_index("concept")["concept_type"].to_dict()
    graph_role = selected.set_index("concept")["graph_role"].to_dict()
    patterns = [(c, re.compile(r"(?<![a-z0-9])" + re.escape(c) + r"(?![a-z0-9])")) for c in concepts]

    rows = []
    for row in papers.itertuples():
        text = row.full_text
        matched = []
        for concept, pat in patterns:
            if pat.search(text):
                matched.append(concept)
        # Cap very noisy papers while preserving higher-scoring terms.
        if len(matched) > 45:
            order = selected[selected["concept"].isin(matched)].sort_values("score", ascending=False)["concept"].tolist()
            matched = order[:45]
        for concept in matched:
            rows.append(
                {
                    "paper_id": row.paper_id,
                    "source": row.source,
                    "year": row.year,
                    "title": row.title,
                    "doi": row.doi,
                    "concept": concept,
                    "concept_type": concept_type.get(concept, phrase_type(concept)),
                    "graph_role": graph_role.get(concept, "background"),
                }
            )
    pc = pd.DataFrame(rows).drop_duplicates(["paper_id", "concept"])
    return selected, pc


def summarize(pc, selected):
    pc_ite = pc[pc["source"].isin(["iTE1", "iTE2"])]
    pc_tg = pc[pc["source"] == "TG"]
    ite = set(pc_ite["concept"])
    tg = set(pc_tg["concept"])
    summary = {
        "selected_vocab": len(selected),
        "paper_concept_rows": len(pc),
        "total_unique_concepts_used": pc["concept"].nunique(),
        "iTE_unique_concepts": len(ite),
        "TG_unique_concepts": len(tg),
        "shared_concepts": len(ite & tg),
        "iTE_only_concepts": len(ite - tg),
        "TG_only_concepts": len(tg - ite),
        "iTE_papers_with_concepts": pc_ite["paper_id"].nunique(),
        "TG_papers_with_concepts": pc_tg["paper_id"].nunique(),
    }
    type_rows = []
    for typ in sorted(pc["concept_type"].dropna().unique()):
        i = set(pc_ite[pc_ite["concept_type"] == typ]["concept"])
        t = set(pc_tg[pc_tg["concept_type"] == typ]["concept"])
        type_rows.append(
            {
                "concept_type": typ,
                "iTE_unique": len(i),
                "TG_unique": len(t),
                "shared": len(i & t),
                "iTE_only": len(i - t),
                "TG_only": len(t - i),
            }
        )
    return pd.DataFrame([summary]), pd.DataFrame(type_rows)


def summarize_roles(pc):
    if pc.empty:
        return pd.DataFrame()
    return (
        pc.groupby(["graph_role", "concept_type"], as_index=False)
        .agg(
            unique_concepts=("concept", "nunique"),
            paper_concept_rows=("concept", "size"),
            papers=("paper_id", "nunique"),
        )
        .sort_values(["graph_role", "unique_concepts"], ascending=[True, False])
    )


def main():
    papers = read_all()
    vocab = build_candidate_vocabulary(papers)
    vocab.to_csv(OUT / "open_candidate_vocabulary_scored.csv", index=False)
    selected, pc = assign_concepts_to_papers(papers, vocab, max_vocab=1500)
    selected.to_csv(OUT / "open_nmi_selected_vocabulary_1500.csv", index=False)
    pc.to_csv(OUT / "open_nmi_paper_concepts_1500.csv", index=False)
    selected[selected["graph_role"] == "recommendation_candidate"].to_csv(
        OUT / "open_nmi_recommendation_candidates.csv", index=False
    )
    summary, by_type = summarize(pc, selected)
    role_summary = summarize_roles(pc)
    summary.to_csv(OUT / "open_nmi_concept_summary.csv", index=False)
    by_type.to_csv(OUT / "open_nmi_concept_summary_by_type.csv", index=False)
    role_summary.to_csv(OUT / "open_nmi_concept_summary_by_role.csv", index=False)
    print(summary.T.to_string(header=False))
    print("\nBy type")
    print(by_type.to_string(index=False))
    print("\nTop vocabulary")
    print(selected.head(50).to_string(index=False))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
