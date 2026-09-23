import csv
import math
import re
import textwrap
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.manifold import TSNE
from sklearn.preprocessing import normalize


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
DATA_DIR = Path("/Users/ryan/Documents/Codex/2026-07-15/r/work")
OUT = ROOT / "outputs"
WORK = ROOT / "work"
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)

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
    "axes.linewidth": 0.75,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
})


PALETTE = {
    "tg": "#5B8DB8",
    "ite": "#C89B5A",
    "shared": "#7B7B7B",
    "accent": "#B75F5A",
    "mechanism": "#7C9A68",
    "device": "#9A7BA8",
    "material": "#D08C60",
    "electrode": "#5B8A72",
    "redox": "#A55C6B",
    "medium": "#5E83A1",
    "neutral": "#D8D8D8",
    "dark": "#30343B",
}


CONCEPT_RULES = [
    ("ferri/ferrocyanide redox couple", "redox", r"ferri|ferrocyanide|fe\(cn\)|\[fe\(cn\)6\]|fecn"),
    ("Fe2+/Fe3+ redox couple", "redox", r"fe2\+|fe3\+|iron-based|ferric|ferrous"),
    ("iodide/triiodide redox couple", "redox", r"iodide|triiodide|i-/i3|polyiodide|iodine"),
    ("Cu/Cu2+ redox couple", "redox", r"cu/c|\bcu2\+|copper"),
    ("Zn/I redox chemistry", "redox", r"zinc-iodine|zn.*iod|zn plating|zinc.*thermal charging"),
    ("organic redox couple", "redox", r"tempo|viologen|quinone|pyrazine|organic redox|radical"),
    ("redox entropy", "mechanism", r"redox entropy|entropy change|reaction entropy|entropy.*redox"),
    ("solvation entropy", "mechanism", r"solvation entropy|solvation|solvent.*entropy|hydration entropy"),
    ("thermodiffusion", "mechanism", r"thermodiffusion|soret|thermal diffusion"),
    ("ion association/complexation", "mechanism", r"complexation|ion association|coordination|crystallization|ion-pair|ion pair"),
    ("electrode kinetics", "mechanism", r"redox kinetics|charge-transfer|charge transfer|electrode.*kinetic|reaction area"),
    ("mass transport", "mechanism", r"mass transfer|diffusion resistance|viscosity|convection|liquid-flow|microchannel"),
    ("phase transition", "mechanism", r"phase transition|solid-liquid|precipitation|crystallization|phase-change"),
    ("water activity/hydration", "mechanism", r"water activity|hydration|moisture|humidity|water binding"),
    ("gel confinement", "mechanism", r"confinement|gel network|polymer network|double-network|nanochannel|ion channel"),
    ("hydrogel electrolyte", "medium", r"hydrogel|gelatin|alginate|pva|pam|paam|gellan|bacterial cellulose|cellulose"),
    ("organohydrogel/eutogel", "medium", r"organohydrogel|eutogel|deep-eutectic|deep eutectic|des\b"),
    ("ionic liquid electrolyte", "medium", r"ionic liquid|imidazolium|tfsi"),
    ("aqueous electrolyte", "medium", r"aqueous|water|kcl|licl|lithium chloride"),
    ("anti-freezing electrolyte", "medium", r"anti-freez|antifreez|subzero|ethylene glycol|glycerol"),
    ("flexible/wearable device", "device", r"wearable|flexible|e-skin|skin|patch|dressing|body heat|facial|textile"),
    ("self-powered sensor", "device", r"self-powered|sensor|sensing|monitoring|recognition"),
    ("electrochemical refrigeration", "device", r"refrigeration|cooling"),
    ("thermal charging/storage", "device", r"thermal charging|energy storage|charging cell|storage"),
    ("solar heat harvesting", "device", r"solar|photothermal|evaporation|steam|light"),
    ("PV waste heat coupling", "device", r"photovoltaic|pv panel|concentrated pv|cpv"),
    ("microfluidic thermocell", "device", r"microchannel|liquid-flow|flow thermocell"),
    ("MXene", "material", r"mxene|ti3c2"),
    ("PEDOT:PSS", "material", r"pedot|pss"),
    ("cellulose scaffold", "material", r"cellulose|cotton|nanocellulose"),
    ("polymer matrix", "material", r"polymer|pva|pam|paam|alginate|gelatin|gellan|polyacrylamide"),
    ("carbon electrode", "electrode", r"carbon nanotube|cnt|graphene|carbon framework|carbon cloth|aerogel"),
    ("hierarchical/porous electrode", "electrode", r"hierarchical electrode|porous electrode|aerogel electrode|3d hierarchical"),
    ("MXene electrode/additive", "electrode", r"mxene|ti3c2"),
]

STOP_PHRASES = {
    "thermogalvanic", "thermoelectric", "ionic thermoelectric", "generator",
    "material", "materials", "device", "devices", "cell", "cells", "effect",
    "performance", "high", "low", "efficient", "based", "using",
}


def read_source(path, source):
    df = pd.read_csv(path)
    df["source"] = source
    df["year"] = pd.to_numeric(df["年份"], errors="coerce").astype("Int64")
    df["title"] = df["文章名"].fillna("")
    df["journal"] = df["期刊名"].fillna("")
    df["doi"] = df["DOI"].fillna("")
    df["abstract"] = df["摘要"].fillna("")
    df["material"] = df["材料"].fillna("")
    df["mechanism"] = df["机制"].fillna("")
    df["doc_id"] = [f"{source}_{i:04d}" for i in range(len(df))]
    return df[["doc_id", "source", "year", "title", "journal", "doi", "abstract", "material", "mechanism"]]


def norm_text(s):
    return re.sub(r"\s+", " ", str(s).lower()).strip()


def extract_rule_concepts(row):
    text = norm_text(" ".join([row.title, row.abstract, row.material, row.mechanism]))
    concepts = []
    cats = {}
    for concept, cat, pat in CONCEPT_RULES:
        if re.search(pat, text):
            concepts.append(concept)
            cats[concept] = cat
    return concepts, cats


def make_ngram_candidates(df, top_n=300):
    text = (df["material"].fillna("") + " " + df["mechanism"].fillna("")).map(norm_text)
    vectorizer = CountVectorizer(
        ngram_range=(2, 3),
        min_df=3,
        max_df=0.45,
        stop_words="english",
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9+\-/]{2,}\b",
    )
    X = vectorizer.fit_transform(text)
    terms = np.array(vectorizer.get_feature_names_out())
    counts = np.asarray(X.sum(axis=0)).ravel()
    order = counts.argsort()[::-1]
    out = []
    for idx in order:
        term = terms[idx]
        if any(p in term for p in STOP_PHRASES):
            continue
        if len(term) < 8:
            continue
        out.append((term, int(counts[idx])))
        if len(out) >= top_n:
            break
    return out, vectorizer, X


def assign_ngram_concepts(df, candidates):
    selected = []
    for term, count in candidates:
        if count >= 4:
            selected.append(term)
    selected = selected[:180]
    cats = {}
    for term in selected:
        if any(x in term for x in ["redox", "fe2", "fe3", "iodide", "triiodide", "ferrocyanide"]):
            cats[term] = "redox"
        elif any(x in term for x in ["entropy", "diffusion", "solvation", "complex", "kinetic", "transfer"]):
            cats[term] = "mechanism"
        elif any(x in term for x in ["hydrogel", "gel", "electrolyte", "solvent", "ionic liquid"]):
            cats[term] = "medium"
        elif any(x in term for x in ["sensor", "wearable", "cooling", "solar", "storage"]):
            cats[term] = "device"
        elif any(x in term for x in ["electrode", "carbon", "mxene"]):
            cats[term] = "electrode"
        else:
            cats[term] = "material"
    doc_terms = []
    for _, row in df.iterrows():
        text = norm_text(f"{row.title} {row.material} {row.mechanism}")
        found = [term for term in selected if term in text]
        doc_terms.append(found[:10])
    return doc_terms, cats


def period_label(year):
    y = int(year)
    if y <= 2015:
        return "<=2015"
    if y <= 2019:
        return "2016-2019"
    if y <= 2022:
        return "2020-2022"
    return "2023-2026"


def save_all(fig, stem):
    fig.savefig(str(OUT / f"{stem}.svg"), bbox_inches="tight")
    fig.savefig(str(OUT / f"{stem}.pdf"), bbox_inches="tight")
    fig.savefig(str(OUT / f"{stem}.png"), bbox_inches="tight", dpi=600)
    fig.savefig(str(OUT / f"{stem}.tiff"), bbox_inches="tight", dpi=600)
    plt.close(fig)


def build_graph(docs):
    G = nx.MultiGraph()
    for row in docs.itertuples():
        concepts = sorted(set(row.concepts))
        for c in concepts:
            G.add_node(c)
        for u, v in combinations(concepts, 2):
            G.add_edge(u, v, year=int(row.year), source=row.source, doc_id=row.doc_id)
    return G


def concept_first_year(docs, source=None):
    fy = {}
    for row in docs.itertuples():
        if source and row.source != source:
            continue
        for c in row.concepts:
            y = int(row.year)
            if c not in fy or y < fy[c]:
                fy[c] = y
    return fy


def concept_counts(docs, source=None):
    cnt = Counter()
    for row in docs.itertuples():
        if source and row.source != source:
            continue
        cnt.update(set(row.concepts))
    return cnt


def plot_bubble(tg_docs, cat_map):
    cnt = concept_counts(tg_docs, "TG")
    top = cnt.most_common(30)
    fig, ax = plt.subplots(figsize=(7.1, 4.2))
    ax.set_axis_off()
    cols = 5
    xs, ys = [], []
    for i in range(len(top)):
        r, c = divmod(i, cols)
        xs.append(c + 0.5 * (r % 2))
        ys.append(-r)
    xs = np.array(xs, dtype=float)
    ys = np.array(ys, dtype=float)
    xs = (xs - xs.mean()) / 2.65
    ys = (ys - ys.mean()) / 2.95 - 0.22
    sizes = np.array([c for _, c in top], dtype=float)
    sizes = 170 + 900 * (sizes - sizes.min()) / max(1, sizes.max() - sizes.min())
    for (concept, count), x, y, size in zip(top, xs, ys, sizes):
        cat = cat_map.get(concept, "material")
        ax.scatter(x, y, s=size, color=PALETTE.get(cat, PALETTE["neutral"]), alpha=0.72, lw=0.7, ec="white")
        label = concept.replace(" redox couple", "").replace(" electrolyte", "")
        label = "\n".join(textwrap.wrap(label, width=18, break_long_words=False))
        fs = 5.0 + 1.3 * math.sqrt(count / max(cnt.values()))
        ax.text(x, y, label, ha="center", va="center", fontsize=fs, color="#20242A", wrap=True)
    ax.text(-1.25, 1.02, "a", fontsize=12, fontweight="bold")
    ax.text(-1.12, 1.02, "TG concept cloud", fontsize=11, fontweight="bold")
    ax.text(-1.12, 0.90, "Bubble size: article count; colour: concept family", fontsize=7, color="#555")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.05, 1.15)
    save_all(fig, "tg_concept_cloud")


def plot_atlas(docs, cat_map):
    all_concepts = sorted({c for cs in docs["concepts"] for c in cs})
    doc_index = {d: i for i, d in enumerate(docs["doc_id"])}
    concept_index = {c: i for i, c in enumerate(all_concepts)}
    M = np.zeros((len(all_concepts), len(docs)), dtype=float)
    for row in docs.itertuples():
        j = doc_index[row.doc_id]
        for c in set(row.concepts):
            M[concept_index[c], j] = 1.0
    M = normalize(M, norm="l2", axis=1)
    n_comp = min(25, M.shape[1] - 1, M.shape[0] - 1)
    Z = TruncatedSVD(n_components=max(2, n_comp), random_state=3).fit_transform(M)
    if len(all_concepts) > 20:
        perplexity = min(20, max(5, (len(all_concepts) - 1) // 4))
        xy = TSNE(n_components=2, init="pca", learning_rate="auto", perplexity=perplexity, random_state=4).fit_transform(Z)
    else:
        xy = Z[:, :2]
    xy = (xy - xy.mean(axis=0)) / xy.std(axis=0)
    total = concept_counts(docs)
    tg = concept_counts(docs, "TG")
    ite = concept_counts(docs[docs["source"].isin(["iTE1", "iTE2"])])
    spec = np.array([(tg[c] + 1) / (tg[c] + ite[c] + 2) for c in all_concepts])
    freq = np.array([total[c] for c in all_concepts])
    colors = []
    for v in spec:
        if v > 0.62:
            colors.append(PALETTE["tg"])
        elif v < 0.34:
            colors.append(PALETTE["ite"])
        else:
            colors.append(PALETTE["shared"])
    fig, ax = plt.subplots(figsize=(7.1, 4.6))
    hb = ax.hexbin(xy[:, 0], xy[:, 1], C=freq, gridsize=24, reduce_C_function=np.sum, cmap="Greys", alpha=0.25, linewidths=0)
    ax.scatter(xy[:, 0], xy[:, 1], s=12 + 12 * np.sqrt(freq), c=colors, alpha=0.82, lw=0.25, ec="white")
    top_labels = [c for c, _ in concept_counts(docs).most_common(26)]
    for c in top_labels:
        i = concept_index[c]
        ax.text(xy[i, 0], xy[i, 1], c.replace(" electrolyte", "").replace(" redox couple", ""),
                fontsize=5.8, ha="center", va="center", color="#20242A")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("co-occurrence embedding dimension 1")
    ax.set_ylabel("co-occurrence embedding dimension 2")
    ax.text(0.01, 0.98, "b", transform=ax.transAxes, fontsize=12, fontweight="bold", va="top")
    ax.text(0.07, 0.98, "Concept atlas and density", transform=ax.transAxes, fontsize=11, fontweight="bold", va="top")
    ax.text(0.07, 0.91, "Blue: TG-skewed; ochre: iTE-skewed; grey: shared", transform=ax.transAxes, fontsize=7, color="#555", va="top")
    save_all(fig, "tg_ite_concept_atlas")

    coords = pd.DataFrame({
        "concept": all_concepts,
        "x": xy[:, 0],
        "y": xy[:, 1],
        "total_count": [total[c] for c in all_concepts],
        "tg_count": [tg[c] for c in all_concepts],
        "ite_count": [ite[c] for c in all_concepts],
        "tg_specificity": spec,
        "category": [cat_map.get(c, "material") for c in all_concepts],
    })
    coords.to_csv(OUT / "concept_atlas_coordinates.csv", index=False)
    return coords


def plot_evolution(tg_docs, cat_map):
    periods = ["<=2015", "2016-2019", "2020-2022", "2023-2026"]
    cats = ["redox", "medium", "mechanism", "device", "material", "electrode"]
    data = pd.DataFrame(0, index=periods, columns=cats, dtype=float)
    for row in tg_docs.itertuples():
        p = period_label(row.year)
        seen_cats = [cat_map.get(c, "material") for c in set(row.concepts)]
        for cat in seen_cats:
            if cat in data.columns:
                data.loc[p, cat] += 1
    frac = data.div(data.sum(axis=1), axis=0).fillna(0)
    x = np.arange(len(periods))
    fig, ax = plt.subplots(figsize=(7.1, 3.8))
    bottom = np.zeros(len(periods))
    for cat in cats:
        ax.fill_between(x, bottom, bottom + frac[cat].to_numpy(), color=PALETTE.get(cat, "#999"), alpha=0.78, lw=0)
        ymid = bottom + frac[cat].to_numpy() / 2
        if frac[cat].iloc[-1] > 0.07:
            ax.text(x[-1] + 0.06, ymid[-1], cat, va="center", fontsize=7, color="#333")
        bottom += frac[cat].to_numpy()
    ax.set_xlim(-0.05, len(periods) - 0.55)
    ax.set_ylim(0, 1)
    ax.set_xticks(x)
    ax.set_xticklabels(periods)
    ax.set_ylabel("share of TG concept mentions")
    ax.text(0.01, 0.98, "c", transform=ax.transAxes, fontsize=12, fontweight="bold", va="top")
    ax.text(0.07, 0.98, "TG mechanism-space evolution", transform=ax.transAxes, fontsize=11, fontweight="bold", va="top")
    ax.text(0.07, 0.90, "Period-normalized concept-family composition", transform=ax.transAxes, fontsize=7, color="#555", va="top")
    save_all(fig, "tg_evolution_paths")
    data.to_csv(OUT / "tg_period_concept_family_counts.csv")


def plot_knowledge_flow(docs):
    tg_first = concept_first_year(docs, "TG")
    ite_first = concept_first_year(docs[docs["source"].isin(["iTE1", "iTE2"])])
    flows = []
    for c, ty in tg_first.items():
        iy = ite_first.get(c)
        if iy is not None and iy < ty:
            flows.append((c, iy, ty, ty - iy))
    flows = sorted(flows, key=lambda x: (-x[3], x[2], x[0]))
    df = pd.DataFrame(flows, columns=["concept", "first_iTE_year", "first_TG_year", "lag_years"])
    df.to_csv(OUT / "ite_to_tg_candidate_knowledge_flows.csv", index=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.1, 3.8), gridspec_kw={"width_ratios": [1.05, 1.45]})
    bins = np.arange(0, max([1] + df["lag_years"].tolist()) + 2) - 0.5 if len(df) else np.arange(3)
    ax1.hist(df["lag_years"] if len(df) else [], bins=bins, color=PALETTE["ite"], ec="white")
    ax1.set_xlabel("years concept appeared in iTE before TG")
    ax1.set_ylabel("number of concepts")
    ax1.text(0.02, 0.98, "d", transform=ax1.transAxes, fontsize=12, fontweight="bold", va="top")
    ax1.text(0.14, 0.98, "Knowledge-flow lag", transform=ax1.transAxes, fontsize=10.5, fontweight="bold", va="top")

    show = df.sort_values("lag_years", ascending=False).head(16).iloc[::-1]
    y = np.arange(len(show))
    if len(show):
        segments = [[(r.first_iTE_year, i), (r.first_TG_year, i)] for i, r in enumerate(show.itertuples())]
        lc = LineCollection(segments, colors=PALETTE["shared"], linewidths=1.8, alpha=0.65)
        ax2.add_collection(lc)
        ax2.scatter(show["first_iTE_year"], y, color=PALETTE["ite"], s=24, label="iTE first")
        ax2.scatter(show["first_TG_year"], y, color=PALETTE["tg"], s=24, label="TG first")
        ax2.set_yticks(y)
        ax2.set_yticklabels(show["concept"], fontsize=6)
        ax2.set_xlim(min(show["first_iTE_year"]) - 1, max(show["first_TG_year"]) + 1)
    ax2.set_xlabel("first observed year")
    ax2.legend(loc="lower right", fontsize=6)
    ax2.text(0.02, 0.98, "Candidate iTE -> TG transferred concepts", transform=ax2.transAxes,
             fontsize=10.5, fontweight="bold", va="top")
    save_all(fig, "ite_to_tg_knowledge_flow")


def plot_emergent_edges(docs, cat_map):
    early = docs[docs["year"] <= 2022]
    late = docs[docs["year"] >= 2023]
    G_early = nx.Graph()
    for row in early.itertuples():
        for u, v in combinations(sorted(set(row.concepts)), 2):
            G_early.add_edge(u, v)
    late_edges = Counter()
    support = defaultdict(list)
    for row in late[late["source"] == "TG"].itertuples():
        for u, v in combinations(sorted(set(row.concepts)), 2):
            if not G_early.has_edge(u, v):
                late_edges[(u, v)] += 1
                support[(u, v)].append(row.title)
    scored = []
    for (u, v), n in late_edges.items():
        if u not in G_early or v not in G_early:
            d = np.nan
        else:
            try:
                d = nx.shortest_path_length(G_early, u, v)
            except nx.NetworkXNoPath:
                d = np.nan
        scored.append((u, v, n, d, cat_map.get(u, "material"), cat_map.get(v, "material"), support[(u, v)][0]))
    edge_df = pd.DataFrame(scored, columns=["concept_u", "concept_v", "late_TG_count", "early_graph_distance", "cat_u", "cat_v", "example_title"])
    edge_df = edge_df.sort_values(["late_TG_count", "early_graph_distance"], ascending=[False, False])
    edge_df.to_csv(OUT / "tg_emergent_edges_2023_2026.csv", index=False)

    top = edge_df.head(24).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.1, 5.0))
    labels = [f"{r.concept_u} + {r.concept_v}" for r in top.itertuples()]
    vals = top["late_TG_count"].to_numpy()
    dvals = top["early_graph_distance"].fillna(5).to_numpy()
    colors = [PALETTE["accent"] if d >= 3 or np.isnan(d) else PALETTE["tg"] for d in dvals]
    ax.barh(np.arange(len(top)), vals, color=colors, alpha=0.82)
    ax.set_yticks(np.arange(len(top)))
    ax.set_yticklabels(labels, fontsize=5.6)
    ax.set_xlabel("new TG co-occurrences after 2022")
    ax.text(0.01, 0.98, "e", transform=ax.transAxes, fontsize=12, fontweight="bold", va="top")
    ax.text(0.07, 0.98, "Emergent TG concept links", transform=ax.transAxes, fontsize=11, fontweight="bold", va="top")
    ax.text(0.07, 0.92, "Red marks more distant or absent pre-2023 links in the early graph", transform=ax.transAxes, fontsize=7, color="#555", va="top")
    save_all(fig, "tg_emergent_links")


def write_summary(docs, cat_map):
    tg = docs[docs["source"] == "TG"]
    ite = docs[docs["source"].isin(["iTE1", "iTE2"])]
    tg_cnt = concept_counts(docs, "TG")
    ite_cnt = concept_counts(ite)
    flows = pd.read_csv(OUT / "ite_to_tg_candidate_knowledge_flows.csv")
    emergent = pd.read_csv(OUT / "tg_emergent_edges_2023_2026.csv")
    lines = []
    lines.append("# Thermogalvanic Concept-Graph Pilot")
    lines.append("")
    lines.append("## Dataset")
    lines.append(f"- TG articles: {len(tg)} ({int(tg.year.min())}-{int(tg.year.max())})")
    lines.append(f"- iTE context articles: {len(ite)} ({int(ite.year.min())}-{int(ite.year.max())})")
    lines.append(f"- Unique extracted concepts: {len(set(c for cs in docs.concepts for c in cs))}")
    lines.append("")
    lines.append("## Top TG Concepts")
    for c, n in tg_cnt.most_common(20):
        lines.append(f"- {c}: {n}")
    lines.append("")
    lines.append("## Candidate iTE -> TG Knowledge Flows")
    for r in flows.head(15).itertuples():
        lines.append(f"- {r.concept}: iTE {int(r.first_iTE_year)} -> TG {int(r.first_TG_year)} (lag {int(r.lag_years)} years)")
    lines.append("")
    lines.append("## Emergent TG Links After 2022")
    for r in emergent.head(15).itertuples():
        dist = "not connected" if pd.isna(r.early_graph_distance) else f"d={int(r.early_graph_distance)}"
        lines.append(f"- {r.concept_u} + {r.concept_v}: {int(r.late_TG_count)} late TG papers; early graph {dist}")
    lines.append("")
    lines.append("## Pilot Caveat")
    lines.append("Concepts were extracted with an auditable dictionary plus high-frequency n-grams from the material/mechanism fields. This is useful for scoping figures, but an NMI-grade study should replace this layer with manually seeded LLM concept extraction and synonym normalization.")
    (OUT / "tg_concept_graph_pilot_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    df = pd.concat([
        read_source(TG_PATH, "TG"),
        read_source(ITE1_PATH, "iTE1"),
        read_source(ITE2_PATH, "iTE2"),
    ], ignore_index=True)
    df = df.dropna(subset=["year"])
    df = df[df["year"].between(1990, 2026)].copy()
    df = df.drop_duplicates(subset=["doi", "title", "source"], keep="first")

    candidates, _, _ = make_ngram_candidates(df)
    ngram_doc_terms, ngram_cats = assign_ngram_concepts(df, candidates)

    all_cats = {}
    concepts_all = []
    for row, extra in zip(df.itertuples(), ngram_doc_terms):
        rule_concepts, cats = extract_rule_concepts(row)
        all_cats.update(cats)
        all_cats.update(ngram_cats)
        concepts = list(dict.fromkeys(rule_concepts + extra))
        concepts_all.append(concepts[:22])
    df["concepts"] = concepts_all
    df = df[df["concepts"].map(len) >= 2].copy()

    rows = []
    for row in df.itertuples():
        for c in row.concepts:
            rows.append({
                "doc_id": row.doc_id,
                "source": row.source,
                "year": int(row.year),
                "title": row.title,
                "doi": row.doi,
                "concept": c,
                "category": all_cats.get(c, "material"),
            })
    pd.DataFrame(rows).to_csv(OUT / "article_concepts_long.csv", index=False)

    edges = []
    for row in df.itertuples():
        for u, v in combinations(sorted(set(row.concepts)), 2):
            edges.append({"doc_id": row.doc_id, "source": row.source, "year": int(row.year), "concept_u": u, "concept_v": v})
    pd.DataFrame(edges).to_csv(OUT / "concept_edges_long.csv", index=False)

    plot_bubble(df[df["source"] == "TG"], all_cats)
    plot_atlas(df, all_cats)
    plot_evolution(df[df["source"] == "TG"], all_cats)
    plot_knowledge_flow(df)
    plot_emergent_edges(df, all_cats)
    write_summary(df, all_cats)
    print("wrote outputs to", OUT)


if __name__ == "__main__":
    main()
