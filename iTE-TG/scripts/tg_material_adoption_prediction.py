"""Predict future TG material combinations from non-overlapping iTE papers.

The unit of prediction is a pair:
    iTE-enriched donor material + established TG anchor material
that has not co-occurred in TG before the cutoff year.
"""

from itertools import combinations, product
from pathlib import Path
import re

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "source_tables"
OUT = ROOT / "figures_and_results" / "tg_material_adoption_iter"
OUT.mkdir(parents=True, exist_ok=True)

MATERIAL_RULES = {
    "PVA polymer matrix": r"\bpva\b|poly\s*\(vinyl alcohol\)|polyvinyl alcohol",
    "PAM/polyacrylamide matrix": r"\bpam\b|polyacrylamide",
    "PNIPAM thermoresponsive polymer": r"pnipam|poly\(n-isopropylacrylamide\)",
    "GelMA matrix": r"\bgelma\b|gelatin methacryloyl",
    "gelatin matrix": r"\bgelatin\b",
    "alginate matrix": r"\balginate\b",
    "chitosan matrix": r"\bchitosan\b",
    "cellulose nanofiber matrix": r"cellulose|nanocellulose|bacterial cellulose|cotton",
    "zwitterionic polymer": r"zwitterion|zwitterionic|\bsbma\b|sulfobetaine",
    "PEDOT:PSS conductor": r"pedot\s*:?\s*pss",
    "polyaniline conductor": r"\bpani\b|polyaniline",
    "carbon nanotube scaffold": r"\bcnt\b|swcnt|mwcnt|carbon nanotube",
    "graphene/graphene-oxide scaffold": r"graphene|graphene oxide|\bgo\b",
    "MXene scaffold": r"mxene|ti3c2",
    "MoS2 scaffold": r"\bmos2\b|molybdenum disulfide",
    "porous carbon electrode": r"carbon cloth|carbon felt|carbon aerogel|activated carbon|porous carbon",
    "metal-oxide electrode": r"metal oxide|mno2|tio2|wo3|v2o5|ruo2",
    "Prussian-blue/hexacyanoferrate electrode": r"prussian blue|hexacyanoferrate|cohcf|cuhcf|nihcf",
    "Fe2+/Fe3+ redox electrolyte": r"fe2\+|fe3\+|ferrous|ferric",
    "ferri/ferrocyanide electrolyte": r"ferri.?ferrocyanide|fe\(cn\)|\[fe\(cn\)6\]|k3fe\(cn\)6|k4fe\(cn\)6",
    "iodide/triiodide electrolyte": r"triiodide|i3-|\bi-/i3|\bki\b|\bnai\b.*iod|iodide",
    "Cu-based redox electrolyte": r"cu2\+|cu\+/cu2|copper redox|cucl2|cu\(en\)",
    "quinone redox electrolyte": r"hydroquinone|benzoquinone|\bhq/bq\b|quinone",
    "TEMPO/viologen organic redox": r"\btempo\b|viologen",
    "Li-salt electrolyte": r"licl|litfsi|liclo4|lithium salt|li\+",
    "Na-salt electrolyte": r"nacl|natfsi|naclo4|sodium salt|na\+",
    "K-salt electrolyte": r"\bkcl\b|\bkoh\b|potassium salt|k\+",
    "ionic-liquid electrolyte": r"ionic liquid|imidazolium|pyridinium|piperidinium|emim|bmim",
    "deep-eutectic electrolyte": r"deep eutectic|\bdes\b|eutogel",
    "ethylene-glycol organohydrogel": r"ethylene glycol|\beg\b",
    "glycerol organohydrogel": r"glycerol|glycerin",
    "acetonitrile/nitrile solvent": r"acetonitrile|nitrile solvent|\bacn\b",
    "cyclodextrin host": r"cyclodextrin|alpha-cd|beta-cd|α-cyclodextrin|β-cyclodextrin",
    "crown-ether host": r"crown ether|crown-ether|18-crown-6",
    "silica/inorganic nanoparticle filler": r"silica|sio2|inorganic nanoparticle",
    "biomass-derived matrix": r"biomass|lignin|wood|bamboo|silk|protein",
}


def norm_doi(value):
    s = str(value or "").strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    return re.sub(r"\s+", "", s)


def norm_title(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def read_table(name, source):
    d = pd.read_csv(DATA / name).rename(columns={
        "文章名": "title", "期刊名": "journal", "DOI": "doi", "年份": "year",
        "摘要": "abstract", "材料": "material", "机制": "mechanism",
    })
    for c in ["title", "journal", "doi", "abstract", "material", "mechanism"]:
        d[c] = d[c].fillna("")
    d["year"] = pd.to_numeric(d["year"], errors="coerce")
    d = d.dropna(subset=["year"]).copy()
    d["year"] = d["year"].astype(int)
    d["source"] = source
    d["doi_norm"] = d["doi"].map(norm_doi)
    d["title_norm"] = d["title"].map(norm_title)
    return d


def load_and_deduplicate():
    tg = read_table("TG_first333_material_mechanism.csv", "TG")
    ite = pd.concat([
        read_table("iTE1_first1000_material_mechanism.csv", "iTE1"),
        read_table("iTE2_first711_material_mechanism.csv", "iTE2"),
    ], ignore_index=True)

    tg_dois = set(tg.loc[tg["doi_norm"] != "", "doi_norm"])
    tg_titles = set(tg.loc[tg["title_norm"] != "", "title_norm"])
    ite["overlap_by_doi"] = ite["doi_norm"].ne("") & ite["doi_norm"].isin(tg_dois)
    ite["overlap_by_title"] = ite["title_norm"].ne("") & ite["title_norm"].isin(tg_titles)
    overlap = ite[ite["overlap_by_doi"] | ite["overlap_by_title"]].copy()
    overlap.to_csv(OUT / "ite_removed_tg_overlap.csv", index=False)

    clean = ite[~(ite["overlap_by_doi"] | ite["overlap_by_title"])].copy()
    # Remove duplicates between iTE1 and iTE2, preferring the first occurrence.
    has_doi = clean["doi_norm"].ne("")
    with_doi = clean[has_doi].drop_duplicates("doi_norm")
    without_doi = clean[~has_doi].drop_duplicates("title_norm")
    clean = pd.concat([with_doi, without_doi], ignore_index=True)

    audit = pd.DataFrame([{
        "tg_records": len(tg),
        "ite_records_raw": len(ite),
        "ite_removed_tg_overlap": len(overlap),
        "ite_overlap_unique_doi": overlap.loc[overlap["doi_norm"] != "", "doi_norm"].nunique(),
        "ite_overlap_unique_title": overlap["title_norm"].nunique(),
        "ite_records_after_tg_exclusion_and_internal_dedup": len(clean),
    }])
    audit.to_csv(OUT / "deduplication_audit.csv", index=False)
    papers = pd.concat([tg, clean], ignore_index=True)
    papers = papers[papers["year"].between(1990, 2026)].copy()
    papers["paper_id"] = [f"P{i:05d}" for i in range(len(papers))]
    return papers, audit


def extract_materials(text):
    s = str(text or "").lower()
    return [label for label, pattern in MATERIAL_RULES.items() if re.search(pattern, s)]


def make_paper_materials(papers):
    rows = []
    for r in papers.itertuples():
        for material in extract_materials(r.material):
            rows.append({
                "paper_id": r.paper_id, "source": r.source, "year": r.year,
                "title": r.title, "doi": r.doi, "material": material,
            })
    pm = pd.DataFrame(rows).drop_duplicates(["paper_id", "material"])
    counts = pm.groupby("material")["paper_id"].nunique()
    pm = pm[pm["material"].map(counts).between(2, 300)].copy()
    return pm


def graph_until(pm, cutoff, sources=None):
    d = pm[pm["year"] <= cutoff]
    if sources is not None:
        d = d[d["source"].isin(sources)]
    g = nx.Graph()
    for _, x in d.groupby("paper_id"):
        mats = sorted(x["material"].unique())
        g.add_nodes_from(mats)
        for u, v in combinations(mats, 2):
            if g.has_edge(u, v):
                g[u][v]["weight"] += 1
            else:
                g.add_edge(u, v, weight=1)
    return g


def first_year(pm, material, sources, cutoff):
    d = pm[(pm["material"] == material) & pm["source"].isin(sources) & (pm["year"] <= cutoff)]
    return None if d.empty else int(d["year"].min())


def candidate_pairs(pm, cutoff):
    past = pm[pm["year"] <= cutoff]
    ite_sources = ["iTE1", "iTE2"]
    ni = past[past["source"].isin(ite_sources)].groupby("material")["paper_id"].nunique().to_dict()
    nt = past[past["source"] == "TG"].groupby("material")["paper_id"].nunique().to_dict()
    donors = [m for m, n in ni.items() if n >= 2 and nt.get(m, 0) <= 8]
    anchors = [m for m, n in nt.items() if n >= 2]
    gall, gtg, gite = graph_until(pm, cutoff), graph_until(pm, cutoff, ["TG"]), graph_until(pm, cutoff, ite_sources)
    rows = []
    seen_unordered = set()
    for u, v in product(donors, anchors):
        pair_key = tuple(sorted((u, v)))
        if u == v or pair_key in seen_unordered or gtg.has_edge(u, v):
            continue
        try:
            dist = nx.shortest_path_length(gall, u, v)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            dist = 12
        common = len(list(nx.common_neighbors(gall, u, v))) if u in gall and v in gall else 0
        aa = next(nx.adamic_adar_index(gall, [(u, v)]))[2] if u in gall and v in gall else 0
        iu, tu = first_year(pm, u, ite_sources, cutoff), first_year(pm, u, ["TG"], cutoff)
        lead = cutoff - iu + 1 if iu is not None and tu is None else max(0, (tu or cutoff) - (iu or cutoff))
        rows.append({
            "cutoff_year": cutoff, "ite_donor_material": u, "tg_anchor_material": v,
            "u_degree_all": gall.degree(u) if u in gall else 0,
            "v_degree_all": gall.degree(v) if v in gall else 0,
            "u_degree_tg": gtg.degree(u) if u in gtg else 0,
            "v_degree_tg": gtg.degree(v) if v in gtg else 0,
            "u_degree_ite": gite.degree(u) if u in gite else 0,
            "v_degree_ite": gite.degree(v) if v in gite else 0,
            "common_neighbors": common, "adamic_adar": aa,
            "preferential_attachment": (gall.degree(u) if u in gall else 0) * (gall.degree(v) if v in gall else 0),
            "shortest_path": min(dist, 12), "ite_lead_years": lead,
            "ite_count": ni.get(u, 0), "tg_donor_count": nt.get(u, 0), "tg_anchor_count": nt.get(v, 0),
        })
        seen_unordered.add(pair_key)
    return pd.DataFrame(rows).drop_duplicates(["ite_donor_material", "tg_anchor_material"])


def add_labels(pm, candidates, start, end):
    future = pm[(pm["source"] == "TG") & pm["year"].between(start, end)]
    paper_sets = [(set(g["material"]), g["title"].iloc[0]) for _, g in future.groupby("paper_id")]
    labels, examples = [], []
    for r in candidates.itertuples():
        hits = [title for mats, title in paper_sets if r.ite_donor_material in mats and r.tg_anchor_material in mats]
        labels.append(int(bool(hits)))
        examples.append(hits[0] if hits else "")
    out = candidates.copy()
    out["future_TG_material_pair_label"] = labels
    out["future_example_title"] = examples
    out["future_window"] = f"{start}-{end}"
    return out


FEATURES = [
    "u_degree_all", "v_degree_all", "u_degree_tg", "v_degree_tg", "u_degree_ite", "v_degree_ite",
    "common_neighbors", "adamic_adar", "preferential_attachment", "shortest_path",
    "ite_lead_years", "ite_count", "tg_donor_count", "tg_anchor_count",
]


def rank_score(df):
    r = lambda x: pd.Series(x).rank(pct=True).to_numpy()
    return (r(df["preferential_attachment"]) + .45*r(df["adamic_adar"]) +
            .35*r(df["common_neighbors"]) + .20*r(-df["shortest_path"]) +
            .15*r(df["ite_lead_years"]))


def fit_and_score(train, test):
    xtr, ytr = train[FEATURES].fillna(0), train["future_TG_material_pair_label"].to_numpy()
    xte, yte = test[FEATURES].fillna(0), test["future_TG_material_pair_label"].to_numpy()
    scaler = StandardScaler().fit(xtr)
    lr = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=17).fit(scaler.transform(xtr), ytr)
    rf = RandomForestClassifier(n_estimators=600, min_samples_leaf=4, class_weight="balanced_subsample",
                                random_state=17, n_jobs=-1).fit(xtr, ytr)
    ml = .5*lr.predict_proba(scaler.transform(xte))[:, 1] + .5*rf.predict_proba(xte)[:, 1]
    graph = rank_score(test)
    hybrid = .65*pd.Series(graph).rank(pct=True).to_numpy() + .35*pd.Series(ml).rank(pct=True).to_numpy()
    out = test.copy()
    out["ml_score"], out["graph_score"], out["hybrid_score"] = ml, graph, hybrid
    # Material-pair backtests show that topology alone is weak; keep the hybrid
    # as a diagnostic but use the supervised probability as the formal rank.
    out["material_prediction_score"] = ml
    metrics = {"n_train": len(train), "train_positive": int(ytr.sum()), "n_test": len(test), "test_positive": int(yte.sum())}
    for name, score in [("ml", ml), ("graph", graph), ("hybrid", hybrid)]:
        metrics[f"{name}_roc_auc"] = roc_auc_score(yte, score)
        metrics[f"{name}_average_precision"] = average_precision_score(yte, score)
        for k in [10, 25, 50]:
            idx = np.argsort(score)[::-1][:min(k, len(score))]
            metrics[f"{name}_precision_at_{k}"] = float(yte[idx].mean())
    return out.sort_values("material_prediction_score", ascending=False), metrics, (scaler, lr, rf)


def main():
    papers, audit = load_and_deduplicate()
    pm = make_paper_materials(papers)
    pm.to_csv(OUT / "paper_materials_after_dedup.csv", index=False)
    train_parts, windows = [], []
    for cutoff in range(2014, 2022):
        c = candidate_pairs(pm, cutoff)
        if c.empty:
            continue
        x = add_labels(pm, c, cutoff + 1, min(cutoff + 3, 2023))
        train_parts.append(x)
        windows.append({"cutoff": cutoff, "n": len(x), "positive": int(x["future_TG_material_pair_label"].sum())})
    train = pd.concat(train_parts, ignore_index=True).drop_duplicates(
        ["cutoff_year", "ite_donor_material", "tg_anchor_material"])
    test = add_labels(pm, candidate_pairs(pm, 2022), 2023, 2026)
    train.to_csv(OUT / "material_train_samples.csv", index=False)
    test.to_csv(OUT / "material_test_samples_2022_to_2026.csv", index=False)
    pd.DataFrame(windows).to_csv(OUT / "rolling_window_summary.csv", index=False)
    if train["future_TG_material_pair_label"].sum() < 2 or test["future_TG_material_pair_label"].sum() < 1:
        raise RuntimeError("Too few positive material-pair events; revise material vocabulary.")
    scored, metrics, models = fit_and_score(train, test)
    scored.to_csv(OUT / "material_scored_backtest_2022_to_2026.csv", index=False)
    pd.DataFrame([metrics]).to_csv(OUT / "material_backtest_metrics.csv", index=False)

    future = candidate_pairs(pm, 2026)
    scaler, lr, rf = models
    ml = .5*lr.predict_proba(scaler.transform(future[FEATURES].fillna(0)))[:, 1] + .5*rf.predict_proba(future[FEATURES].fillna(0))[:, 1]
    graph = rank_score(future)
    future["ml_score"], future["graph_score"] = ml, graph
    future["hybrid_score"] = .65*pd.Series(graph).rank(pct=True).to_numpy() + .35*pd.Series(ml).rank(pct=True).to_numpy()
    future["material_prediction_score"] = future["ml_score"]
    future.sort_values("material_prediction_score", ascending=False).to_csv(OUT / "post2026_material_candidates.csv", index=False)
    print(audit.to_string(index=False))
    print(pd.DataFrame([metrics]).T.to_string(header=False))
    print("\nTop post-2026 material pairs")
    print(future.sort_values("material_prediction_score", ascending=False)[
        ["ite_donor_material", "tg_anchor_material", "material_prediction_score"]].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
